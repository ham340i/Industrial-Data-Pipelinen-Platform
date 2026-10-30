"""Validated sequential DAG execution with isolated per-run data and history."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import Literal
from uuid import uuid4

from pydantic import Field

from app.blocks.context import BlockContext, BlockEvent
from app.blocks.contracts import Contract, Table
from app.blocks.errors import BlockError, BlockFailure
from app.blocks.registry import BlockRegistry
from app.execution.frames import Frame, FrameValues, to_frames, to_tables
from app.pipelines.models import Edge, PipelineDefinition
from app.pipelines.validation import Diagnostic, diagnose

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
        identity = str(uuid4()) if run_id is None else run_id
        BlockContext(
            identity,
            "runtime",
            resolve_resource=resolve_resource,
            workspace_root=workspace_root,
        )
        result = ExecutionContext(identity)
        token = cancellation or Cancellation()
        order = graph.topological_order()
        nodes = {node.id: node for node in graph.nodes}
        incoming: dict[str, list[Edge]] = {node_id: [] for node_id in order}
        for edge in sorted(graph.edges, key=lambda item: item.id):
            incoming[edge.target.node_id].append(edge)

        def transition(state: State, node_id: str | None = None) -> None:
            if node_id is None:
                result.state = state
            else:
                result.node_states[node_id] = state
            event = StateEvent(run_id=identity, node_id=node_id, state=state)
            result.history.append(event)
            if on_state is not None:
                try:
                    on_state(event)
                except Exception:
                    pass

        transition("queued")
        for node_id in order:
            transition("queued", node_id)
        transition("running")
        retained_rows = retained_cells = 0
        for node_id in order:
            edges = incoming[node_id]
            cancelled = token.is_cancelled()
            if cancelled or any(
                result.node_states[e.source.node_id] != "completed" for e in edges
            ):
                code = "cancelled" if cancelled else "dependency_failed"
                result.failures[node_id] = BlockFailure(
                    code=code,
                    reason="Execution was cancelled."
                    if cancelled
                    else "An upstream dependency did not complete.",
                    node_id=node_id,
                )
                transition("skipped", node_id)
                continue
            transition("running", node_id)
            node = nodes[node_id]
            try:
                inputs: FrameValues = {}
                for edge in edges:
                    values = result.outputs[edge.source.node_id].get(
                        edge.source.port, ()
                    )
                    inputs[edge.target.port] = inputs.get(edge.target.port, ()) + values
                input_frames = [
                    v
                    for values in inputs.values()
                    for v in values
                    if isinstance(v, Frame)
                ]
                rows = sum(v.data.height for v in input_frames)
                cells = sum(v.data.height * v.data.width for v in input_frames)

                self._check_budget(retained_rows + rows, retained_cells + cells)
                # Detach fan-out inputs so branches cannot mutate one another.
                result.inputs[node_id] = to_frames(to_tables(inputs))
                context = BlockContext(
                    identity,
                    node_id,
                    log_sink=result.block_events.append,
                    resolve_resource=resolve_resource,
                    workspace_root=workspace_root,
                    is_cancelled=token.is_cancelled,
                )
                context.check_cancelled()
                block = self.registry.resolve(node.block_id, node.block_version)
                raw_outputs = block.run(node.config, to_tables(inputs), context)
                tables = [
                    v
                    for values in raw_outputs.values()
                    for v in values
                    if isinstance(v, Table)
                ]
                rows += sum(len(v.rows) for v in tables)
                cells += sum(len(v.rows) * len(v.data_schema.columns) for v in tables)
                self._check_budget(retained_rows + rows, retained_cells + cells)
                outputs = to_frames(raw_outputs)
                retained_rows += rows
                retained_cells += cells
                result.outputs[node_id] = outputs
            except BlockError as exc:
                result.inputs.pop(node_id, None)
                result.failures[node_id] = exc.at_node(node_id).failure
                transition("failed", node_id)
            except Exception:
                result.inputs.pop(node_id, None)
                result.failures[node_id] = BlockFailure(
                    code="execution_failed",
                    reason="Block execution failed.",
                    node_id=node_id,
                )
                transition("failed", node_id)
            else:
                transition("completed", node_id)
        transition("failed" if result.failures else "completed")
        return result

    def _check_budget(self, rows: int, cells: int) -> None:
        if rows > self.limits.max_rows or cells > self.limits.max_cells:
            raise BlockError("data_limit", "Run exceeds its retained data budget.")
