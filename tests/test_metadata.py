"""Real file-backed SQLite, migration and portability boundary checks for #7."""

import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, insert, inspect, select, text
from sqlalchemy.exc import IntegrityError, StatementError

from app.config import settings
from app.main import app
from app.metadata.database import Database
from app.metadata.migrate import check, downgrade, upgrade
from app.metadata.models import (
    Base,
    BlockRegistryEntry,
    OutputEndpoint,
    Pipeline,
    PipelineRevision,
    Project,
    Run,
    WorkspaceBinding,
)
from app.metadata.portable import portable_definition

ROOT = Path(__file__).resolve().parents[1]
GRAPH: dict[str, Any] = {
    "schema_version": 1,
    "nodes": [{"id": "source", "block_id": "csv.read", "resource_id": "input"}],
    "edges": [],
    "config": {"delimiter": ",", "columns": ["name", "value"], "limit": 10},
}


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "nested % workspace" / "metadata.sqlite3")
    upgrade(database)
    yield database
    database.close()


@pytest.fixture
def seeded(database: Database) -> Database:
    with database.transaction() as session:
        project = Project(id="project", name="Example")
        pipeline = Pipeline(id="pipeline", project=project, name="Import")
        revision = PipelineRevision(
            id="revision", pipeline=pipeline, revision=1, definition=GRAPH
        )
        session.add(Run(id="run", pipeline_revision=revision))
    return database


def test_complete_metadata_survives_reopening(seeded: Database):
    with seeded.transaction() as session:
        session.add_all(
            [
                WorkspaceBinding(
                    project_id="project",
                    resource_id="input",
                    local_path="C:/private/data.csv",
                    secret_reference="os-keyring:source",
                ),
                BlockRegistryEntry(
                    block_id="csv.read",
                    version="1",
                    name="Read CSV",
                    category="source",
                    public_metadata={"inputs": [], "outputs": ["table"]},
                ),
                OutputEndpoint(
                    run_id="run",
                    node_id="source",
                    name="table",
                    format="csv",
                    artifact_ref="output-resource",
                    row_count=0,
                ),
            ]
        )
    seeded.close()
    reopened = Database(seeded.path)
    try:
        with reopened.transaction() as session:
            run = session.get(Run, "run")
            assert run is not None
            assert run.state == "queued" and run.row_count is None
            revision = run.pipeline_revision
            assert revision.pipeline.project.name == "Example"
            assert revision.definition == GRAPH
            assert revision.created_at.tzinfo is None
            exported = json.dumps(revision.definition)
            assert "private" not in exported and "os-keyring" not in exported
            assert run.outputs[0].row_count == 0
            assert revision.pipeline.project.bindings[0].secret_reference is not None
            assert session.get(BlockRegistryEntry, ("csv.read", "1")) is not None
    finally:
        reopened.close()


def test_transaction_rolls_back_earlier_flushed_writes(database: Database):
    with pytest.raises(IntegrityError), database.transaction() as session:
        session.add(Project(id="should-rollback", name="Valid"))
        session.flush()
        session.add(Pipeline(project_id="missing-parent", name="Invalid"))
    with database.transaction() as session:
        assert session.get(Project, "should-rollback") is None
        session.add(Project(id="next-transaction", name="Still usable"))
    with database.transaction() as session:
        assert session.get(Project, "next-transaction") is not None


def test_exception_rolls_back_session_and_ddl(database: Database):
    with pytest.raises(RuntimeError), database.transaction() as session:
        session.add(Project(id="rollback", name="Rollback"))
        session.flush()
        session.execute(text("CREATE TABLE temporary_ddl (id INTEGER)"))
        raise RuntimeError("synthetic failure")
    assert "temporary_ddl" not in inspect(database.engine).get_table_names()
    with database.transaction() as session:
        assert session.get(Project, "rollback") is None


@pytest.mark.parametrize("reconnect", [False, True])
def test_foreign_keys_apply_to_each_connection(database: Database, reconnect: bool):
    if reconnect:
        database.engine.dispose()
    with database.engine.connect() as first, database.engine.connect() as second:
        for connection in (first, second):
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar() == 5000
    with pytest.raises(IntegrityError), database.transaction() as session:
        session.add(Run(pipeline_revision_id="nonexistent"))


@pytest.mark.parametrize(
    "model,values",
    [
        (Project, {"name": " "}),
        (Project, {"name": "x" * 129}),
        (Pipeline, {"project_id": "project", "name": "Import"}),
        (
            PipelineRevision,
            {"pipeline_id": "pipeline", "revision": 1, "definition": GRAPH},
        ),
        (
            PipelineRevision,
            {"pipeline_id": "pipeline", "revision": 0, "definition": GRAPH},
        ),
        (Run, {"pipeline_revision_id": "revision", "state": "unknown"}),
        (Run, {"pipeline_revision_id": "revision", "row_count": -1}),
        (Run, {"pipeline_revision_id": "revision", "ended_at": datetime(2026, 1, 1)}),
        (
            Run,
            {
                "pipeline_revision_id": "revision",
                "started_at": datetime(2026, 1, 2),
                "ended_at": datetime(2026, 1, 1),
            },
        ),
        (WorkspaceBinding, {"project_id": "project", "resource_id": "input"}),
        (
            WorkspaceBinding,
            {"project_id": "project", "resource_id": " ", "local_path": "data.csv"},
        ),
        (
            OutputEndpoint,
            {
                "run_id": "run",
                "node_id": "n",
                "name": "x",
                "format": "invalid",
                "artifact_ref": "resource",
            },
        ),
        (
            OutputEndpoint,
            {
                "run_id": "run",
                "node_id": "n",
                "name": "x",
                "format": "csv",
                "artifact_ref": " ",
            },
        ),
        (
            OutputEndpoint,
            {
                "run_id": "run",
                "node_id": "n",
                "name": "x",
                "format": "csv",
                "artifact_ref": "resource",
                "row_count": -1,
            },
        ),
    ],
)
def test_database_constraints(
    seeded: Database, model: type[Base], values: dict[str, Any]
):
    with pytest.raises(IntegrityError), seeded.transaction() as session:
        session.add(model(**values))


def test_binding_registry_and_output_unique_identities(seeded: Database):
    factories: list[Callable[[], Base]] = [
        lambda: WorkspaceBinding(
            project_id="project", resource_id="input", local_path="data.csv"
        ),
        lambda: BlockRegistryEntry(
            block_id="csv.read",
            version="1",
            name="CSV",
            category="source",
            public_metadata={},
        ),
        lambda: OutputEndpoint(
            run_id="run",
            node_id="n",
            name="table",
            format="csv",
            artifact_ref="resource",
        ),
    ]
    for factory in factories:
        with seeded.transaction() as session:
            session.add(factory())
        with pytest.raises(IntegrityError), seeded.transaction() as session:
            session.add(factory())


def test_run_updates_allow_normal_execution_lifecycle(seeded: Database):
    start = datetime(2026, 1, 1)
    with seeded.transaction() as session:
        run = session.get(Run, "run")
        assert run is not None
        run.state, run.started_at = "running", start
    with seeded.transaction() as session:
        run = session.get(Run, "run")
        assert run is not None
        run.state, run.row_count = "succeeded", 7
        run.ended_at = start + timedelta(seconds=2)
    with seeded.transaction() as session:
        assert session.scalar(select(Run.row_count).where(Run.id == "run")) == 7


@pytest.mark.parametrize(
    "model,identity",
    [
        (Project, "project"),
        (Pipeline, "pipeline"),
        (PipelineRevision, "revision"),
        (Run, "run"),
    ],
)
def test_referenced_history_cannot_be_deleted(
    seeded: Database, model: type[Base], identity: str
):
    if model is Run:
        with seeded.transaction() as session:
            session.add(
                OutputEndpoint(
                    run_id="run",
                    node_id="n",
                    name="table",
                    format="csv",
                    artifact_ref="resource",
                )
            )
    with pytest.raises(IntegrityError), seeded.transaction() as session:
        session.execute(delete(model).where(model.id == identity))  # type: ignore[attr-defined]


def test_revision_history_is_immutable_and_runs_keep_original(seeded: Database):
    with seeded.transaction() as session:
        original = session.get(PipelineRevision, "revision")
        assert original is not None
        detached = original.definition
        detached["nodes"].append({"id": "new"})
        assert original.definition == GRAPH
        with pytest.raises(ValueError, match="immutable"):
            original.definition = detached
        session.add(
            PipelineRevision(
                id="revision-2", pipeline_id="pipeline", revision=2, definition=detached
            )
        )
    with pytest.raises(ValueError, match="immutable"), seeded.transaction() as session:
        original = session.get(PipelineRevision, "revision")
        assert original is not None
        original.revision = 3
    with seeded.transaction() as session:
        run = session.get(Run, "run")
        assert run is not None
        assert run.pipeline_revision.revision == 1
        assert run.pipeline_revision.definition == GRAPH
        assert session.get(PipelineRevision, "revision-2") is not None


@pytest.mark.parametrize(
    "value",
    [
        {"config": {"local_path": "relative.csv"}},
        {"nested": [{"secretReference": "keyring:source"}]},
        {"nodes": [{"config": {"API-Key": "synthetic"}}]},
        {"config": {"password": "synthetic"}},
        {"config": {"connection_string": "synthetic"}},
        {"input": "C:\\private\\file.csv"},
        {"input": "/private/file.csv"},
        {"input": "\\\\server\\share\\file.csv"},
        {"input": "FILE:///private/file.csv"},
        {"input": "C:relative-drive.csv"},
        {"input": float("nan")},
        {"input": float("inf")},
        {"input": ({"password": "synthetic"},)},
        {1: "non-string-key"},
    ],
)
def test_portable_definition_rejects_runtime_fields(value: dict[str, Any]):
    with pytest.raises(ValueError):
        portable_definition(value)


def test_portable_definition_is_detached_and_json_only():
    original = {"resource_id": "input", "settings": [True, None, 1.5, "value"]}
    exported = portable_definition(original)
    assert exported == original
    exported["settings"].append("new")
    assert len(original["settings"]) == 4
    with pytest.raises(TypeError):
        portable_definition({"object": Path("data.csv")})
    with pytest.raises(ValueError, match="JSON object"):
        portable_definition([])  # type: ignore[arg-type]


@pytest.mark.parametrize("definition", [{"path": "relative.csv"}, None])
def test_core_insert_also_enforces_portability(seeded: Database, definition: Any):
    with pytest.raises(StatementError), seeded.transaction() as session:
        session.execute(
            insert(Base.metadata.tables["pipeline_revisions"]).values(
                id="core", pipeline_id="pipeline", revision=2, definition=definition
            )
        )


def test_migration_round_trip_and_schema_drift(database: Database):
    expected = set(Base.metadata.tables)
    assert set(inspect(database.engine).get_table_names()) == expected | {
        "alembic_version"
    }
    upgrade(database)
    check(database)
    for table, columns in [
        ("pipelines", ["project_id"]),
        ("pipeline_revisions", ["pipeline_id"]),
        ("runs", ["pipeline_revision_id"]),
        ("output_endpoints", ["run_id"]),
        ("block_registry", ["category"]),
        ("workspace_bindings", ["project_id"]),
    ]:
        assert any(
            index["column_names"] == columns
            for index in inspect(database.engine).get_indexes(table)
        )
    with database.engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE unrelated (id INTEGER)")
        connection.exec_driver_sql("INSERT INTO unrelated VALUES (42)")
    downgrade(database)
    assert set(inspect(database.engine).get_table_names()) == {
        "alembic_version",
        "unrelated",
    }
    with database.engine.begin() as connection:
        assert connection.exec_driver_sql("SELECT id FROM unrelated").scalar() == 42
        connection.exec_driver_sql("DROP TABLE unrelated")
    upgrade(database)
    check(database)


def test_failed_initial_migration_rolls_back_tables_and_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from alembic import operations

    database = Database(tmp_path / "failed.sqlite3")
    original = operations.Operations.create_table

    def failing_create(self: Any, table_name: str, *args: Any, **kwargs: Any) -> Any:
        result = original(self, table_name, *args, **kwargs)
        if table_name == "pipeline_revisions":
            raise RuntimeError("synthetic migration failure")
        return result

    try:
        with monkeypatch.context() as patch:
            patch.setattr(operations.Operations, "create_table", failing_create)
            with pytest.raises(RuntimeError, match="synthetic migration failure"):
                upgrade(database)
        assert inspect(database.engine).get_table_names() == []
        upgrade(database)
        check(database)
    finally:
        database.close()


def test_api_startup_migrates_and_reuses_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    path = tmp_path / "api.sqlite3"
    monkeypatch.setattr(settings, "metadata_path", path)
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        with cast(Database, app.state.database).transaction() as session:
            session.add(Project(id="startup", name="Persisted"))
    assert app.state.database is None
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/v1/example", json={"name": "test", "count": 1}
            ).status_code
            == 200
        )
        with cast(Database, app.state.database).transaction() as session:
            assert session.get(Project, "startup") is not None
    assert app.state.database is None


def test_api_refuses_unknown_migration_version(
    database: Database, monkeypatch: pytest.MonkeyPatch
):
    with database.engine.begin() as connection:
        connection.exec_driver_sql("UPDATE alembic_version SET version_num='unknown'")
    monkeypatch.setattr(settings, "metadata_path", database.path)
    with pytest.raises(Exception, match="unknown"), TestClient(app):
        pytest.fail("Startup must fail before serving requests")
    assert app.state.database is None


def test_import_does_not_create_database_and_downgrade_requires_confirmation(
    tmp_path: Path,
):
    path = tmp_path / "not-created" / "metadata.sqlite3"
    environment = dict(os.environ, LPS_METADATA_PATH=str(path), PYTHONPATH=str(ROOT))
    imported = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert imported.returncode == 0, imported.stderr
    assert not path.parent.exists()
    refused = subprocess.run(
        [sys.executable, "-m", "app.metadata.migrate", "downgrade"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert refused.returncode == 2
    assert "confirm-data-loss" in refused.stderr
    assert not path.parent.exists()
