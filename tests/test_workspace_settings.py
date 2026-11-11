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
def no_environment_root(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "workspace_root", None)
    monkeypatch.setattr(
        settings,
        "allowed_workspace_roots",
        [
            tmp_path / name
            for name in (
                "root-1",
                "root-2",
                "override",
                "valid",
                "missing",
                "file.txt",
                "root",
                "other",
                "repaired",
            )
        ],
    )


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


@pytest.mark.parametrize(
    "suffix", ["outside", "missing", "../escape", "\\\\server\\share"]
)
def test_unapproved_paths_are_rejected_before_filesystem_access(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suffix: str
):
    monkeypatch.setattr(settings, "allowed_workspace_roots", [])
    existing = tmp_path / "outside"
    existing.mkdir()

    def unexpected_probe(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Unapproved request reached the filesystem probe")

    monkeypatch.setattr(workspace, "checked_root", unexpected_probe)
    value = suffix if suffix.startswith("\\\\") else str(tmp_path / suffix)
    response = client.put(URL, json={"root_path": value})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "workspace_invalid_path"
    assert not workspace.settings_file(app.state.database).exists()
    assert list(existing.iterdir()) == []


def test_default_permitted_root_and_startup_without_environment(
    client: TestClient, tmp_path: Path
):
    root = tmp_path / "workspaces"
    root.mkdir()
    assert str(root) in client.get(URL).json()["allowed_roots"]
    assert client.put(URL, json={"root_path": str(root)}).status_code == 200
    # Exercise lifespan with no environment root (the shared fixture sets one).
    with TestClient(app) as restarted:
        assert restarted.get(URL).json()["root_path"] == str(root)
