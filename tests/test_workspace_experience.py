# AI contribution: 50% or more AI-generated
"""Workspace switching, named folders, migration and downloadable run evidence."""

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.config import settings
from app.main import app
from app.metadata.models import (
    Pipeline,
    PipelineRevision,
    Project,
    RunEvent,
    WorkspaceBinding,
)
from app.workspace_storage import initialize_workspace_storage, pipeline_data_folder


def graph() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "nodes": [
            {
                "id": "source",
                "block_id": "source.json",
                "block_version": "1.0.0",
                "config": {"resource_ref": "inputs/readings.json"},
            },
            {
                "id": "sink",
                "block_id": "sink.parquet",
                "block_version": "1.0.0",
                "config": {"resource_ref": "outputs/results.parquet"},
            },
        ],
        "edges": [
            {
                "id": "link",
                "source": {"node_id": "source", "port": "table"},
                "target": {"node_id": "sink", "port": "table"},
            }
        ],
    }


def create(
    client: TestClient,
    project_name: str = "Factory Reports",
    pipeline_name: str = "Daily Production",
) -> tuple[str, str]:
    project = client.post("/api/v1/projects", json={"name": project_name})
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]
    pipeline = client.post(
        f"/api/v1/projects/{project_id}/pipelines",
        json={"name": pipeline_name, "definition": graph()},
    )
    assert pipeline.status_code == 201, pipeline.text
    return project_id, pipeline.json()["id"]


def test_switching_workspaces_reloads_only_their_projects_and_pipelines(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root_a = settings.workspace_root
    assert root_a is not None
    project_a, pipeline_a = create(client)
    folder_a = root_a / "Factory Reports" / "Daily Production"
    assert (folder_a / "inputs").is_dir()
    assert not (root_a / project_a).exists()
    (folder_a / "inputs/readings.json").write_text('[{"value": 4}]', encoding="utf-8")
    preview = client.post(
        f"/api/v1/projects/{project_a}/pipelines/preview",
        json={
            "pipeline_id": pipeline_a,
            "definition": {"nodes": graph()["nodes"][:1], "edges": []},
            "node_id": "source",
        },
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["rows"] == [{"value": 4}]
    executed = client.post(
        f"/api/v1/projects/{project_a}/pipelines/{pipeline_a}/execute"
    )
    assert executed.status_code == 201, executed.text
    run_id = executed.json()["run_id"]
    detail = client.get(f"/api/v1/runs/{run_id}").json()
    assert detail["state"] == "succeeded", detail
    artifact_id = detail["outputs"][0]["id"]
    assert (
        client.post(f"/api/v1/artifacts/{artifact_id}/query", json={}).status_code
        == 200
    )

    root_b = tmp_path / "Other workspace"
    root_b.mkdir()
    monkeypatch.setattr(settings, "allowed_workspace_roots", [root_b])
    url = "/api/v1/settings/workspace"
    client.put(url, json={"root_path": str(root_b)}).raise_for_status()
    assert client.get("/api/v1/projects").json()["items"] == []
    assert client.get(f"/api/v1/projects/{project_a}/pipelines").status_code == 404
    assert client.get(f"/api/v1/runs/{run_id}").status_code == 404
    assert client.get(f"/api/v1/runs/{run_id}/log").status_code == 404
    assert client.get(f"/api/v1/artifacts/{artifact_id}").status_code == 404
    project_b, _ = create(client)
    assert [item["id"] for item in client.get("/api/v1/projects").json()["items"]] == [
        project_b
    ]
    assert not (
        root_b / "Factory Reports" / "Daily Production" / "inputs/readings.json"
    ).exists()
    client.put(url, json={"root_path": str(root_a)}).raise_for_status()
    assert [item["id"] for item in client.get("/api/v1/projects").json()["items"]] == [
        project_a
    ]
    assert (
        client.get(f"/api/v1/projects/{project_a}/pipelines").json()["items"][0]["id"]
        == pipeline_a
    )
    assert (
        client.post(f"/api/v1/artifacts/{artifact_id}/query", json={}).status_code
        == 200
    )


def test_pipeline_rename_moves_inputs_and_keeps_history_accessible(
    client: TestClient,
) -> None:
    project, pipeline = create(client)
    folder = pipeline_data_folder(app.state.database, pipeline)
    (folder / "inputs/readings.json").write_text('[{"value":1}]', encoding="utf-8")
    run = client.post(
        f"/api/v1/projects/{project}/pipelines/{pipeline}/execute"
    ).json()["run_id"]
    artifact = client.get(f"/api/v1/runs/{run}").json()["outputs"][0]["id"]
    renamed = client.patch(
        f"/api/v1/projects/{project}/pipelines/{pipeline}",
        json={"name": "Renamed Pipeline", "expected_revision": 1},
    )
    assert renamed.status_code == 200, renamed.text
    assert not folder.exists()
    assert (folder.parent / "Renamed Pipeline/inputs/readings.json").is_file()
    assert (
        client.post(f"/api/v1/artifacts/{artifact}/query", json={}).status_code == 200
    )


def test_migration_copies_legacy_data_and_retains_originals(client: TestClient) -> None:
    root = settings.workspace_root
    assert root is not None
    with app.state.database.transaction() as session:
        project = Project(name="Legacy project")
        session.add(project)
        session.flush()
        pipeline = Pipeline(project_id=project.id, name="Imported pipeline")
        session.add(pipeline)
        session.flush()
        session.add(
            PipelineRevision(pipeline_id=pipeline.id, revision=1, definition=graph())
        )
        project_id, pipeline_id = project.id, pipeline.id
    original = root / project_id / "inputs"
    original.mkdir(parents=True)
    (original / "readings.json").write_text('[{"value":5}]', encoding="utf-8")
    with app.state.database.transaction() as session:
        session.add(
            WorkspaceBinding(
                project_id=project_id,
                resource_id="private.json",
                local_path=str(original / "readings.json"),
            )
        )
    initialize_workspace_storage(app.state.database)
    copied = root / "Legacy project/Imported pipeline/inputs/readings.json"
    assert copied.read_bytes() == (original / "readings.json").read_bytes()
    assert (
        pipeline_data_folder(app.state.database, pipeline_id).name
        == "Imported pipeline"
    )

    with app.state.database.transaction() as session:
        binding = session.scalar(
            select(WorkspaceBinding).where(WorkspaceBinding.project_id == project_id)
        )
        assert Path(binding.local_path) == Path("inputs/readings.json")
    source = graph()["nodes"][0] | {"config": {"resource_ref": "private.json"}}
    preview = client.post(
        f"/api/v1/projects/{project_id}/pipelines/preview",
        json={
            "pipeline_id": pipeline_id,
            "definition": {"nodes": [source], "edges": []},
            "node_id": "source",
        },
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["rows"] == [{"value": 5}]


def test_download_contains_all_events_and_redacts_legacy_text(
    client: TestClient,
) -> None:
    project, pipeline = create(client)
    folder = pipeline_data_folder(app.state.database, pipeline)
    (folder / "inputs/readings.json").write_text('[{"value":1}]', encoding="utf-8")
    run = client.post(
        f"/api/v1/projects/{project}/pipelines/{pipeline}/execute"
    ).json()["run_id"]
    with app.state.database.transaction() as session:
        last = max(
            session.scalars(select(RunEvent.sequence).where(RunEvent.run_id == run))
        )
        for index in range(151):
            session.add(
                RunEvent(
                    run_id=run,
                    sequence=last + index + 1,
                    level="info",
                    kind="test",
                    message=f"Event-{index:03} password=private-value",
                )
            )
    response = client.get(f"/api/v1/runs/{run}/log")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    assert "Event-000" in response.text and "Event-150" in response.text
    assert "private-value" not in response.text
    assert "[REDACTED]" in response.text


def test_duplicate_names_get_readable_unique_directories(client: TestClient) -> None:
    first, _ = create(client, "Plant", "Conveyor")
    second, _ = create(client, "plant", "Conveyor")
    with app.state.database.transaction() as session:
        a, b = session.get(Project, first), session.get(Project, second)
        assert a.directory_name == "Plant"
        assert b.directory_name == "plant (2)"


def test_rename_conflicts_keep_the_original_folder_and_revision(
    client: TestClient,
) -> None:
    project, pipeline = create(client)
    original = pipeline_data_folder(app.state.database, pipeline)
    (original / "inputs/kept.txt").write_text("keep", encoding="utf-8")
    duplicate = client.post(
        f"/api/v1/projects/{project}/pipelines",
        json={"name": "Already exists", "definition": graph()},
    )
    assert duplicate.status_code == 201
    result = client.patch(
        f"/api/v1/projects/{project}/pipelines/{pipeline}",
        json={"name": "Already exists", "expected_revision": 1},
    )
    assert result.status_code == 409
    assert (original / "inputs/kept.txt").read_text() == "keep"
    assert (
        client.get(f"/api/v1/projects/{project}/pipelines/{pipeline}").json()[
            "revision"
        ]
        == 1
    )


def test_folder_rename_cannot_race_a_run_before_telemetry_is_created(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from app.pipelines import api

    project, pipeline = create(client)
    original = pipeline_data_folder(app.state.database, pipeline)
    (original / "inputs/readings.json").write_text('[{"value": 1}]', encoding="utf-8")
    entered, release = Event(), Event()
    from app.runs import execute_revision as execute

    def delayed(*args: Any, **kwargs: Any) -> Any:
        entered.set()
        assert release.wait(5)
        return execute(*args, **kwargs)

    monkeypatch.setattr(api, "execute_revision", delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(
            client.post, f"/api/v1/projects/{project}/pipelines/{pipeline}/execute"
        )
        try:
            assert entered.wait(3)
            renamed = client.patch(
                f"/api/v1/projects/{project}/pipelines/{pipeline}",
                json={"name": "Unsafe rename", "expected_revision": 1},
            )
            assert renamed.status_code == 409, renamed.text
            assert original.is_dir()
        finally:
            release.set()
        assert pending.result().json()["state"] == "succeeded"


def test_timer_keeps_its_original_workspace_after_switch(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.blocks.catalog import executor
    from app.execution import Cancellation
    from app.runs.scheduler import _Timer

    project, pipeline = create(client)
    folder = pipeline_data_folder(app.state.database, pipeline)
    (folder / "inputs/readings.json").write_text('[{"value": 1}]', encoding="utf-8")
    with app.state.database.transaction() as session:
        revision = session.scalar(
            select(PipelineRevision.id).where(PipelineRevision.pipeline_id == pipeline)
        )
    root = settings.workspace_root
    other = tmp_path / "Other root"
    other.mkdir()
    monkeypatch.setattr(settings, "allowed_workspace_roots", [other])
    client.put(
        "/api/v1/settings/workspace", json={"root_path": str(other)}
    ).raise_for_status()
    timer = _Timer(app.state.database, executor, pipeline, revision, 60, None)
    timer._run_once(Cancellation())
    assert (folder / "outputs/results.parquet").is_file()
    assert client.get("/api/v1/runs").json()["items"] == []
    client.put(
        "/api/v1/settings/workspace", json={"root_path": str(root)}
    ).raise_for_status()
    assert client.get("/api/v1/runs").json()["items"][0]["state"] == "succeeded"
