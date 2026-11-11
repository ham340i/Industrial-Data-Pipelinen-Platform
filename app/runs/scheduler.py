# AI contribution: below 50% AI-generated
"""Single-process, in-memory interval timer for Timer-triggered pipelines (#29).

Deliberately minimal, per the Release 1 design notes: no cron, no durable or
distributed scheduling, no new scheduling framework. A timer exists only
while this process is running - restarting the service loses every running
timer, and callers must call ``start`` again after a restart.

No-overlap is structural, not a separate lock: one dedicated thread per timer
both waits out the interval and runs the pipeline, in that order, in a loop.
The next wait cannot begin until the current run's call into
``execute_revision`` has returned, so two runs of the same timer can never be
in flight at once.

Stopping cancels cooperatively, like the rest of the executor: ``stop()``
sets the pipeline's ``Cancellation`` token immediately, but a block already
running is not preemptible (Python cannot interrupt a thread mid-call), so
``stop()`` waits (bounded by ``join_timeout``) for that block to return before
the run is recorded as cancelled and the thread joins. A timer with only one,
long-running block therefore cannot be stopped before that block finishes; a
multi-block pipeline stops after its current block, as usual.

If the block is still running when ``join_timeout`` elapses, ``stop()`` does
not pretend the timer is gone: it raises ``TimerStopTimedOut`` and leaves the
timer registered as stopping, so a replacement ``start()`` for the same
pipeline is rejected until the old thread actually exits, and never runs
concurrently with it. ``stop_all()`` (used at application shutdown) instead
blocks for as long as it takes, since the caller is about to close the
database and must not do so while a timer thread might still touch it.

The decision to start the next tick and the decision to stop share one lock,
so a tick can never begin after ``stop()`` has already set the stop signal
under that same lock - closing the race where a timer's wait happens to time
out at the exact moment ``stop()`` is called.
"""

import logging
import threading
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy import select

from app.config import settings
from app.metadata.models import Pipeline, PipelineRevision

from app.execution import Cancellation, Executor
from app.metadata.database import Database
from app.runs.service import execute_revision

logger = logging.getLogger(__name__)


class TimerAlreadyRunning(Exception):
    def __init__(self, pipeline_id: str) -> None:
        self.pipeline_id = pipeline_id
        super().__init__(f"A timer is already running for pipeline {pipeline_id}.")


class TimerNotRunning(Exception):
    def __init__(self, pipeline_id: str) -> None:
        self.pipeline_id = pipeline_id
        super().__init__(f"No timer is running for pipeline {pipeline_id}.")


class TimerStopTimedOut(Exception):
    def __init__(self, pipeline_id: str) -> None:
        self.pipeline_id = pipeline_id
        super().__init__(
            f"Timer for pipeline {pipeline_id} is still finishing its current "
            "run; it did not stop within the timeout."
        )


@dataclass(frozen=True)
class TimerStatus:
    pipeline_id: str
    revision_id: str
    interval_seconds: int


class _Timer:
    """One background thread: wait out the interval, run, repeat."""

    def __init__(
        self,
        db: Database,
        executor: Executor,
        pipeline_id: str,
        revision_id: str,
        interval_seconds: int,
    ) -> None:
        self.status = TimerStatus(pipeline_id, revision_id, interval_seconds)
        self._db = db
        self._executor = executor
        self._stop_event = threading.Event()
        # Guards both halves of the race a timer boundary can create: a tick
        # deciding to start, and stop() deciding to cancel/signal. Both hold
        # this lock, so whichever runs first is final - a tick can never
        # begin after stop() has already set the stop signal under it.
        self._lock = threading.Lock()
        self._current_cancellation: Cancellation | None = None
        self._thread = threading.Thread(
            target=self._loop, name=f"timer-{pipeline_id}", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def stop(self, *, join_timeout: float) -> bool:
        """Signal the loop to stop and cancel a run in flight, then wait.

        Returns True once the thread has fully exited, False if it is still
        finishing an in-flight block after ``join_timeout``: cooperative
        cancellation cannot preempt a block that is already running, so the
        caller must not treat the timer as gone (and must not start a
        replacement for the same pipeline) until this returns True.
        """
        with self._lock:
            self._stop_event.set()
            if self._current_cancellation is not None:
                self._current_cancellation.cancel()
        self._thread.join(timeout=join_timeout)
        return not self._thread.is_alive()

    def wait_until_stopped(self) -> None:
        """Block with no timeout. Used only at application shutdown, where
        the caller is about to close the database and a leftover thread
        touching it is not an option."""
        self._thread.join()

    def _loop(self) -> None:
        while not self._stop_event.wait(self.status.interval_seconds):
            token = Cancellation()
            with self._lock:
                # Re-checked here, under the same lock stop() uses, even
                # though the loop condition above already tested it: wait()
                # can report "timed out" at the exact instant stop() sets
                # the signal, and only this second check - serialized
                # against stop() - can still catch that dead heat.
                if self._stop_event.is_set():
                    return
                self._current_cancellation = token
            self._run_once(token)

    def _run_once(self, token: Cancellation) -> None:
        try:
            with self._db.transaction() as session:
                project_id = session.execute(
                    select(Pipeline.project_id)
                    .join(PipelineRevision, PipelineRevision.pipeline_id == Pipeline.id)
                    .where(PipelineRevision.id == self.status.revision_id)
                ).scalar_one()
            execute_revision(
                self._db,
                self._executor,
                self.status.revision_id,
                cancellation=token,
                workspace_root=settings.workspace_root / project_id,
            )
        except Exception:
            # The run row itself already records a truthful failed/cancelled
            # state; this just keeps one bad tick from killing the timer.
            logger.exception(
                "Timer tick failed for pipeline %s revision %s",
                self.status.pipeline_id,
                self.status.revision_id,
            )
        finally:
            with self._lock:
                self._current_cancellation = None


class TimerScheduler:
    """Tracks at most one running timer per pipeline."""

    def __init__(self, db: Database, executor: Executor) -> None:
        self._db = db
        self._executor = executor
        self._lock = threading.Lock()
        self._timers: dict[str, _Timer] = {}

    def start(self, pipeline_id: str, revision_id: str, interval_seconds: int) -> None:
        with self._lock:
            existing = self._timers.get(pipeline_id)
            if existing is not None:
                if existing.is_alive():
                    raise TimerAlreadyRunning(pipeline_id)
                # A previous stop() timed out while this one's block was
                # still running; it has since exited on its own, so the slot
                # is free again rather than staying rejected forever.
                del self._timers[pipeline_id]
            timer = _Timer(
                self._db, self._executor, pipeline_id, revision_id, interval_seconds
            )
            # Publish only a started thread, while stop/start share this lock.
            timer.start()
            self._timers[pipeline_id] = timer

    def stop(self, pipeline_id: str, *, join_timeout: float = 30.0) -> None:
        with self._lock:
            timer = self._timers.get(pipeline_id)
        if timer is None:
            raise TimerNotRunning(pipeline_id)
        stopped = timer.stop(join_timeout=join_timeout)
        with self._lock:
            # Only remove the entry this call actually stopped: a concurrent
            # stop() or a replacement start() may have already changed it.
            if self._timers.get(pipeline_id) is timer and stopped:
                del self._timers[pipeline_id]
        if not stopped:
            # Still finishing its current run: keep it registered so a
            # replacement start() for this pipeline is rejected, never left
            # free to run the same pipeline concurrently with it.
            raise TimerStopTimedOut(pipeline_id)

    def status(self, pipeline_id: str) -> TimerStatus | None:
        with self._lock:
            timer = self._timers.get(pipeline_id)
        return timer.status if timer is not None else None

    def stop_all(self, *, join_timeout: float = 30.0) -> None:
        """Called at app shutdown: blocks until no timer thread remains, so
        the caller can safely close the database right after this returns.
        A thread still finishing a block is waited for, never abandoned.
        """
        with self._lock:
            timers = list(self._timers.values())
            self._timers.clear()
        for timer in timers:
            if not timer.stop(join_timeout=join_timeout):
                logger.warning(
                    "Timer for pipeline %s is still finishing its current "
                    "run after %.1fs; waiting for it to exit before "
                    "shutdown continues.",
                    timer.status.pipeline_id,
                    join_timeout,
                )
                timer.wait_until_stopped()


def scheduler(request: Request) -> TimerScheduler:
    configured: TimerScheduler | None = request.app.state.scheduler
    if configured is None:
        raise RuntimeError("Timer scheduler is unavailable")
    return configured
