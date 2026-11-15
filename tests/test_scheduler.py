# AI contribution: below 50% AI-generated
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
from app.execution import Cancellation, Executor
from app.metadata.database import Database
from app.metadata.migrate import upgrade
from app.metadata.models import Run
from app.runs.scheduler import (
    TimerAlreadyRunning,
    TimerNotRunning,
    TimerScheduler,
    TimerStopTimedOut,
    _Timer,
)
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
        self.started = threading.Event()
        self._lock = threading.Lock()

    def _execute(
        self, config: BlockConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        start = time.monotonic()
        self.started.set()
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
    # Poll for two completed ticks instead of a fixed sleep: a slow or
    # loaded CI runner can delay thread scheduling well past the ~2.6s a
    # fast machine needs for two 1s-interval, 0.6s-delay ticks.
    deadline = time.monotonic() + 10.0
    while len(trigger.calls) < 2 and time.monotonic() < deadline:
        time.sleep(0.1)
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

    # Wait for the block to actually start, rather than guessing a sleep
    # duration: a loaded CI runner can delay thread scheduling enough that a
    # fixed sleep sometimes lands before the tick starts, which would cancel
    # it before it ever ran instead of mid-run.
    assert trigger.started.wait(timeout=5)
    started = time.monotonic()
    scheduler.stop("pipeline", join_timeout=5)
    elapsed = time.monotonic() - started
    assert elapsed < 4.0  # waited for the block, not a second full interval

    with db.transaction() as session:
        runs = list(session.scalars(select(Run)))
        assert len(runs) == 1
        assert runs[0].state == "succeeded"


def test_stop_rejects_a_replacement_while_the_old_run_is_still_finishing(
    db: Database,
):
    """Review finding (#29): a stop() that times out on an in-flight block
    must not free the pipeline id for a replacement start() - that would let
    two timers of the same pipeline run concurrently, which the single-
    thread-per-timer design is meant to rule out entirely.
    """
    trigger = RecordingTrigger(delay=1.0)
    revision_id = seed_revision(db, chain("test.trigger"))
    scheduler = TimerScheduler(db, executor_for(trigger))
    scheduler.start("pipeline", revision_id, interval_seconds=1)

    assert trigger.started.wait(timeout=5)  # now mid-run
    with pytest.raises(TimerStopTimedOut):
        scheduler.stop("pipeline", join_timeout=0.05)  # far too short to finish

    # The old thread is still running that block: a replacement must be
    # rejected, not allowed to execute the same pipeline alongside it.
    with pytest.raises(TimerAlreadyRunning):
        scheduler.start("pipeline", revision_id, interval_seconds=1)

    # Once the in-flight run genuinely finishes, the slot frees up again.
    deadline = time.monotonic() + 5.0
    while len(trigger.calls) < 1 and time.monotonic() < deadline:
        time.sleep(0.05)
    scheduler.stop("pipeline")
    scheduler.start("pipeline", revision_id, interval_seconds=30)
    scheduler.stop("pipeline")


def test_stop_at_the_interval_boundary_never_lets_a_new_run_start(db: Database):
    """Deterministic regression for the exact race flagged in review (#29):
    a tick's wait() reporting "timed out" at the very instant stop() sets
    the stop signal must still not let that tick start. The loop's own
    lock-guarded re-check - serialized against stop() - is what has to catch
    it, not the timing of wait()'s return.
    """
    trigger = RecordingTrigger()
    revision_id = seed_revision(db, chain("test.trigger"))
    scheduler = TimerScheduler(db, executor_for(trigger))

    # Built directly, not via scheduler.start(): the patches below must be in
    # place *before* the background thread makes its first wait() call, or
    # that call resolves the original method and the race is never exercised.
    timer = _Timer(  # noqa: SLF001 - white-box race test
        db, executor_for(trigger), "pipeline", revision_id, interval_seconds=3600
    )

    woke = threading.Event()
    release = threading.Event()
    stop_called = threading.Event()
    real_set = timer._stop_event.set  # noqa: SLF001

    def patched_wait(timeout: float | None = None) -> bool:
        woke.set()
        assert release.wait(timeout=5)
        return False  # pretend the interval elapsed, exactly as stop() races in

    def patched_set() -> None:
        stop_called.set()
        real_set()

    timer._stop_event.wait = patched_wait  # type: ignore[method-assign] # noqa: SLF001
    timer._stop_event.set = patched_set  # type: ignore[method-assign] # noqa: SLF001

    scheduler._timers["pipeline"] = timer  # noqa: SLF001 - white-box registration
    timer.start()

    assert woke.wait(timeout=5)  # the loop is now paused right where it matters

    stop_thread = threading.Thread(target=scheduler.stop, args=("pipeline",))
    stop_thread.start()
    assert stop_called.wait(timeout=5)  # stop() has set the signal
    release.set()  # only now let the tick's wait() report "timed out"
    stop_thread.join(timeout=5)

    assert trigger.calls == []  # no run ever started after stop() began


def test_stop_after_tick_is_accepted_cancels_before_block_execution(
    db: Database, monkeypatch: pytest.MonkeyPatch
):
    """An accepted tick need not succeed when Stop arrives before its block."""
    trigger = RecordingTrigger()
    revision_id = seed_revision(db, chain("test.trigger"))
    timer = _Timer(db, executor_for(trigger), "pipeline", revision_id, 1)
    accepted = threading.Event()
    release = threading.Event()
    tokens: list[Cancellation] = []
    original_run_once = timer._run_once

    def paused_run_once(token: Cancellation) -> None:
        tokens.append(token)
        accepted.set()
        if release.wait(timeout=5):
            original_run_once(token)

    monkeypatch.setattr(timer, "_run_once", paused_run_once)
    timer.start()
    try:
        assert accepted.wait(timeout=5)
        # This sets cancellation synchronously while the accepted tick is held.
        assert timer.stop(join_timeout=0) is False
        assert tokens[0].is_cancelled()
        release.set()
        timer._thread.join(timeout=5)
        assert not timer.is_alive()
        assert len(tokens) == 1  # no subsequent tick after stopping
        assert trigger.calls == []
        with db.transaction() as session:
            runs = list(session.scalars(select(Run)))
            assert len(runs) == 1
            assert runs[0].state == "cancelled"
            assert runs[0].error_code == "cancelled"
            assert runs[0].ended_at is not None
    finally:
        release.set()
        assert timer.stop(join_timeout=5)


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


def test_stop_all_waits_for_an_active_run_before_the_caller_closes_the_database(
    db: Database,
):
    """Mirrors ``app.main``'s shutdown sequence exactly (#29 review): it calls
    ``stop_all()`` and only then closes the database. This asserts that
    ordering is actually safe - ``stop_all()`` must not return, and the run's
    own thread must not still exist, while a block is still mid-execution,
    or the in-flight run's write-back would race a database the caller is
    about to close right after.
    """
    trigger = RecordingTrigger(delay=1.0)
    revision_id = seed_revision(db, chain("test.trigger"))
    scheduler = TimerScheduler(db, executor_for(trigger))
    scheduler.start("pipeline", revision_id, interval_seconds=1)

    assert trigger.started.wait(timeout=5)  # now mid-run, as at a real shutdown
    scheduler.stop_all(join_timeout=0.05)  # too short to finish on its own

    # No thread survives stop_all() returning, no matter how short
    # join_timeout was - exactly what makes closing the database next safe.
    assert not any(t.name == "timer-pipeline" for t in threading.enumerate())

    db.close()  # the same step app.main takes right after stop_all()

    with db.transaction() as session:
        runs = list(session.scalars(select(Run)))
    assert len(runs) == 1
    assert runs[0].state == "succeeded"


def test_start_publishes_only_started_timer(
    db: Database, monkeypatch: pytest.MonkeyPatch
):
    scheduler = TimerScheduler(db, executor_for(RecordingTrigger()))
    original_start = _Timer.start
    observed = []

    def checked_start(timer: _Timer) -> None:
        observed.append(timer.status.pipeline_id in scheduler._timers)
        assert scheduler._lock.locked()
        original_start(timer)

    monkeypatch.setattr(_Timer, "start", checked_start)
    scheduler.start("pipeline", "revision", 30)
    try:
        assert observed == [False]
    finally:
        scheduler.stop("pipeline")


def test_failed_start_does_not_leave_registered_timer(
    db: Database, monkeypatch: pytest.MonkeyPatch
):
    scheduler = TimerScheduler(db, executor_for(RecordingTrigger()))

    def fail_start(timer: _Timer) -> None:
        raise RuntimeError("cannot start thread")

    monkeypatch.setattr(_Timer, "start", fail_start)
    with pytest.raises(RuntimeError, match="cannot start"):
        scheduler.start("pipeline", "revision", 30)
    assert scheduler.status("pipeline") is None
