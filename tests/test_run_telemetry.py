# AI contribution: 50% or more AI-generated
"""Durable run evidence on real file-backed SQLite (#27)."""

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.execution import Cancellation, ExecutionContext, Executor, InvalidPipeline
from app.execution.runtime import State, StateEvent
from app.metadata.database import Database
from app.metadata.migrate import upgrade
from app.metadata.models import Run, RunBlock, RunEvent
from app.pipelines.models import PipelineDefinition
from app.runs import RevisionNotFound, RunRecorder, execute_revision
from app.runs.recorder import recover_interrupted
from tests.run_support import Cancel, chain, executor, seed_revision


# Progress a run reports before its process stops without finishing.
STARTED: list[tuple[str | None, State]] = [
    (None, "queued"),
    (None, "running"),
    ("n0", "running"),
]


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "runs.sqlite3")
    upgrade(database)
    yield database
    database.close()


def stored(db: Database, run_id: str) -> tuple[Run, list[RunBlock], list[RunEvent]]:
    with db.transaction() as session:
        run = session.get(Run, run_id)
        assert run is not None
        return run, list(run.blocks), list(run.events)


def test_success_persists_run_block_timings_and_counts(db: Database):
    revision_id = seed_revision(db, chain("test.source", "test.double", "test.sink"))
    outcome = execute_revision(db, executor(), revision_id)
    run, blocks, events = stored(db, outcome.run_id)

    assert (run.state, run.pipeline_revision_id) == ("succeeded", revision_id)
    assert run.started_at is not None and run.ended_at is not None
    assert run.started_at <= run.ended_at
    assert run.duration_ms is not None and run.duration_ms >= 0
    assert run.row_count == 2  # rows the leaf sink received
    assert run.error_code is None
    assert [(b.position, b.node_id, b.block_id) for b in blocks] == [
        (0, "n0", "test.source"),
        (1, "n1", "test.double"),
        (2, "n2", "test.sink"),
    ]
    assert {b.state for b in blocks} == {"completed"}
    assert [(b.rows_in, b.rows_out) for b in blocks] == [(0, 2), (2, 2), (2, None)]
    assert all(b.duration_ms is not None and b.duration_ms >= 0 for b in blocks)
    assert [e.sequence for e in events] == list(range(len(events)))
    assert events[-1].message == "Run succeeded"
    assert {e.message for e in events if e.kind == "block"} >= {
        "Block test.double@1 started",
        "Block test.double@1 succeeded",
    }


def test_measured_zero_rows_differ_from_unknown_counts(db: Database):
    empty = execute_revision(
        db, executor(), seed_revision(db, chain("test.empty", "test.sink"))
    )
    failed = execute_revision(
        db, executor(), seed_revision(db, chain("test.source", "test.fail"))
    )
    empty_run, empty_blocks, _ = stored(db, empty.run_id)
    failed_run, failed_blocks, _ = stored(db, failed.run_id)

    assert empty_run.row_count == 0
    assert empty_blocks[0].rows_out == 0
    assert failed_run.row_count is None
    assert (failed_blocks[1].rows_in, failed_blocks[1].rows_out) == (None, None)


def test_block_failure_is_structured_redacted_and_root_caused(db: Database):
    revision_id = seed_revision(db, chain("test.source", "test.fail", "test.sink"))
    outcome = execute_revision(db, executor(), revision_id)
    run, blocks, events = stored(db, outcome.run_id)

    assert outcome.state == run.state == "failed"
    assert run.error_code == "source_unreadable"  # not the downstream symptom
    assert [b.state for b in blocks] == ["completed", "failed", "skipped"]
    assert (blocks[1].error_code, blocks[2].error_code) == (
        "source_unreadable",
        "dependency_failed",
    )
    persisted = [run.error_reason, blocks[1].error_reason] + [e.message for e in events]
    for text in persisted:
        assert text is not None
        assert "hunter2" not in text and "/home/alice" not in text
    assert "password=[REDACTED]" in (blocks[1].error_reason or "")
    assert any(e.level == "warning" and e.node_id == "n1" for e in events)


def test_invalid_pipeline_is_refused_without_a_run_row(db: Database):
    revision_id = seed_revision(db, chain("test.source", "test.missing"))
    with pytest.raises(InvalidPipeline):
        execute_revision(db, executor(), revision_id)
    with db.transaction() as session:
        assert session.scalar(select(func.count(Run.id))) == 0


def test_unknown_revision_is_reported(db: Database):
    with pytest.raises(RevisionNotFound):
        execute_revision(db, executor(), "no-such-revision")


def test_cancellation_is_recorded_as_cancelled(db: Database):
    token, block = Cancellation(), Cancel()
    block.token = token
    revision_id = seed_revision(db, chain("test.source", "test.cancel", "test.sink"))
    outcome = execute_revision(db, executor(block), revision_id, cancellation=token)
    run, blocks, _ = stored(db, outcome.run_id)

    assert run.state == "cancelled"
    assert [b.state for b in blocks] == ["completed", "completed", "skipped"]
    assert blocks[2].error_code == "cancelled"


class CrashingExecutor(Executor):
    """Reports progress, then dies the way an unexpected engine bug would."""

    def execute(
        self, definition: PipelineDefinition, **options: Any
    ) -> ExecutionContext:
        notify = options["on_state"]
        run_id = options["run_id"]
        for node_id, state in STARTED:
            notify(StateEvent(run_id=run_id, node_id=node_id, state=state))
        raise RuntimeError("engine bug")


def test_unexpected_crash_leaves_a_truthful_terminal_state(db: Database):
    revision_id = seed_revision(db, chain("test.source", "test.sink"))
    crashing = CrashingExecutor(executor().registry)
    with pytest.raises(RuntimeError, match="engine bug"):
        execute_revision(db, crashing, revision_id)
    with db.transaction() as session:
        run = session.scalars(select(Run)).one()
        blocks, events = list(run.blocks), list(run.events)
        assert (run.state, run.error_code) == ("failed", "execution_failed")
    assert [b.state for b in blocks] == ["failed", "skipped"]
    assert events[-1].level == "error"
    assert "engine bug" not in events[-1].message


def test_restart_closes_interrupted_runs_once_and_keeps_finished_ones(tmp_path: Path):
    path = tmp_path / "restart.sqlite3"
    first = Database(path)
    upgrade(first)
    revision_id = seed_revision(first, chain("test.source", "test.sink"))
    finished = execute_revision(first, executor(), revision_id).run_id
    definition = PipelineDefinition.from_json(
        json.dumps(chain("test.source", "test.sink"))
    )
    recorder = RunRecorder(first, "abandoned", revision_id, definition)
    for node_id, state in STARTED:
        recorder.on_state(StateEvent(run_id="abandoned", node_id=node_id, state=state))
    first.close()  # the process "dies" here

    second = Database(path)
    try:
        assert recover_interrupted(second) == ["abandoned"]
        assert recover_interrupted(second) == []
        run, blocks, events = stored(second, "abandoned")
        assert (run.state, run.error_code) == ("failed", "interrupted")
        assert run.ended_at is not None and run.started_at is not None
        assert run.ended_at >= run.started_at
        assert [b.state for b in blocks] == ["failed", "skipped"]
        assert [e.sequence for e in events] == list(range(len(events)))
        assert stored(second, finished)[0].state == "succeeded"
    finally:
        second.close()


def test_runs_of_one_revision_are_isolated(db: Database):
    revision_id = seed_revision(db, chain("test.source", "test.sink"))
    first = execute_revision(db, executor(), revision_id)
    second = execute_revision(db, executor(), revision_id)
    assert first.run_id != second.run_id
    for outcome in (first, second):
        run, blocks, events = stored(db, outcome.run_id)
        assert run.row_count == 2
        assert {b.run_id for b in blocks} == {e.run_id for e in events} == {run.id}
        assert len(blocks) == 2


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_durations_use_the_injected_monotonic_clock(db: Database):
    revision_id = seed_revision(db, chain("test.source"))
    definition = PipelineDefinition.from_json(json.dumps(chain("test.source")))
    clock = Clock()
    recorder = RunRecorder(db, "timed", revision_id, definition, clock=clock)
    context = ExecutionContext(
        "timed", state="completed", node_states={"n0": "completed"}
    )
    recorder.on_state(StateEvent(run_id="timed", state="queued"))
    recorder.on_state(StateEvent(run_id="timed", state="running"))
    recorder.on_state(StateEvent(run_id="timed", node_id="n0", state="running"))
    clock.now += 1.25
    recorder.on_state(StateEvent(run_id="timed", node_id="n0", state="completed"))
    clock.now += 0.5
    assert recorder.finish(context, cancelled=False) == "succeeded"
    run, blocks, _ = stored(db, "timed")
    assert (blocks[0].duration_ms, run.duration_ms) == (1250, 1750)


def test_persistence_failures_are_logged_not_silently_dropped(
    db: Database, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    definition = PipelineDefinition.from_json(
        '{"schema_version":1,"nodes":[],"edges":[]}'
    )
    recorder = RunRecorder(db, "lost", "missing-revision", definition)

    def unavailable(**_: Any) -> Any:
        raise OperationalError("BEGIN", {}, Exception("database is locked"))

    monkeypatch.setattr(db, "transaction", unavailable)
    with caplog.at_level(logging.WARNING, logger="app.runs.recorder"):
        recorder.on_state(StateEvent(run_id="lost", state="queued"))
    assert recorder.created is False
    assert "could not persist queued state" in caplog.text
