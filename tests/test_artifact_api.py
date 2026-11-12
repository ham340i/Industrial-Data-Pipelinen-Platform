"""Artifact metadata and bounded-query HTTP contracts (#28)."""

from typing import cast
from pathlib import Path
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient

from app.blocks.contracts import Column, DataSchema
from app.config import settings
from app.metadata.database import Database
from app.metadata.models import OutputEndpoint, Run
from tests.run_support import chain, seed_revision

SCHEMA = DataSchema(
    columns=(
        Column(name="name", dtype="string", nullable=False),
        Column(name="value", dtype="integer", nullable=True),
    )
)


def db_of(client: TestClient) -> Database:
    return cast(Database, client.app.state.database)  # type: ignore[attr-defined]


def registered(client: TestClient, *, format_: str = "parquet") -> str:
    db = db_of(client)
    revision_id = seed_revision(db, chain("test.source"))
    run_id, artifact_id = str(uuid4()), str(uuid4())
    assert settings.workspace_root is not None
    output = settings.workspace_root / "outputs"
    output.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pylist(
            [{"name": "alpha", "value": 1}, {"name": "beta", "value": None}],
            schema=pa.schema(
                [
                    pa.field("name", pa.string(), nullable=False),
                    pa.field("value", pa.int64(), nullable=True),
                ]
            ),
        ),
        output / "result.parquet",
    )
    with db.transaction(write=True) as session:
        session.add(Run(id=run_id, pipeline_revision_id=revision_id, state="succeeded"))
        session.add(
            OutputEndpoint(
                id=artifact_id,
                run_id=run_id,
                node_id="sink",
                name="artifact",
                format=format_,
                artifact_ref="outputs/result.parquet",
                row_count=2,
                schema_json=SCHEMA.model_dump(mode="json"),
            )
        )
    return artifact_id


def test_metadata_exposes_provenance_without_a_machine_path(client: TestClient):
    artifact_id = registered(client)
    response = client.get(f"/api/v1/artifacts/{artifact_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == artifact_id
    assert body["pipeline_revision_id"]
    assert body["pipeline_id"] and body["project_id"]
    assert body["resource_ref"] == "outputs/result.parquet"
    assert body["row_count"] == 2
    assert body["data_schema"] == SCHEMA.model_dump(mode="json")
    assert str(settings.workspace_root) not in response.text


def test_query_returns_only_the_requested_bounded_projection(client: TestClient):
    artifact_id = registered(client)
    response = client.post(
        f"/api/v1/artifacts/{artifact_id}/query",
        json={"columns": ["value"], "limit": 1},
    )

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": 1,
        "artifact_id": artifact_id,
        "run_id": response.json()["run_id"],
        "pipeline_revision_id": response.json()["pipeline_revision_id"],
        "columns": ["value"],
        "rows": [[1]],
        "offset": 0,
        "limit": 1,
        "has_more": True,
    }


def test_query_policy_uses_stable_safe_errors(client: TestClient):
    missing = client.get(f"/api/v1/artifacts/{uuid4()}")
    assert (missing.status_code, missing.json()["error"]["code"]) == (
        404,
        "artifact_not_found",
    )

    artifact_id = registered(client)
    invalid = client.post(
        f"/api/v1/artifacts/{artifact_id}/query",
        json={"sql": "SELECT * FROM read_parquet('/private/file')"},
    )
    assert (invalid.status_code, invalid.json()["error"]["code"]) == (
        422,
        "validation_error",
    )


def test_csv_and_missing_files_are_not_queryable(client: TestClient):
    csv_id = registered(client, format_="csv")
    csv = client.post(f"/api/v1/artifacts/{csv_id}/query", json={})
    assert (csv.status_code, csv.json()["error"]["code"]) == (
        422,
        "artifact_not_queryable",
    )

    parquet_id = registered(client)
    assert settings.workspace_root is not None
    (settings.workspace_root / "outputs" / "result.parquet").unlink()
    missing = client.post(f"/api/v1/artifacts/{parquet_id}/query", json={})
    assert (missing.status_code, missing.json()["error"]["code"]) == (
        409,
        "artifact_unavailable",
    )


def test_artifact_query_uses_saved_root_and_handles_unconfigured_workspace(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    artifact_id = registered(client)
    original = settings.workspace_root
    assert original is not None
    selected = tmp_path / "selected"
    selected.mkdir()
    (original / "outputs").rename(selected / "outputs")
    monkeypatch.setattr(settings, "allowed_workspace_roots", [selected])
    client.put(
        "/api/v1/settings/workspace", json={"root_path": str(selected)}
    ).raise_for_status()
    url = f"/api/v1/artifacts/{artifact_id}/query"
    assert client.post(url, json={}).status_code == 200
    monkeypatch.setattr(settings, "workspace_root", None)
    client.put(
        "/api/v1/settings/workspace", json={"root_path": None}
    ).raise_for_status()
    response = client.post(url, json={})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "artifact_unavailable"
