"""Fault-injection acceptance cases for execution and publication (#34)."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.blocks.catalog import executor
from app.blocks.context import BlockContext
from app.artifacts.registration import register_published_artifacts
from app.artifacts import ArtifactQuery, ArtifactUnavailable, query_artifact
from app.blocks.contracts import Table
from app.blocks.file_sinks import CsvSink, FileSink, ParquetSink, SinkConfig
from app.blocks.errors import BlockError
from app.blocks.sql import SqlSource
from app.execution import Cancellation, ExecutionLimits, Executor
from app.metadata.database import Database
from app.metadata.migrate import upgrade
from app.metadata.models import OutputEndpoint, Run
from app.runs import RunRecorder, execute_revision, recover_interrupted
from app.sources.sql import SqlSourceError
from tests.run_support import seed_revision


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "failures.sqlite3")
    upgrade(database)
    try:
        yield database
    finally:
        database.close()


def pipeline(format_: str = "parquet", overwrite: str = "replace") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "nodes": [
            {
                "id": "source",
                "block_id": "source.csv",
                "block_version": "1.0.0",
                "config": {"resource_ref": "input.csv"},
            },
            {
                "id": "select",
                "block_id": "transform.select",
                "block_version": "1.0.0",
                "config": {"columns": ["sensor", "reading"]},
            },
            {
                "id": "sink",
                "block_id": f"sink.{format_}",
                "block_version": "1.0.0",
                "config": {
                    "resource_ref": f"result.{format_}",
                    "overwrite": overwrite,
                },
            },
        ],
        "edges": [
            {
                "id": "source-select",
                "source": {"node_id": "source", "port": "table"},
                "target": {"node_id": "select", "port": "table"},
            },
            {
                "id": "select-sink",
                "source": {"node_id": "select", "port": "table"},
                "target": {"node_id": "sink", "port": "table"},
            },
        ],
    }


def input_file(root: Path, text: str = "sensor,reading\nA,10\nB,20\n") -> None:
    (root / "input.csv").write_text(text, encoding="utf-8")


@pytest.mark.parametrize("format_", ["csv", "parquet"])
@pytest.mark.parametrize("fault", ["source", "transform", "write", "flush", "publish"])
def test_failed_stage_preserves_target_and_registers_no_output(
    db: Database,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    format_: str,
    fault: str,
):
    input_file(tmp_path)
    graph = pipeline(format_)
    if fault == "source":
        graph["nodes"][0]["config"]["resource_ref"] = "missing.csv"
    elif fault == "transform":
        graph["nodes"][1]["config"]["columns"] = ["missing_column"]
    target = tmp_path / f"result.{format_}"
    target.write_bytes(b"previous successful output")

    def broken_write(
        self: FileSink, path: Path, table: Table, config: SinkConfig
    ) -> None:
        path.write_bytes(b"partial")
        raise OSError("synthetic private write failure")

    def broken_io(*args: Any, **kwargs: Any) -> None:
        raise OSError("synthetic private I/O failure")

    if fault == "write":
        monkeypatch.setattr(
            CsvSink if format_ == "csv" else ParquetSink, "_write", broken_write
        )
    elif fault == "flush":
        monkeypatch.setattr("app.blocks.file_sinks.os.fsync", broken_io)
    elif fault == "publish":
        monkeypatch.setattr("app.blocks.file_sinks.os.replace", broken_io)
    outcome = execute_revision(
        db, executor, seed_revision(db, graph), workspace_root=tmp_path
    )
    failed_node = {"source": "source", "transform": "select"}.get(fault, "sink")
    assert outcome.state == "failed"
    assert outcome.context.node_states[failed_node] == "failed"
    if failed_node != "sink":
        assert outcome.context.node_states["sink"] == "skipped"
    assert target.read_bytes() == b"previous successful output"
    assert not list(tmp_path.glob(".lps-*.tmp"))
    with db.transaction() as session:
        run = session.get(Run, outcome.run_id)
        assert run is not None and run.state == "failed" and run.ended_at is not None
        assert run.row_count is None
        assert session.scalars(select(OutputEndpoint)).all() == []
        assert all(
            block.state in {"completed", "failed", "skipped"} for block in run.blocks
        )


@pytest.mark.parametrize("format_", ["csv", "parquet"])
@pytest.mark.parametrize("checkpoint", ["write", "flush"])
def test_cancellation_before_publication_preserves_previous_output(
    db: Database,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    format_: str,
    checkpoint: str,
):
    input_file(tmp_path)
    token = Cancellation()
    target = tmp_path / f"result.{format_}"
    target.write_bytes(b"previous")
    sink_type = CsvSink if format_ == "csv" else ParquetSink
    original_write = sink_type()._write

    def cancel_after_write(
        self: FileSink, path: Path, table: Table, config: SinkConfig
    ) -> None:
        original_write(path, table, config)
        token.cancel()

    if checkpoint == "write":
        monkeypatch.setattr(sink_type, "_write", cancel_after_write)
    else:
        monkeypatch.setattr("app.blocks.file_sinks.os.fsync", lambda _: token.cancel())
    outcome = execute_revision(
        db,
        executor,
        seed_revision(db, pipeline(format_)),
        workspace_root=tmp_path,
        cancellation=token,
    )
    assert outcome.state == "cancelled"
    assert outcome.context.failures["sink"].code == "cancelled"
    assert target.read_bytes() == b"previous"
    assert not list(tmp_path.glob(".lps-*.tmp"))
    with db.transaction() as session:
        assert session.scalars(select(OutputEndpoint)).all() == []


@pytest.mark.parametrize("format_", ["csv", "parquet"])
def test_repeat_failure_recovery_and_empty_output(
    db: Database, tmp_path: Path, format_: str
):
    revision = seed_revision(db, pipeline(format_))
    outcomes = []
    for text, state, count in (
        ("sensor,reading\nA,10\nB,20\n", "succeeded", 2),
        ("wrong,header\nA,10\n", "failed", None),
        ("sensor,reading\n", "succeeded", 0),
        ("sensor,reading\nC,30\n", "succeeded", 1),
    ):
        input_file(tmp_path, text)
        outcome = execute_revision(db, executor, revision, workspace_root=tmp_path)
        outcomes.append(outcome)
        assert outcome.state == state
        with db.transaction() as session:
            run = session.get(Run, outcome.run_id)
            assert run is not None and run.row_count == count
            assert len(run.outputs) == (0 if state == "failed" else 1)
            if run.outputs:
                assert run.outputs[0].row_count == count
                assert [c["name"] for c in run.outputs[0].schema_json["columns"]] == [
                    "sensor",
                    "reading",
                ]
            assert {b.run_id for b in run.blocks} == {outcome.run_id}
            assert {e.run_id for e in run.events} == {outcome.run_id}
    assert len({o.run_id for o in outcomes}) == 4


@pytest.mark.parametrize("failure", ["registration", "commit"])
def test_finalization_failure_rolls_back_outputs_and_closes_run(
    db: Database,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
):
    input_file(tmp_path)
    revision = seed_revision(db, pipeline())
    if failure == "registration":
        from app.runs import recorder as module

        original = register_published_artifacts

        def fail_registration(*args: Any, **kwargs: Any) -> None:
            original(*args, **kwargs)
            raise RuntimeError("injected finalization failure")

        monkeypatch.setattr(module, "register_published_artifacts", fail_registration)

    failed_once = False

    def fail_commit(session: Session) -> None:
        nonlocal failed_once
        if not failed_once and any(
            isinstance(obj, Run) and obj.state == "succeeded" for obj in session.dirty
        ):
            failed_once = True
            raise RuntimeError("injected finalization failure")

    if failure == "commit":
        event.listen(db.sessions.class_, "before_commit", fail_commit)
    try:
        with pytest.raises(RuntimeError, match="injected finalization"):
            execute_revision(db, executor, revision, workspace_root=tmp_path)
    finally:
        if failure == "commit":
            event.remove(db.sessions.class_, "before_commit", fail_commit)
    with db.transaction() as session:
        run = session.scalars(select(Run)).one()
        assert run.state == "failed" and run.error_code == "execution_failed"
        assert run.ended_at is not None
        assert run.outputs == []
        assert all(b.state in {"completed", "failed", "skipped"} for b in run.blocks)
    assert recover_interrupted(db) == []
    # The filesystem and SQLite are separate transactions; keep the complete file.
    assert (tmp_path / "result.parquet").is_file()


def test_secondary_abort_failure_preserves_primary_error(
    db: Database,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    input_file(tmp_path)
    revision = seed_revision(db, pipeline())

    def fail_finish(*args: Any, **kwargs: Any) -> str:
        raise RuntimeError("primary finalization failure")

    def fail_abort(*args: Any, **kwargs: Any) -> None:
        raise OSError("password=private-abort-detail")

    with monkeypatch.context() as scoped:
        scoped.setattr(RunRecorder, "finish", fail_finish)
        scoped.setattr(RunRecorder, "abort", fail_abort)
        with pytest.raises(RuntimeError, match="primary finalization"):
            execute_revision(db, executor, revision, workspace_root=tmp_path)
    assert "private-abort-detail" not in caplog.text
    assert len(recover_interrupted(db)) == 1
    with db.transaction() as session:
        assert session.scalars(select(Run)).one().state == "failed"


def test_completed_branch_is_registered_when_an_independent_branch_fails(
    db: Database, tmp_path: Path
):
    input_file(tmp_path)
    graph = pipeline()
    graph["nodes"].append(
        {
            "id": "unrelated",
            "block_id": "source.csv",
            "block_version": "1.0.0",
            "config": {"resource_ref": "missing.csv"},
        }
    )
    outcome = execute_revision(
        db, executor, seed_revision(db, graph), workspace_root=tmp_path
    )
    assert outcome.state == "failed"
    assert outcome.context.node_states["sink"] == "completed"
    with db.transaction() as session:
        artifact = session.scalars(select(OutputEndpoint)).one()
        assert artifact.run_id == outcome.run_id and artifact.node_id == "sink"


@pytest.mark.parametrize("overwrite", ["error", "replace"])
def test_repeat_no_clobber_and_explicit_replace(
    db: Database, tmp_path: Path, overwrite: str
):
    input_file(tmp_path)
    revision = seed_revision(db, pipeline(overwrite=overwrite))
    first = execute_revision(db, executor, revision, workspace_root=tmp_path)
    original = (tmp_path / "result.parquet").read_bytes()
    input_file(tmp_path, "sensor,reading\nC,99\n")
    second = execute_revision(db, executor, revision, workspace_root=tmp_path)
    assert first.state == "succeeded"
    assert first.run_id != second.run_id
    with db.transaction() as session:
        run = session.get(Run, second.run_id)
        assert run is not None
        if overwrite == "error":
            assert second.state == "failed" and run.outputs == []
            assert second.context.failures["sink"].code == "output_exists"
            assert (tmp_path / "result.parquet").read_bytes() == original
        else:
            assert second.state == "succeeded" and run.outputs[0].row_count == 1
            assert (tmp_path / "result.parquet").read_bytes() != original


def test_duckdb_connection_closes_after_query_failure(
    db: Database, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    input_file(tmp_path)
    execute_revision(
        db, executor, seed_revision(db, pipeline()), workspace_root=tmp_path
    )
    with db.transaction() as session:
        artifact_id = session.scalars(select(OutputEndpoint)).one().id
    connection = Mock()
    connection.execute.side_effect = RuntimeError("private query failure")
    monkeypatch.setattr("duckdb.connect", lambda **kwargs: connection)
    with pytest.raises(ArtifactUnavailable, match="could not be queried"):
        query_artifact(db, artifact_id, tmp_path, ArtifactQuery())
    connection.close.assert_called_once_with()


@pytest.mark.parametrize("cancelled", [False, True])
def test_sql_connection_closes_after_query_error_or_cancellation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cancelled: bool
):
    path = tmp_path / "source.sqlite3"
    original_connect = sqlite3.connect
    with original_connect(path) as setup:
        setup.execute("CREATE TABLE readings (value INTEGER)")
    setup.close()
    opened: list[sqlite3.Connection] = []
    token = Cancellation()

    def connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        connection: sqlite3.Connection = original_connect(*args, **kwargs)
        opened.append(connection)
        return connection

    def fail_query(*args: Any, **kwargs: Any) -> None:
        if cancelled:
            token.cancel()
        raise SqlSourceError("synthetic query failure")

    monkeypatch.setattr("app.blocks.sql.sqlite3.connect", connect)
    monkeypatch.setattr("app.blocks.sql.execute_read_only_sqlite", fail_query)
    with pytest.raises(BlockError) as error:
        SqlSource().run(
            {
                "resource_ref": path.name,
                "query": "SELECT value FROM readings",
                "columns": ["value"],
                "types": ["integer"],
                "nullable": [False],
            },
            {},
            BlockContext(
                "run", "sql", workspace_root=tmp_path, is_cancelled=token.is_cancelled
            ),
        )
    assert error.value.failure.code == (
        "cancelled" if cancelled else "sql_query_failed"
    )
    assert len(opened) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        opened[0].execute("SELECT 1")


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, SystemExit])
def test_interrupted_writer_cleans_temporary_file_and_aborts_run(
    db: Database,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interruption: type[BaseException],
):
    input_file(tmp_path)
    target = tmp_path / "result.parquet"
    target.write_bytes(b"previous")

    def interrupted_write(
        self: FileSink, path: Path, table: Table, config: SinkConfig
    ) -> None:
        path.write_bytes(b"partial")
        raise interruption()

    monkeypatch.setattr(ParquetSink, "_write", interrupted_write)
    with pytest.raises(interruption):
        execute_revision(
            db, executor, seed_revision(db, pipeline()), workspace_root=tmp_path
        )
    assert target.read_bytes() == b"previous"
    assert not list(tmp_path.glob(".lps-*.tmp"))
    with db.transaction() as session:
        run = session.scalars(select(Run)).one()
        assert run.state == "failed" and run.outputs == []
        assert all(
            block.state in {"completed", "failed", "skipped"} for block in run.blocks
        )


@pytest.mark.parametrize("hook", ["before_execute", "after_execute"])
def test_failed_sink_lifecycle_hook_does_not_register_metadata(
    db: Database,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hook: str,
):
    input_file(tmp_path)

    def fail_hook(*args: Any, **kwargs: Any) -> None:
        raise BlockError("lifecycle_failed", "Synthetic sink lifecycle failure.")

    monkeypatch.setattr(ParquetSink, hook, fail_hook)
    outcome = execute_revision(
        db, executor, seed_revision(db, pipeline()), workspace_root=tmp_path
    )
    assert outcome.state == "failed"
    assert outcome.context.failures["sink"].code == "lifecycle_failed"
    assert (tmp_path / "result.parquet").exists() == (hook == "after_execute")
    with db.transaction() as session:
        assert session.scalars(select(OutputEndpoint)).all() == []


def test_post_publication_executor_budget_failure_does_not_register_output(
    db: Database, tmp_path: Path
):
    input_file(tmp_path)
    limited = Executor(executor.registry, ExecutionLimits(max_rows=8))
    outcome = execute_revision(
        db, limited, seed_revision(db, pipeline()), workspace_root=tmp_path
    )
    assert outcome.state == "failed"
    assert outcome.context.failures["sink"].code == "data_limit"
    assert (tmp_path / "result.parquet").is_file()
    with db.transaction() as session:
        assert session.scalars(select(OutputEndpoint)).all() == []
