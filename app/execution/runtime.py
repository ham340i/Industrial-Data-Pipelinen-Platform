"""Validated sequential DAG execution with isolated per-run data and history."""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import Literal
from uuid import uuid4

from pydantic import Field

from app.blocks.context import BlockContext, BlockEvent
from app.blocks.contracts import Contract, PortValues, Table
from app.blocks.errors import BlockError, BlockFailure
from app.blocks.registry import BlockRegistry
from app.execution.frames import Frame, FrameValues, to_frames, to_tables
from app.pipelines.models import Edge, Node, PipelineDefinition
from app.pipelines.validation import Diagnostic, diagnose

logger = logging.getLogger(__name__)

State = Literal["queued", "running", "completed", "failed", "skipped"]


class ExecutionLimits(Contract):
    max_nodes: int = Field(default=1000, ge=1)
    max_edges: int = Field(default=10000, ge=1)
    max_rows: int = Field(default=1000000, ge=1)
    max_cells: int = Field(default=10000000, ge=1)


class StateEvent(Contract):
    run_id: str
    node_id: str | None = None
    state: State


class InvalidPipeline(ValueError):
    def __init__(self, diagnostics: tuple[Diagnostic, ...]) -> None:
        self.diagnostics = diagnostics
        super().__init__("Pipeline validation failed before execution.")


class Cancellation:
    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


@dataclass
class ExecutionContext:
    run_id: str
    state: State = "queued"
    node_states: dict[str, State] = field(default_factory=dict)
    inputs: dict[str, FrameValues] = field(default_factory=dict, repr=False)
    outputs: dict[str, FrameValues] = field(default_factory=dict, repr=False)
    failures: dict[str, BlockFailure] = field(default_factory=dict)
    history: list[StateEvent] = field(default_factory=list)
    block_events: list[BlockEvent] = field(default_factory=list)


@dataclass
class _Run:
    """Per-run wiring shared by the executor's steps."""

    result: ExecutionContext
    token: Cancellation
    resolve_resource: Callable[[str], Path] | None
    workspace_root: Path | None
    on_state: Callable[[StateEvent], None] | None
    retained_rows: int = 0
    retained_cells: int = 0

    def transition(self, state: State, node_id: str | None = None) -> None:
        result = self.result
        if node_id is None:
            result.state = state
        else:
            result.node_states[node_id] = state
        event = StateEvent(run_id=result.run_id, node_id=node_id, state=state)
        result.history.append(event)
        if self.on_state is not None:
            try:
                self.on_state(event)
            except Exception as exc:
                # An observer (telemetry recorder) must never stop the run it
                # watches; the in-memory history above stays authoritative.
                logger.warning(
                    "Run %s state observer failed on %s: %s",
                    result.run_id,
                    state,
                    type(exc).__name__,
                )

    def context(self, node_id: str) -> BlockContext:
        return BlockContext(
            self.result.run_id,
            node_id,
            log_sink=self.result.block_events.append,
            resolve_resource=self.resolve_resource,
            workspace_root=self.workspace_root,
            is_cancelled=self.token.is_cancelled,
        )


def _frame_size(values: FrameValues) -> tuple[int, int]:
    frames = [v for port in values.values() for v in port if isinstance(v, Frame)]
    return (
        sum(v.data.height for v in frames),
        sum(v.data.height * v.data.width for v in frames),
    )


def _table_size(values: PortValues) -> tuple[int, int]:
    tables = [v for port in values.values() for v in port if isinstance(v, Table)]
    return (
        sum(len(v.rows) for v in tables),
        sum(len(v.rows) * len(v.data_schema.columns) for v in tables),
    )


class Executor:
    def __init__(
        self, registry: BlockRegistry, limits: ExecutionLimits | None = None
    ) -> None:
        self.registry = registry
        self.limits = limits or ExecutionLimits()

    def execute(
        self,
        definition: PipelineDefinition,
        *,
        run_id: str | None = None,
        resolve_resource: Callable[[str], Path] | None = None,
        cancellation: Cancellation | None = None,
        workspace_root: Path | None = None,
        on_state: Callable[[StateEvent], None] | None = None,
    ) -> ExecutionContext:
        graph = self._validated_copy(definition)
        identity = str(uuid4()) if run_id is None else run_id
        BlockContext(
            identity,
            "runtime",
            resolve_resource=resolve_resource,
            workspace_root=workspace_root,
        )
        run = _Run(
            ExecutionContext(identity),
            cancellation or Cancellation(),
            resolve_resource,
            workspace_root,
            on_state,
        )
        order = graph.topological_order()
        nodes = {node.id: node for node in graph.nodes}
        incoming: dict[str, list[Edge]] = {node_id: [] for node_id in order}
        for edge in sorted(graph.edges, key=lambda item: item.id):
            incoming[edge.target.node_id].append(edge)

        run.transition("queued")
        for node_id in order:
            run.transition("queued", node_id)
        run.transition("running")
        logger.info("Run %s started with %d node(s)", identity, len(order))
        for node_id in order:
            edges = incoming[node_id]
            skipped = self._skip_reason(run, node_id, edges)
            if skipped is not None:
                run.result.failures[node_id] = skipped
                run.transition("skipped", node_id)
                continue
            run.transition("running", node_id)
            run.transition(self._run_node(run, nodes[node_id], edges), node_id)
        result = run.result
        run.transition("failed" if result.failures else "completed")
        self._log_outcome(result, len(order))
        return result

    @staticmethod
    def _log_outcome(result: ExecutionContext, node_count: int) -> None:
        log = logger.warning if result.failures else logger.info
        log(
            "Run %s %s; %d of %d node(s) did not complete",
            result.run_id,
            result.state,
            len(result.failures),
            node_count,
        )

    def _validated_copy(self, definition: PipelineDefinition) -> PipelineDefinition:
        # Check size before cloning, then validate a detached definition.
        if (
            len(definition.nodes) > self.limits.max_nodes
            or len(definition.edges) > self.limits.max_edges
        ):
            raise BlockError("graph_limit", "Pipeline exceeds the graph budget.")
        graph = PipelineDefinition.from_json(definition.to_json())
        diagnostics = diagnose(graph, self.registry)
        if diagnostics:
            raise InvalidPipeline(diagnostics)
        return graph

    @staticmethod
    def _skip_reason(run: _Run, node_id: str, edges: list[Edge]) -> BlockFailure | None:
        states = run.result.node_states
        if run.token.is_cancelled():
            return BlockFailure(
                code="cancelled", reason="Execution was cancelled.", node_id=node_id
            )
        if any(states[edge.source.node_id] != "completed" for edge in edges):
            return BlockFailure(
                code="dependency_failed",
                reason="An upstream dependency did not complete.",
                node_id=node_id,
            )
        return None

    def _run_node(self, run: _Run, node: Node, edges: list[Edge]) -> State:
        """Run one block inside the retained-data budget; return its end state."""
        result, node_id = run.result, node.id
        try:
            inputs: FrameValues = {}
            for edge in edges:
                values = result.outputs[edge.source.node_id].get(edge.source.port, ())
                inputs[edge.target.port] = inputs.get(edge.target.port, ()) + values
            rows, cells = _frame_size(inputs)
            self._check_budget(run.retained_rows + rows, run.retained_cells + cells)
            # Detach fan-out inputs so branches cannot mutate one another.
            result.inputs[node_id] = to_frames(to_tables(inputs))
            context = run.context(node_id)
            context.check_cancelled()
            block = self.registry.resolve(node.block_id, node.block_version)
            raw_outputs = block.run(node.config, to_tables(inputs), context)
            output_rows, output_cells = _table_size(raw_outputs)
            rows += output_rows
            cells += output_cells
            self._check_budget(run.retained_rows + rows, run.retained_cells + cells)
            outputs = to_frames(raw_outputs)
            run.retained_rows += rows
            run.retained_cells += cells
            result.outputs[node_id] = outputs
        except BlockError as exc:
            result.inputs.pop(node_id, None)
            result.failures[node_id] = exc.at_node(node_id).failure
            logger.warning(
                "Run %s node %s failed: %s", result.run_id, node_id, exc.failure.code
            )
            return "failed"
        except Exception as exc:
            # Unknown block errors can embed data values; record only the type.
            result.inputs.pop(node_id, None)
            result.failures[node_id] = BlockFailure(
                code="execution_failed",
                reason="Block execution failed.",
                node_id=node_id,
            )
            logger.error(
                "Run %s node %s failed unexpectedly: %s",
                result.run_id,
                node_id,
                type(exc).__name__,
            )
            return "failed"
        return "completed"

    def _check_budget(self, rows: int, cells: int) -> None:
        if rows > self.limits.max_rows or cells > self.limits.max_cells:
            raise BlockError("data_limit", "Run exceeds its retained data budget.")
