"""Real API/SQLite tests for project creation, listing and reopening (#19)."""

from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest

from app.config import settings
from app.main import app


def test_project_create_list_open_and_timestamp(client: TestClient):
    assert client.get("/api/v1/projects").json() == {
        "items": [],
        "total": 0,
        "offset": 0,
        "limit": 20,
    }
    response = client.post(
        "/api/v1/projects", json={"name": "  Synthetic inspection  "}
    )
    assert response.status_code == 201
    project = response.json()
    assert str(UUID(project["id"])) == project["id"]
    assert project["name"] == "Synthetic inspection"
    assert project["created_at"].endswith("Z")
    assert set(project) == {"id", "name", "created_at"}
    assert client.get(f"/api/v1/projects/{project['id']}").json() == project
    assert client.get("/api/v1/projects").json()["items"] == [project]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": ""},
        {"name": " \t "},
        {"name": "x" * 129},
        {"name": 123},
        {"name": "line\nbreak"},
        {"name": "a\x00b"},
        {"name": "demo", "path": "/private"},
    ],
)
def test_invalid_names_do_not_create_rows(
    client: TestClient, payload: dict[str, object]
):
    response = client.post(
        "/api/v1/projects",
        json=payload,
        headers={"X-Correlation-ID": "project-validation"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["correlation_id"] == "project-validation"
    assert client.get("/api/v1/projects").json()["total"] == 0


def test_names_are_labels_not_paths_and_duplicates_have_distinct_ids(
    client: TestClient,
):
    projects = [
        client.post("/api/v1/projects", json={"name": "../../Synthetic"}).json()
        for _ in range(2)
    ]
    assert projects[0]["id"] != projects[1]["id"]
    assert all(project["name"] == "../../Synthetic" for project in projects)
    assert client.get("/api/v1/projects").json()["total"] == 2


def test_name_boundary_and_unicode(client: TestClient):
    for name in ["x" * 128, "製造データ", "🔧" * 128]:
        assert client.post("/api/v1/projects", json={"name": name}).status_code == 201


@pytest.mark.parametrize("query", ["offset=-1", "limit=0", "limit=101", "limit=abc"])
def test_invalid_pagination(client: TestClient, query: str):
    assert client.get("/api/v1/projects?" + query).status_code == 422


def test_stable_pagination_without_duplicate_rows(client: TestClient):
    created = {
        client.post("/api/v1/projects", json={"name": f"Project {i}"}).json()["id"]
        for i in range(5)
    }
    seen: list[str] = []
    for offset in [0, 2, 4]:
        page = client.get(f"/api/v1/projects?offset={offset}&limit=2").json()
        assert page["total"] == 5
        assert page["offset"] == offset and page["limit"] == 2
        seen.extend(item["id"] for item in page["items"])
    assert len(seen) == len(set(seen)) == 5
    assert set(seen) == created
    assert client.get("/api/v1/projects?offset=10").json()["items"] == []


def test_unknown_and_invalid_ids_use_safe_errors(client: TestClient):
    response = client.get(
        f"/api/v1/projects/{uuid4()}", headers={"X-Correlation-ID": "unknown-project"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "project_not_found"
    assert response.json()["error"]["correlation_id"] == "unknown-project"
    assert response.headers["x-correlation-id"] == "unknown-project"
    assert client.get("/api/v1/projects/not-a-uuid").status_code == 422


def test_metadata_survives_service_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "metadata_path", tmp_path / "projects.sqlite3")
    with TestClient(app) as first:
        project = first.post(
            "/api/v1/projects", json={"name": "Survives restart"}
        ).json()
    with TestClient(app) as reopened:
        assert reopened.get(f"/api/v1/projects/{project['id']}").json() == project
        assert reopened.get("/api/v1/projects").json()["items"] == [project]


def test_projects_have_versioned_openapi_contract(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]
    assert {"get", "post"} <= paths["/api/v1/projects"].keys()
    assert "get" in paths["/api/v1/projects/{project_id}"]
