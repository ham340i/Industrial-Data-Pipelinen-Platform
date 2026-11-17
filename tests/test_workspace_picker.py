# AI contribution: 50% or more AI-generated
"""Native picker boundaries and selection without changing saved settings."""

from collections.abc import Iterator
import json
from pathlib import Path
import subprocess
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import native_folder_picker, workspace
from app.config import settings
from app.main import app
from app.metadata.database import Database

URL = "/api/v1/settings/workspace"


@pytest.fixture(autouse=True)
def picker_roots(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    permitted = tmp_path / "permitted"
    permitted.mkdir()
    monkeypatch.setattr(settings, "workspace_root", None)
    monkeypatch.setattr(settings, "allowed_workspace_roots", [permitted])
    monkeypatch.setattr(workspace, "local_drives", lambda: [tmp_path])
    monkeypatch.setattr(workspace, "platform", "win32")

    def unexpected_picker(initial: str | None) -> str | None:
        pytest.fail("Unexpected native dialog in an automated test")

    monkeypatch.setattr(workspace, "open_folder_dialog", unexpected_picker)


@pytest.fixture
def local_client(client: TestClient) -> Iterator[TestClient]:
    local = TestClient(
        app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50001)
    )
    yield local
    local.close()


def test_native_selection_is_not_saved_until_explicit_save(
    local_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chosen = tmp_path / "New workspace"
    chosen.mkdir()
    calls: list[str | None] = []

    def choose(initial: str | None) -> str:
        calls.append(initial)
        return str(chosen)

    monkeypatch.setattr(workspace, "open_folder_dialog", choose)
    project = local_client.post(
        "/api/v1/projects", json={"name": "Native picker"}
    ).json()["id"]
    response = local_client.post(
        f"{URL}/pick-folder", json={"initial_path": str(tmp_path / "permitted")}
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"path": str(chosen)}
    assert calls == [str(tmp_path / "permitted")]
    assert not workspace.settings_file(app.state.database).exists()
    assert not (chosen / project).exists()
    local_client.put(
        URL, json={"root_path": response.json()["path"]}
    ).raise_for_status()
    assert (chosen / project / "inputs").is_dir()
    restarted = Database(app.state.database.path)
    try:
        assert workspace.effective_workspace_root(restarted) == chosen
    finally:
        restarted.close()


def test_cancel_and_invalid_starting_path_leave_setting_unchanged(
    local_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = str(tmp_path / "permitted")
    local_client.put(URL, json={"root_path": saved}).raise_for_status()
    calls: list[str | None] = []

    def cancel(initial: str | None) -> None:
        calls.append(initial)

    monkeypatch.setattr(workspace, "open_folder_dialog", cancel)
    response = local_client.post(
        f"{URL}/pick-folder", json={"initial_path": "invalid draft"}
    )
    assert response.json() == {"path": None}
    assert calls == [None]
    assert local_client.get(URL).json()["root_path"] == saved


@pytest.mark.parametrize(
    "headers",
    [
        {"origin": "https://untrusted.example"},
        {"origin": "null"},
        {"sec-fetch-site": "cross-site"},
    ],
)
def test_untrusted_origins_cannot_open_native_windows(
    local_client: TestClient, headers: dict[str, str]
) -> None:
    response = local_client.post(f"{URL}/pick-folder", json={}, headers=headers)
    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    ("peer", "host"),
    [
        ("192.0.2.12", "127.0.0.1"),
        ("127.0.0.1", "rebound.example"),
    ],
)
def test_remote_and_rebound_requests_cannot_open_native_windows(
    client: TestClient, peer: str, host: str
) -> None:
    remote = TestClient(app, base_url=f"http://{host}", client=(peer, 50001))
    try:
        response = remote.post(
            f"{URL}/pick-folder", json={}, headers={"x-forwarded-for": "127.0.0.1"}
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "workspace_picker_unavailable"
    finally:
        remote.close()


def test_non_windows_picker_has_manual_entry_fallback(
    local_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(workspace, "platform", "linux")
    response = local_client.post(f"{URL}/pick-folder", json={})
    assert response.status_code == 409
    assert "Enter a workspace folder path" in response.json()["error"]["message"]


def test_only_one_native_picker_can_be_open(local_client: TestClient) -> None:
    with workspace.folder_picker_lock:
        response = local_client.post(f"{URL}/pick-folder", json={})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "workspace_picker_busy"


@pytest.mark.parametrize(
    "failure",
    [
        subprocess.TimeoutExpired("picker", 300),
        subprocess.CalledProcessError(1, "picker", stderr="private details"),
        OSError("private details"),
        ValueError("private details"),
    ],
)
def test_picker_errors_are_safe_and_release_the_lock(
    local_client: TestClient, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    def fail(initial: str | None) -> None:
        raise failure

    monkeypatch.setattr(workspace, "open_folder_dialog", fail)
    response = local_client.post(f"{URL}/pick-folder", json={})
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert "private details" not in response.text
    assert not workspace.folder_picker_lock.locked()
    assert not workspace.settings_file(app.state.database).exists()


def test_native_returned_path_must_be_a_real_local_directory(
    local_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        workspace, "open_folder_dialog", lambda initial: str(tmp_path / "missing")
    )
    response = local_client.post(f"{URL}/pick-folder", json={})
    assert response.status_code == 422
    assert not workspace.settings_file(app.state.database).exists()


@pytest.mark.parametrize("returned", [None, "C:/Workspace with spaces"])
def test_native_helper_uses_structured_input_and_supports_cancel(
    monkeypatch: pytest.MonkeyPatch, returned: str | None
) -> None:
    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert command[-2:] == ["-m", "app.native_folder_picker"]
        assert json.loads(kwargs["input"]) == {"initial_path": "C:/Initial folder"}
        assert kwargs["timeout"] == 300
        assert "shell" not in kwargs
        return subprocess.CompletedProcess(command, 0, json.dumps({"path": returned}))

    monkeypatch.setattr(subprocess, "run", run)
    assert native_folder_picker.open_folder_dialog("C:/Initial folder") == returned
