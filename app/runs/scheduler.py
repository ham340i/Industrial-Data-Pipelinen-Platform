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
``stop()`` waits (bounded by ``join_timeout``) for that block to return. A
completed one-block run stays succeeded; unstarted work is skipped, and blocks
with cooperative checkpoints may observe cancellation before committing output.

If the block is still running when ``join_timeout`` elapses, ``stop()`` does
not pretend the timer is gone: it raises ``TimerStopTimedOut`` and leaves the
timer registered as stopping, so a replacement ``start()`` for the same
pipeline is rejected until the old thread actually exits, and never runs
concurrently with it. ``stop_all()`` (used at application shutdown) instead
uses one deadline for all workers and reports unfinished workers explicitly.
The caller must close the database only after a successful drain.

The decision to start the next tick and the decision to stop share one lock,
so a tick can never begin after ``stop()`` has already set the stop signal
under that same lock - closing the race where a timer's wait happens to time
out at the exact moment ``stop()`` is called.
"""

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from fastapi import Request
from sqlalchemy import select

from app.workspace import effective_workspace_root
from app.workspace_storage import pipeline_data_folder, pipeline_storage
from app.metadata.models import Pipeline, PipelineRevision, Project

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


class TimerSchedulerDraining(Exception):
    """A scheduler drain is active or still owns unfinished workers."""


class TimerShutdownTimedOut(Exception):
    def __init__(self, pipeline_ids: tuple[str, ...]) -> None:
        self.pipeline_ids = pipeline_ids
        super().__init__("Timer shutdown did not complete before its deadline.")


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
        workspace_root: Path | None = None,
    ) -> None:
        self.status = TimerStatus(pipeline_id, revision_id, interval_seconds)
        self._db = db
        self._executor = executor
        self._workspace_root = workspace_root
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
        self.request_stop()
        return self.wait_until_stopped(join_timeout=join_timeout)

    def request_stop(self) -> None:
        """Signal cancellation without waiting, so all workers stop promptly."""
        with self._lock:
            self._stop_event.set()
            if self._current_cancellation is not None:
                self._current_cancellation.cancel()

    def wait_until_stopped(self, *, join_timeout: float) -> bool:
        """Wait within the remaining budget; false never means cleaned up."""
        self._thread.join(timeout=max(0.0, join_timeout))
        return not self._thread.is_alive()

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
            with pipeline_storage(self.status.pipeline_id, wait=True):
                with self._db.transaction() as session:
                    project_root = session.execute(
                        select(Project.workspace_root)
                        .join(Pipeline, Project.id == Pipeline.project_id)
                        .join(
                            PipelineRevision,
                            PipelineRevision.pipeline_id == Pipeline.id,
                        )
                        .where(PipelineRevision.id == self.status.revision_id)
                    ).scalar_one()
                root = self._workspace_root or (
                    Path(project_root)
                    if project_root
                    else effective_workspace_root(self._db)
                )
                folder: Path | None = None
                if root is not None:
                    try:
                        folder = pipeline_data_folder(
                            self._db, self.status.pipeline_id, root=root
                        )
                    except ValueError:
                        # Run without a workspace so the tick is still recorded as
                        # a failed run (workspace_required) rather than writing
                        # through an aliased folder (#37 review).
                        logger.warning(
                            "Timer for pipeline %s: project data folder is missing "
                            "or aliased; running without a workspace",
                            self.status.pipeline_id,
                        )
                execute_revision(
                    self._db,
                    self._executor,
                    self.status.revision_id,
                    cancellation=token,
                    workspace_root=folder,
                )
        except Exception as exc:
            # The run service attempts failed-run reconciliation; unavailable
            # storage can defer it until startup recovery. Keep the next tick
            # alive without logging private exception text or traceback values.
            logger.error(
                "Timer tick failed for pipeline %s revision %s (%s)",
                self.status.pipeline_id,
                self.status.revision_id,
                type(exc).__name__,
            )
        finally:
            with self._lock:
                self._current_cancellation = None


class TimerScheduler:
    """Tracks at most one running timer per pipeline."""

    def __init__(
        self, db: Database, executor: Executor, workspace_root: Path | None = None
    ) -> None:
        self._db = db
        self._executor = executor
        self._workspace_root = workspace_root
        self._lock = threading.Lock()
        self._timers: dict[str, _Timer] = {}
        self._draining = False
        self._drain_active = False

    def start(self, pipeline_id: str, revision_id: str, interval_seconds: int) -> None:
        with self._lock:
            if self._draining:
                if self._drain_active or any(
                    t.is_alive() for t in self._timers.values()
                ):
                    raise TimerSchedulerDraining()
                # A timed-out drain has since finished. No live worker can
                # lose its slot, and ordinary reuse is safe again.
                self._timers.clear()
                self._draining = False
            existing = self._timers.get(pipeline_id)
            if existing is not None:
                if existing.is_alive():
                    raise TimerAlreadyRunning(pipeline_id)
                # A previous stop() timed out while this one's block was
                # still running; it has since exited on its own, so the slot
                # is free again rather than staying rejected forever.
                del self._timers[pipeline_id]
            timer = _Timer(
                self._db,
                self._executor,
                pipeline_id,
                revision_id,
                interval_seconds,
                self._workspace_root,
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
        """Signal all timers, then drain within one shared monotonic deadline.

        On timeout, keep live workers registered and reject starts until they
        exit. Only a successful return permits database disposal. Python
        threads cannot forcibly interrupt a block stuck in native I/O.
        """
        with self._lock:
            if self._drain_active:
                raise TimerSchedulerDraining()
            self._draining = self._drain_active = True
            timers = list(self._timers.values())
        try:
            deadline = time.monotonic() + max(0.0, join_timeout)
            for timer in timers:
                timer.request_stop()
            for timer in timers:
                timer.wait_until_stopped(
                    join_timeout=max(0.0, deadline - time.monotonic())
                )
            with self._lock:
                unfinished = tuple(
                    timer.status.pipeline_id for timer in timers if timer.is_alive()
                )
            if unfinished:
                raise TimerShutdownTimedOut(unfinished)
        finally:
            with self._lock:
                self._timers = {
                    identity: timer
                    for identity, timer in self._timers.items()
                    if timer.is_alive()
                }
                self._drain_active = False
                self._draining = bool(self._timers)


def scheduler(request: Request) -> TimerScheduler:
    configured: TimerScheduler | None = request.app.state.scheduler
    if configured is None:
        raise RuntimeError("Timer scheduler is unavailable")
    return configured
