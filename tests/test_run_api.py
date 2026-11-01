# AI contribution: 50% or more AI-generated
"""Run status/detail API over persisted metadata, including restarts (#27)."""

from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.main import app
from app.metadata.database import Database
from app.metadata.models import OutputEndpoint, Run, RunBlock
from app.runs import execute_revision
from tests.run_support import Fail, chain, executor, seed_revision

SUMMARY_KEYS = {
    "schema_version",
    "id",
    "project_id",
    "pipeline_id",
    "pipeline_revision_id",
    "revision",
    "state",
    "created_at",
    "started_at",
    "ended_at",
    "duration_ms",
    "row_count",
    "error",
}
BLOCK_KEYS = {
    "position",
    "node_id",
    "block_id",
    "block_version",
    "state",
    "started_at",
    "ended_at",
    "duration_ms",
    "rows_in",
    "rows_out",
    "error",
}


def db_of(client: TestClient) -> Database:
    return cast(Database, client.app.state.database)  # type: ignore[attr-defined]


def test_detail_has_a_stable_schema_and_links_artifacts(client: TestClient):
    db = db_of(client)
    revision_id = seed_revision(db, chain("test.source", "test.sink"))
    first = execute_revision(db, executor(), revision_id).run_id
    second = execute_revision(db, executor(), revision_id).run_id
    with db.transaction() as session:
        session.add(
            OutputEndpoint(
                run_id=first,
                node_id="n1",
                name="table",
                format="parquet",
                artifact_ref="artifact-1",
                row_count=2,
            )
        )

    body = client.get(f"/api/v1/runs/{first}").json()
    assert set(body) == SUMMARY_KEYS | {"blocks", "events", "outputs"}
    assert (body["schema_version"], body["state"], body["row_count"]) == (
        1,
        "succeeded",
        2,
    )
    assert {key for block in body["blocks"] for key in block} == BLOCK_KEYS
    assert [o["artifact_ref"] for o in body["outputs"]] == ["artifact-1"]
    assert client.get(f"/api/v1/runs/{second}").json()["outputs"] == []


def test_failed_run_exposes_structured_redacted_error(client: TestClient):
    db = db_of(client)
    revision_id = seed_revision(db, chain("test.source", "test.fail"))
    run_id = execute_revision(db, executor(), revision_id).run_id
    response = client.get(f"/api/v1/runs/{run_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "failed"
    assert body["error"]["code"] == "source_unreadable"
    assert body["blocks"][1]["error"]["code"] == "source_unreadable"
    assert "hunter2" not in response.text and "/home/alice" not in response.text


@pytest.mark.parametrize(
    "reason,fragments",
    [
        # Opposite quote type embedded in a JSON-style quoted value.
        ('{"password": "synthetic\'secret"}', ["synthetic'secret", "secret"]),
        # Escaped matching quote embedded in a JSON-style quoted value.
        ('{"password": "synthetic\\" secret"}', ["synthetic", "secret"]),
        # Opposite quote type embedded in a bare key=value quoted value.
        ('password="synthetic\' secret"', ["synthetic' secret", "secret"]),
        # Whitespace inside matching quotes.
        ('token="a b c" failed', ["a b c"]),
        # Key and value use different quote styles.
        ("{\"password\": 'synthetic-secret'}", ["synthetic-secret"]),
    ],
)
def test_quoted_credential_edge_cases_never_reach_db_or_api(
    client: TestClient, reason: str, fragments: list[str]
):
    """Credentials with embedded/escaped quotes must not survive persistence
    or the HTTP detail response (#27 follow-up review)."""
    db = db_of(client)
    revision_id = seed_revision(db, chain("test.source", "test.fail"))
    run_id = execute_revision(
        db, executor(fail=Fail(reason=reason)), revision_id
    ).run_id

    with db.transaction() as session:
        run = session.get(Run, run_id)
        assert run is not None
        block = session.scalars(
            select(RunBlock).where(RunBlock.run_id == run_id, RunBlock.node_id == "n1")
        ).one()
        for text in (run.error_reason, block.error_reason):
            assert text is not None
            for fragment in fragments:
                assert fragment not in text

    response = client.get(f"/api/v1/runs/{run_id}")
    assert response.status_code == 200
    for fragment in fragments:
        assert fragment not in response.text


def test_list_filters_paginates_and_orders_newest_first(client: TestClient):
    db = db_of(client)
    good = seed_revision(db, chain("test.source"))
    bad = seed_revision(db, chain("test.source", "test.fail"))
    ids = [execute_revision(db, executor(), r).run_id for r in (good, good, bad)]

    page = client.get("/api/v1/runs", params={"limit": 2}).json()
    assert (page["total"], len(page["items"])) == (3, 2)
    assert set(page["items"][0]) == SUMMARY_KEYS
    assert page["items"][0]["id"] == ids[2]
    failed = client.get("/api/v1/runs", params={"state": "failed"}).json()
    assert [item["id"] for item in failed["items"]] == [ids[2]]
    pipeline_id = client.get(f"/api/v1/runs/{ids[0]}").json()["pipeline_id"]
    scoped = client.get("/api/v1/runs", params={"pipeline_id": pipeline_id}).json()
    assert {item["id"] for item in scoped["items"]} == set(ids[:2])


@pytest.mark.parametrize(
    "path,status,code",
    [
        (f"/api/v1/runs/{uuid4()}", 404, "run_not_found"),
        ("/api/v1/runs/not-a-uuid", 422, "validation_error"),
        ("/api/v1/runs?state=exploded", 422, "validation_error"),
        ("/api/v1/runs?limit=0", 422, "validation_error"),
        ("/api/v1/runs?limit=101", 422, "validation_error"),
    ],
)
def test_invalid_requests_return_error_envelopes(
    client: TestClient, path: str, status: int, code: str
):
    response = client.get(path)
    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert "Traceback" not in response.text


def test_metadata_survives_restart_and_interrupted_runs_are_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "metadata_path", tmp_path / "restart.sqlite3")
    with TestClient(app) as client:
        db = db_of(client)
        revision_id = seed_revision(db, chain("test.source", "test.sink"))
        finished = execute_revision(db, executor(), revision_id).run_id
        abandoned = str(uuid4())
        with db.transaction() as session:
            session.add(
                Run(id=abandoned, pipeline_revision_id=revision_id, state="running")
            )

    with TestClient(app) as client:
        kept = client.get(f"/api/v1/runs/{finished}").json()
        closed = client.get(f"/api/v1/runs/{abandoned}").json()
    assert (kept["state"], kept["row_count"]) == ("succeeded", 2)
    assert closed["state"] == "failed"
    assert closed["error"]["code"] == "interrupted"
    assert closed["ended_at"] is not None
