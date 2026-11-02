# AI contribution: 50% or more AI-generated
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
"""

import logging
import threading
from dataclasses import dataclass

from fastapi import Request

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
        self._current_run = threading.Lock()
        self._current_cancellation: Cancellation | None = None
        self._thread = threading.Thread(
            target=self._loop, name=f"timer-{pipeline_id}", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self, *, join_timeout: float) -> None:
        """Signal the loop to stop and cancel a run in flight, then wait."""
        self._stop_event.set()
        with self._current_run:
            if self._current_cancellation is not None:
                self._current_cancellation.cancel()
        self._thread.join(timeout=join_timeout)

    def _loop(self) -> None:
        while not self._stop_event.wait(self.status.interval_seconds):
            if self._stop_event.is_set():
                return
            self._run_once()

    def _run_once(self) -> None:
        token = Cancellation()
        with self._current_run:
            self._current_cancellation = token
        try:
            execute_revision(
                self._db, self._executor, self.status.revision_id, cancellation=token
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
            with self._current_run:
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
            if pipeline_id in self._timers:
                raise TimerAlreadyRunning(pipeline_id)
            timer = _Timer(
                self._db, self._executor, pipeline_id, revision_id, interval_seconds
            )
            self._timers[pipeline_id] = timer
        timer.start()

    def stop(self, pipeline_id: str, *, join_timeout: float = 30.0) -> None:
        with self._lock:
            timer = self._timers.pop(pipeline_id, None)
        if timer is None:
            raise TimerNotRunning(pipeline_id)
        timer.stop(join_timeout=join_timeout)

    def status(self, pipeline_id: str) -> TimerStatus | None:
        with self._lock:
            timer = self._timers.get(pipeline_id)
        return timer.status if timer is not None else None

    def stop_all(self, *, join_timeout: float = 30.0) -> None:
        """Called at app shutdown: leaves no background thread running."""
        with self._lock:
            timers = list(self._timers.values())
            self._timers.clear()
        for timer in timers:
            timer.stop(join_timeout=join_timeout)


def scheduler(request: Request) -> TimerScheduler:
    configured: TimerScheduler | None = request.app.state.scheduler
    if configured is None:
        raise RuntimeError("Timer scheduler is unavailable")
    return configured
