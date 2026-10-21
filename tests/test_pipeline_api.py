"""Real SQLite authoring roundtrips, isolation and conflict handling (#14)."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select

from app.main import app
from app.metadata.models import PipelineRevision


def graph() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "nodes": [
            {
                "id": key,
                "block_id": "synthetic.add_constant",
                "block_version": "1.0.0",
                "config": {"amount": i},
            }
            for i, key in enumerate(("a", "b"))
        ],
        "edges": [
            {
                "id": "ab",
                "source": {"node_id": "a", "port": "table"},
                "target": {"node_id": "b", "port": "table"},
            }
        ],
        "layout": {
            "positions": {"a": {"x": 10.0, "y": -20.0}, "b": {"x": 300.0, "y": 40.0}}
        },
    }


def project_path(client: TestClient) -> str:
    project = client.post("/api/v1/projects", json={"name": "Synthetic"}).json()
    return f"/api/v1/projects/{project['id']}/pipelines"


def test_create_reload_update_rename_and_history(client: TestClient):
    path = project_path(client)
    created = client.post(path, json={"name": " Inspection ", "definition": graph()})
    assert created.status_code == 201, created.text
    original = created.json()
    assert original["name"] == "Inspection"
    assert original["revision"] == 1
    assert original["definition"] == graph()
    url = f"{path}/{original['id']}"
    assert client.get(url).json() == original
    changed = graph()
    changed["nodes"][0]["config"]["amount"] = 8
    changed["layout"]["positions"]["a"] = {"x": -100, "y": 22}
    result = client.put(
        url, json={"name": "Edited", "expected_revision": 1, "definition": changed}
    )
    assert result.status_code == 200, result.text
    assert result.json()["definition"] == changed
    renamed = client.patch(url, json={"name": "Renamed", "expected_revision": 2})
    assert renamed.status_code == 200
    assert renamed.json()["definition"] == changed
    assert renamed.json()["revision"] == 3
    assert client.get(path).json()["items"][0]["name"] == "Renamed"
    with app.state.database.transaction() as session:
        revisions = session.scalars(
            select(PipelineRevision).order_by(PipelineRevision.revision)
        ).all()
        assert [r.revision for r in revisions] == [1, 2, 3]
        assert revisions[0].definition == graph()


def test_cross_project_access_and_name_conflicts(client: TestClient):
    a, b = project_path(client), project_path(client)
    payload = {"name": "Example", "definition": graph()}
    original = client.post(a, json=payload).json()
    assert client.post(a, json=payload).status_code == 409
    assert client.post(b, json=payload).status_code == 201
    assert client.get(f"{b}/{original['id']}").status_code == 404
    assert (
        client.put(
            f"{b}/{original['id']}", json=payload | {"expected_revision": 1}
        ).status_code
        == 404
    )
    assert client.get(f"/api/v1/projects/{uuid4()}/pipelines").status_code == 404


def test_concurrent_writers_cannot_overwrite_and_stale_rename_fails(client: TestClient):
    path = project_path(client)
    original = client.post(path, json={"name": "First", "definition": graph()}).json()
    url = f"{path}/{original['id']}"

    def save(name: str) -> int:
        return int(
            client.put(
                url, json={"name": name, "definition": graph(), "expected_revision": 1}
            ).status_code
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, ["Writer A", "Writer B"])) == [200, 409]
    assert (
        client.patch(url, json={"name": "Stale", "expected_revision": 1}).status_code
        == 409
    )
    assert client.get(url).json()["revision"] == 2


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 2},
        {
            "nodes": [
                {
                    "id": "x",
                    "block_id": "example",
                    "block_version": "1",
                    "config": {"password": "PRIVATE_SENTINEL"},
                }
            ]
        },
        {
            "nodes": [
                {
                    "id": "x",
                    "block_id": "example",
                    "block_version": "1",
                    "config": {"path": "/private/example.csv"},
                }
            ]
        },
        {
            "edges": [
                {
                    "id": "bad",
                    "source": {"node_id": "a", "port": "table"},
                    "target": {"node_id": "a", "port": "table"},
                }
            ]
        },
        {"layout": {"positions": {"missing": {"x": 0, "y": 0}}}},
    ],
)
def test_invalid_definitions_are_rejected_without_persistence(
    client: TestClient, change: dict[str, Any]
):
    path = project_path(client)
    response = client.post(
        path, json={"name": "Rejected", "definition": graph() | change}
    )
    assert response.status_code == 422, response.text
    assert "PRIVATE_SENTINEL" not in response.text
    assert "schema_version 1" in response.json()["error"]["message"]
    assert client.get(path).json()["total"] == 0


def test_interrupted_save_rolls_back_name_and_revision(client: TestClient):
    path = project_path(client)
    original = client.post(
        path, json={"name": "Original", "definition": graph()}
    ).json()
    url = f"{path}/{original['id']}"

    def interrupt(*args: object) -> None:
        raise RuntimeError("Synthetic interrupted write")

    event.listen(PipelineRevision, "before_insert", interrupt)
    try:
        response = client.put(
            url, json={"name": "Lost", "definition": graph(), "expected_revision": 1}
        )
        assert response.status_code == 500
    finally:
        event.remove(PipelineRevision, "before_insert", interrupt)
    assert client.get(url).json() == original


def test_pipeline_cors_supports_update_and_rename(client: TestClient):
    for method in ("PUT", "PATCH"):
        response = client.options(
            "/api/v1/projects/example/pipelines/example",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": method,
            },
        )
        assert response.status_code == 200
