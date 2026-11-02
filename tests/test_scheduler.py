# AI contribution: 50% or more AI-generated
"""Timer scheduler: start/stop, no-overlap and shutdown cleanup (#29)."""

import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.blocks.base import Block
from app.blocks.context import BlockContext
from app.blocks.contracts import (
    BlockConfig,
    BlockDescriptor,
    ControlSignal,
    Port,
    PortValues,
)
from app.blocks.registry import BlockRegistry
from app.execution import Executor
from app.metadata.database import Database
from app.metadata.migrate import upgrade
from app.metadata.models import Run
from app.runs.scheduler import TimerAlreadyRunning, TimerNotRunning, TimerScheduler
from sqlalchemy import select
from tests.run_support import chain, seed_revision

SIGNAL = (Port(name="signal", kind="control"),)


class RecordingTrigger(Block[BlockConfig]):
    """A trigger that sleeps ``delay`` seconds and records each call's span."""

    config_model = BlockConfig
    descriptor = BlockDescriptor(
        block_id="test.trigger",
        version="1",
        block_type="trigger",
        name="Recording Trigger",
        category="test",
        outputs=SIGNAL,
    )

    def __init__(self, delay: float = 0.0) -> None:
        self.delay = delay
        self.calls: list[tuple[float, float]] = []
        self._lock = threading.Lock()

    def _execute(
        self, config: BlockConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        start = time.monotonic()
        time.sleep(self.delay)
        end = time.monotonic()
        with self._lock:
            self.calls.append((start, end))
        return {"signal": (ControlSignal(),)}


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "scheduler.sqlite3")
    upgrade(database)
    yield database
    database.close()


def executor_for(trigger: RecordingTrigger) -> Executor:
    registry = BlockRegistry()
    registry.register(trigger)
    return Executor(registry)


def non_overlapping(calls: list[tuple[float, float]]) -> bool:
    ordered = sorted(calls)
    # Deliberately offset by one: ordered[1:] is always one element shorter.
    pairs = zip(ordered, ordered[1:], strict=False)
    return all(a_end <= b_start for (_, a_end), (b_start, _) in pairs)


def test_start_stop_round_trip_tracks_status(db: Database):
    trigger = RecordingTrigger()
    revision_id = seed_revision(db, chain("test.trigger"))
    scheduler = TimerScheduler(db, executor_for(trigger))

    assert scheduler.status("pipeline") is None
    scheduler.start("pipeline", revision_id, 1)
    status = scheduler.status("pipeline")
    assert status is not None
    assert (status.pipeline_id, status.revision_id, status.interval_seconds) == (
        "pipeline",
        revision_id,
        1,
    )
    scheduler.stop("pipeline")
    assert scheduler.status("pipeline") is None


def test_start_twice_raises_already_running(db: Database):
    trigger = RecordingTrigger()
    revision_id = seed_revision(db, chain("test.trigger"))
    scheduler = TimerScheduler(db, executor_for(trigger))
    scheduler.start("pipeline", revision_id, 5)
    try:
        with pytest.raises(TimerAlreadyRunning):
            scheduler.start("pipeline", revision_id, 5)
    finally:
        scheduler.stop("pipeline")


def test_stop_when_not_running_raises_not_running(db: Database):
    scheduler = TimerScheduler(db, executor_for(RecordingTrigger()))
    with pytest.raises(TimerNotRunning):
        scheduler.stop("pipeline")


def test_stop_between_ticks_returns_promptly(db: Database):
    """Stopping during the wait phase must not block for the full interval."""
    trigger = RecordingTrigger()
    revision_id = seed_revision(db, chain("test.trigger"))
    scheduler = TimerScheduler(db, executor_for(trigger))
    scheduler.start("pipeline", revision_id, interval_seconds=30)

    started = time.monotonic()
    scheduler.stop("pipeline")
    assert time.monotonic() - started < 2.0
    assert trigger.calls == []  # the 30s wait never elapsed


def test_runs_from_a_slow_timer_never_overlap(db: Database):
    """The core #29 requirement: no two ticks of the same timer run at once."""
    trigger = RecordingTrigger(delay=0.6)
    revision_id = seed_revision(db, chain("test.trigger"))
    scheduler = TimerScheduler(db, executor_for(trigger))

    scheduler.start("pipeline", revision_id, interval_seconds=1)
    time.sleep(3.2)
    scheduler.stop("pipeline")

    assert len(trigger.calls) >= 2
    assert non_overlapping(trigger.calls)


def test_stop_waits_for_an_in_flight_block_to_finish_rather_than_killing_it(
    db: Database,
):
    """Cancellation is cooperative (#29): a block already running cannot be
    preempted, so a one-node timer's in-flight run still completes and is
    recorded truthfully as succeeded, not cancelled. ``stop()`` waits for it
    (bounded by ``join_timeout``) instead of abandoning the thread.
    """
    trigger = RecordingTrigger(delay=1.5)
    revision_id = seed_revision(db, chain("test.trigger"))
    scheduler = TimerScheduler(db, executor_for(trigger))
    scheduler.start("pipeline", revision_id, interval_seconds=1)

    time.sleep(1.2)  # the first tick is now running
    started = time.monotonic()
    scheduler.stop("pipeline", join_timeout=5)
    elapsed = time.monotonic() - started
    assert elapsed < 4.0  # waited for the block, not a second full interval

    with db.transaction() as session:
        runs = list(session.scalars(select(Run)))
        assert len(runs) == 1
        assert runs[0].state == "succeeded"


def test_stop_all_cleans_up_every_running_timer(db: Database):
    trigger_a, trigger_b = RecordingTrigger(), RecordingTrigger()
    revision_a = seed_revision(db, chain("test.trigger"))
    revision_b = seed_revision(db, chain("test.trigger"))
    scheduler = TimerScheduler(db, executor_for(trigger_a))
    scheduler_b_executor = executor_for(trigger_b)
    # Reuse one scheduler for both: it only needs one executor per pipeline's
    # own block registry here, so give the second pipeline its own instance.
    scheduler2 = TimerScheduler(db, scheduler_b_executor)

    scheduler.start("pipeline-a", revision_a, 30)
    scheduler2.start("pipeline-b", revision_b, 30)
    assert scheduler.status("pipeline-a") is not None
    assert scheduler2.status("pipeline-b") is not None

    started = time.monotonic()
    scheduler.stop_all()
    scheduler2.stop_all()
    assert time.monotonic() - started < 2.0

    assert scheduler.status("pipeline-a") is None
    assert scheduler2.status("pipeline-b") is None
    # A fresh start for the same pipeline id must succeed: nothing leaked.
    scheduler.start("pipeline-a", revision_a, 30)
    scheduler.stop("pipeline-a")
