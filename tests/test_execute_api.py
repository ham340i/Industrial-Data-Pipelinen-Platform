# AI contribution: 50% or more AI-generated
"""Execute and timer start/stop/status HTTP APIs (#29)."""

import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def manual_graph() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "nodes": [{"id": "n0", "block_id": "trigger.manual", "block_version": "1.0.0"}],
        "edges": [],
    }


def timer_graph(interval_seconds: int) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "nodes": [
            {
                "id": "n0",
                "block_id": "trigger.timer",
                "block_version": "1.0.0",
                "config": {"interval_seconds": interval_seconds},
            }
        ],
        "edges": [],
    }


def invalid_graph() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "nodes": [{"id": "n0", "block_id": "no.such.block", "block_version": "1"}],
        "edges": [],
    }


def pipelines_path(client: TestClient) -> str:
    project = client.post("/api/v1/projects", json={"name": "Execute"}).json()
    return f"/api/v1/projects/{project['id']}/pipelines"


def create(client: TestClient, path: str, definition: dict[str, Any]) -> str:
    response = client.post(path, json={"name": "P", "definition": definition})
    assert response.status_code == 201, response.text
    return response.json()["id"]  # type: ignore[no-any-return]


def test_execute_runs_the_latest_revision_and_returns_its_run_id(client: TestClient):
    path = pipelines_path(client)
    pipeline_id = create(client, path, manual_graph())

    response = client.post(f"{path}/{pipeline_id}/execute")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["state"] == "succeeded"

    detail = client.get(f"/api/v1/runs/{body['run_id']}")
    assert detail.status_code == 200
    assert detail.json()["state"] == "succeeded"


def test_execute_unknown_pipeline_is_structured_404(client: TestClient):
    path = pipelines_path(client)
    response = client.post(f"{path}/00000000-0000-0000-0000-000000000000/execute")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "pipeline_not_found"


def test_execute_invalid_pipeline_is_structured_422_and_creates_no_run(
    client: TestClient,
):
    path = pipelines_path(client)
    pipeline_id = create(client, path, invalid_graph())

    response = client.post(f"{path}/{pipeline_id}/execute")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "block_unavailable"
    assert error["node_context"] == "n0"

    runs = client.get("/api/v1/runs").json()
    assert runs["total"] == 0


def test_timer_start_stop_and_status_round_trip(client: TestClient):
    path = pipelines_path(client)
    pipeline_id = create(client, path, timer_graph(30))

    assert client.get(f"{path}/{pipeline_id}/timer").json() == {
        "running": False,
        "revision_id": None,
        "interval_seconds": None,
    }

    start = client.post(f"{path}/{pipeline_id}/timer/start")
    assert start.status_code == 201, start.text
    started = start.json()
    assert started["running"] is True
    assert started["interval_seconds"] == 30

    status = client.get(f"{path}/{pipeline_id}/timer")
    assert status.json() == started

    again = client.post(f"{path}/{pipeline_id}/timer/start")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "timer_already_running"

    stop = client.post(f"{path}/{pipeline_id}/timer/stop")
    assert stop.status_code == 200
    assert stop.json() == {
        "running": False,
        "revision_id": None,
        "interval_seconds": None,
    }

    stop_again = client.post(f"{path}/{pipeline_id}/timer/stop")
    assert stop_again.status_code == 404
    assert stop_again.json()["error"]["code"] == "timer_not_running"


def test_timer_start_without_a_timer_trigger_is_structured_422(client: TestClient):
    path = pipelines_path(client)
    pipeline_id = create(client, path, manual_graph())

    response = client.post(f"{path}/{pipeline_id}/timer/start")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "timer_trigger_missing"


def test_timer_start_with_invalid_interval_is_structured_422(client: TestClient):
    path = pipelines_path(client)
    graph = timer_graph(1)
    graph["nodes"][0]["config"]["interval_seconds"] = 0  # saved unvalidated (#21)
    pipeline_id = create(client, path, graph)

    response = client.post(f"{path}/{pipeline_id}/timer/start")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_trigger_config"


def test_timer_ticks_create_isolated_runs_without_overlap(client: TestClient):
    path = pipelines_path(client)
    pipeline_id = create(client, path, timer_graph(1))

    client.post(f"{path}/{pipeline_id}/timer/start")
    time.sleep(2.3)
    client.post(f"{path}/{pipeline_id}/timer/stop")

    runs = client.get("/api/v1/runs", params={"pipeline_id": pipeline_id}).json()
    assert 1 <= runs["total"] <= 3
    assert all(item["state"] == "succeeded" for item in runs["items"])


def test_shutdown_stops_every_running_timer_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """No background thread survives the app lifespan ending (#29)."""
    monkeypatch.setattr(settings, "metadata_path", tmp_path / "shutdown.sqlite3")
    with TestClient(app) as client:
        path = pipelines_path(client)
        pipeline_id = create(client, path, timer_graph(30))
        start = client.post(f"{path}/{pipeline_id}/timer/start")
        assert start.status_code == 201
        assert any(t.name == f"timer-{pipeline_id}" for t in threading.enumerate())
    assert not any(t.name == f"timer-{pipeline_id}" for t in threading.enumerate())
