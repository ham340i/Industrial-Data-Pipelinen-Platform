"""Private settings persistence and immediate preview/project integration."""

from pathlib import Path
import os
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.metadata.database import Database
from app import workspace

URL = "/api/v1/settings/workspace"


@pytest.fixture(autouse=True)
def no_environment_root(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "workspace_root", None)


def test_save_persists_prepares_projects_and_changes_preview_without_restart(
    client: TestClient, tmp_path: Path
):
    initial = client.get(URL)
    assert initial.json()["source"] == "unconfigured"
    assert initial.headers["cache-control"] == "no-store"
    project = client.post("/api/v1/projects", json={"name": "Workspace"}).json()["id"]
    request = {
        "definition": {
            "nodes": [
                {
                    "id": "source",
                    "block_id": "source.json",
                    "block_version": "1.0.0",
                    "config": {"resource_ref": "inputs/data.json"},
                }
            ],
            "edges": [],
        },
        "node_id": "source",
    }
    preview_url = f"/api/v1/projects/{project}/pipelines/preview"
    assert (
        client.post(preview_url, json=request).json()["error"]["code"]
        == "workspace_required"
    )
    for value in (1, 2):
        root = tmp_path / f"root-{value}"
        root.mkdir()
        response = client.put(URL, json={"root_path": str(root)})
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["source"] == "application"
        data = root / project / "inputs" / "data.json"
        data.write_text('[{"value":' + str(value) + "}]", encoding="utf-8")
        assert client.post(preview_url, json=request).json()["rows"] == [
            {"value": value}
        ]
        # A new Database instance reads the persisted selection, not process state.
        restarted = Database(app.state.database.path)
        try:
            assert workspace.effective_workspace_root(restarted) == root
        finally:
            restarted.close()
    assert (tmp_path / "root-1" / project / "inputs" / "data.json").exists()
    created = client.post("/api/v1/projects", json={"name": "New"})
    assert created.status_code == 201
    assert (tmp_path / "root-2" / created.json()["id"] / "inputs").is_dir()
    assert settings.workspace_root is None
    assert client.get("/api/v1/runs").json()["total"] == 0


def test_environment_fallback_and_reset(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    environment = tmp_path / "environment"
    environment.mkdir()
    monkeypatch.setattr(settings, "workspace_root", environment)
    assert client.get(URL).json()["source"] == "environment"
    override = tmp_path / "override"
    override.mkdir()
    client.put(URL, json={"root_path": str(override)}).raise_for_status()
    assert client.get(URL).json()["root_path"] == str(override)
    reset = client.put(URL, json={"root_path": None})
    assert reset.json()["root_path"] == str(environment)
    assert reset.json()["source"] == "environment"
    monkeypatch.setattr(settings, "workspace_root", None)
    assert client.put(URL, json={"root_path": None}).json()["source"] == "unconfigured"


@pytest.mark.parametrize("kind", ["relative", "missing", "file", "empty", "null-byte"])
def test_invalid_path_does_not_replace_setting(
    client: TestClient, tmp_path: Path, kind: str
):
    root = tmp_path / "valid"
    root.mkdir()
    client.put(URL, json={"root_path": str(root)}).raise_for_status()
    file = tmp_path / "file.txt"
    file.write_text("existing", encoding="utf-8")
    value = {
        "relative": "relative/path",
        "missing": str(tmp_path / "missing"),
        "file": str(file),
        "empty": "",
        "null-byte": str(root) + "\x00",
    }[kind]
    response = client.put(URL, json={"root_path": value})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "workspace_invalid_path"
    assert response.headers["cache-control"] == "no-store"
    assert client.get(URL).json()["root_path"] == str(root)


def test_unwritable_root_and_failed_atomic_save_preserve_previous(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path / "root"
    root.mkdir()
    client.put(URL, json={"root_path": str(root)}).raise_for_status()
    other = tmp_path / "other"
    other.mkdir()

    def denied(*args: Any, **kwargs: Any) -> Any:
        raise PermissionError("private system detail")

    with monkeypatch.context() as patch:
        patch.setattr(workspace, "NamedTemporaryFile", denied)
        response = client.put(URL, json={"root_path": str(other)})
        assert response.status_code == 422
    with monkeypatch.context() as patch:
        patch.setattr(os, "replace", denied)
        response = client.put(URL, json={"root_path": str(other)})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "workspace_save_failed"
    assert "private system detail" not in response.text
    assert client.get(URL).json()["root_path"] == str(root)
    assert not list(tmp_path.glob(".workspace-*.tmp"))


def test_project_folder_collision_prevents_save(client: TestClient, tmp_path: Path):
    project = client.post("/api/v1/projects", json={"name": "Collision"}).json()["id"]
    root = tmp_path / "root"
    root.mkdir()
    (root / project).write_text("existing data", encoding="utf-8")
    response = client.put(URL, json={"root_path": str(root)})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "workspace_project_folder"
    assert client.get(URL).json()["source"] == "unconfigured"
    assert (root / project).read_text() == "existing data"


def test_corrupt_settings_can_be_repaired(client: TestClient, tmp_path: Path):
    workspace.settings_file(app.state.database).write_text(
        "bad config", encoding="utf-8"
    )
    response = client.get(URL)
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    root = tmp_path / "repaired"
    root.mkdir()
    assert client.put(URL, json={"root_path": str(root)}).status_code == 200
    assert client.get(URL).json()["root_path"] == str(root)


def test_request_validation_is_no_store(client: TestClient):
    response = client.put(URL, json={"root_path": 123})
    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
