# AI contribution: 50% or more AI-generated
"""Persist executor callbacks as durable run evidence in short transactions (#27).

State transitions are written as they happen, so a process that dies mid-run
leaves a ``running`` row that ``recover_interrupted`` closes on next startup.
``finish`` then reconciles every block with the executor's authoritative result.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.execution import ExecutionContext, Frame, StateEvent
from app.execution.frames import FrameValues
from app.metadata.database import Database
from app.metadata.models import Run, RunBlock, RunEvent, utc_now
from app.pipelines.models import PipelineDefinition
from app.runs.redaction import redact

logger = logging.getLogger(__name__)

TERMINAL_BLOCK_STATES = frozenset({"completed", "failed", "skipped"})
UNFINISHED_RUN_STATES = ("queued", "running")
INTERRUPTED = "interrupted"
INTERRUPTED_REASON = "The local service stopped before this run finished."


@dataclass(frozen=True)
class PlannedNode:
    node_id: str
    block_id: str
    block_version: str


def plan(definition: PipelineDefinition) -> tuple[PlannedNode, ...]:
    nodes = {node.id: node for node in definition.nodes}
    return tuple(
        PlannedNode(node_id, nodes[node_id].block_id, nodes[node_id].block_version)
        for node_id in definition.topological_order()
    )


def count_rows(values: FrameValues | None) -> int | None:
    """Rows carried by frames; None when the port values hold no frame at all."""
    frames = [v for vs in (values or {}).values() for v in vs if isinstance(v, Frame)]
    return sum(frame.data.height for frame in frames) if frames else None


def next_sequence(session: Session, run_id: str) -> int:
    latest = session.scalar(
        select(func.coalesce(func.max(RunEvent.sequence), -1)).where(
            RunEvent.run_id == run_id
        )
    )
    return int(latest if latest is not None else -1) + 1


def close_unfinished(session: Session, run: Run, code: str, reason: str) -> None:
    """Give an abandoned run a truthful terminal state without inventing success."""
    now = utc_now()
    for block in run.blocks:
        if block.state == "running":
            block.state, block.ended_at = "failed", now
            block.error_code, block.error_reason = code, reason
        elif block.state == "queued":
            block.state = "skipped"
    run.state, run.ended_at = "failed", now
    run.started_at = run.started_at or run.created_at
    run.error_code, run.error_reason = code, reason
    session.add(
        RunEvent(
            run_id=run.id,
            sequence=next_sequence(session, run.id),
            level="error",
            kind="state",
            code=code,
            message=redact(f"Run failed: {reason}"),
        )
    )


def recover_interrupted(db: Database) -> list[str]:
    """Close runs left queued/running by a previous process; returns their IDs."""
    with db.transaction(write=True) as session:
        runs = session.scalars(
            select(Run).where(Run.state.in_(UNFINISHED_RUN_STATES))
        ).all()
        for run in runs:
            close_unfinished(session, run, INTERRUPTED, INTERRUPTED_REASON)
        recovered = [run.id for run in runs]
    if recovered:
        logger.warning("Marked %d interrupted run(s) as failed", len(recovered))
    return recovered


class RunRecorder:
    """Durable sink for one run. Create one recorder per execution."""

    def __init__(
        self,
        db: Database,
        run_id: str,
        revision_id: str,
        definition: PipelineDefinition,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.db, self.run_id, self.revision_id = db, run_id, revision_id
        self.created = False
        self._nodes = plan(definition)
        sources = {edge.source.node_id for edge in definition.edges}
        self._leaves = tuple(n.node_id for n in self._nodes if n.node_id not in sources)
        self._clock = clock
        self._marks: dict[str | None, float] = {}
        self._sequence = 0

    def on_state(self, event: StateEvent) -> None:
        """Executor callback. The executor ignores callback errors, so log them."""
        try:
            with self.db.transaction(write=True) as session:
                if not self.created:
                    self._create(session)
                self._apply(session, event)
            self.created = True
        except Exception as exc:
            # No exc_info: SQL errors echo bound values into the message.
            logger.warning(
                "Run %s: could not persist %s state for node %s (%s)",
                self.run_id,
                event.state,
                event.node_id or "<run>",
                type(exc).__name__,
            )

    def finish(self, context: ExecutionContext, *, cancelled: bool) -> str:
        """Write final block evidence and the run's terminal state; returns it."""
        with self.db.transaction(write=True) as session:
            if not self.created:
                self._create(session)
                self.created = True
            run = self._run(session)
            for block in run.blocks:
                self._finish_block(block, context)
            for item in context.block_events:
                self._append(
                    session,
                    level="warning" if item.event == "failed" else "info",
                    kind="block",
                    node_id=item.node_id,
                    code=item.error_code,
                    message=f"Block {item.block_id}@{item.version} {item.event}",
                )
            self._finish_run(session, run, context, cancelled)
            return run.state

    def abort(self, code: str, reason: str) -> None:
        """Close the run after an unexpected executor failure."""
        if not self.created:
            return
        with self.db.transaction(write=True) as session:
            close_unfinished(session, self._run(session), code, reason)

    def _create(self, session: Session) -> None:
        session.add(Run(id=self.run_id, pipeline_revision_id=self.revision_id))
        session.flush()
        for position, node in enumerate(self._nodes):
            session.add(
                RunBlock(
                    run_id=self.run_id,
                    position=position,
                    node_id=node.node_id,
                    block_id=node.block_id,
                    block_version=node.block_version,
                )
            )

    def _run(self, session: Session) -> Run:
        run = session.get(Run, self.run_id)
        if run is None:
            raise LookupError(f"Run {self.run_id} was not persisted")
        return run

    def _apply(self, session: Session, event: StateEvent) -> None:
        now, mark = utc_now(), self._clock()
        if event.state == "running":
            self._marks[event.node_id] = mark
        if event.node_id is None:
            if event.state == "running":
                run = self._run(session)
                run.state, run.started_at = "running", now
            subject = "Run"
        else:
            self._apply_block(session, event, now, mark)
            subject = f"Node {event.node_id}"
        self._append(
            session,
            level="warning" if event.state == "failed" else "info",
            kind="state",
            node_id=event.node_id,
            message=f"{subject} {event.state}",
        )

    def _apply_block(
        self, session: Session, event: StateEvent, now: datetime, mark: float
    ) -> None:
        block = session.scalars(
            select(RunBlock).where(
                RunBlock.run_id == self.run_id, RunBlock.node_id == event.node_id
            )
        ).one()
        block.state = event.state
        if event.state == "running":
            block.started_at = now
        elif event.state in TERMINAL_BLOCK_STATES and block.started_at is not None:
            block.ended_at = now
            block.duration_ms = self._elapsed_ms(event.node_id, mark)

    def _finish_block(self, block: RunBlock, context: ExecutionContext) -> None:
        block.state = context.node_states.get(block.node_id, block.state)
        if block.state == "completed":
            block.rows_in = count_rows(context.inputs.get(block.node_id)) or 0
            block.rows_out = count_rows(context.outputs.get(block.node_id))
        failure = context.failures.get(block.node_id)
        if failure is not None:
            block.error_code, block.error_reason = failure.code, redact(failure.reason)
        if block.started_at is not None and block.ended_at is None:
            block.ended_at = utc_now()

    def _finish_run(
        self, session: Session, run: Run, context: ExecutionContext, cancelled: bool
    ) -> None:
        if context.state == "completed":
            run.state = "succeeded"
        else:
            run.state = "cancelled" if cancelled else "failed"
        run.started_at = run.started_at or run.created_at
        run.ended_at = utc_now()
        run.duration_ms = self._elapsed_ms(None, self._clock())
        run.row_count = self._row_count(context)
        root = self._root_failure(context)
        if root is not None:
            run.error_code, run.error_reason = root
        self._append(
            session,
            level="info" if run.state == "succeeded" else "warning",
            kind="state",
            code=run.error_code,
            message=f"Run {run.state}",
        )

    def _row_count(self, context: ExecutionContext) -> int | None:
        """Rows written by leaf nodes: sinks count inputs, other leaves outputs."""
        total = 0
        for node_id in self._leaves:
            if context.node_states.get(node_id) != "completed":
                return None
            rows = count_rows(context.outputs.get(node_id))
            if rows is None:
                rows = count_rows(context.inputs.get(node_id)) or 0
            total += rows
        return total

    def _root_failure(self, context: ExecutionContext) -> tuple[str, str] | None:
        """First direct failure in run order; skipped dependents are symptoms."""
        failures = [
            context.failures[n.node_id]
            for n in self._nodes
            if n.node_id in context.failures
        ]
        direct = [f for f in failures if f.code != "dependency_failed"] or failures
        if not direct:
            return None
        return direct[0].code, redact(f"Node {direct[0].node_id}: {direct[0].reason}")

    def _elapsed_ms(self, key: str | None, mark: float) -> int | None:
        start = self._marks.get(key)
        return None if start is None else max(0, round((mark - start) * 1000))

    def _append(
        self,
        session: Session,
        *,
        level: str,
        kind: str,
        message: str,
        node_id: str | None = None,
        code: str | None = None,
    ) -> None:
        session.add(
            RunEvent(
                run_id=self.run_id,
                sequence=self._sequence,
                level=level,
                kind=kind,
                node_id=node_id,
                code=code,
                message=redact(message),
            )
        )
        self._sequence += 1
