# AI contribution: below 50% AI-generated
"""Audited linear preview plans. Never call Executor, run(), sinks or timers."""

import logging
from collections.abc import Callable
from pathlib import Path
from threading import Event
from time import monotonic
from uuid import uuid4

from sqlalchemy import select

from app.blocks.context import BlockContext
from app.blocks.contracts import PortValues, PreviewObservation, Table
from app.blocks.errors import BlockError
from app.blocks.registry import BlockRegistry, RegisteredBlock
from app.metadata.database import Database
from app.metadata.models import Project, WorkspaceBinding
from app.pipelines.models import Edge, GraphDraft, Node
from app.pipelines.validation import diagnose
from app.preview.errors import PreviewError
from app.workspace import project_data_folder
from app.workspace_storage import pipeline_data_folder, visible_project
from app.metadata.models import Pipeline
from app.preview.models import (
    MAX_ANCESTORS,
    MAX_SECONDS,
    NullSummary,
    PreviewRequest,
    PreviewResult,
)

logger = logging.getLogger(__name__)

# SDK capability is necessary but not proof of bounded upstream work. These
# exact versions have reviewed read/row-preserving preview implementations.
SOURCE_POLICIES = {
    ("source.csv", "1.0.0"): ".csv",
    ("source.json", "1.0.0"): ".json",
    ("source.parquet", "1.0.0"): ".parquet",
}
SUPPORTED = frozenset(SOURCE_POLICIES) | frozenset(
    {
        ("transform.select", "1.0.0"),
        ("synthetic.add_constant", "1.0.0"),
    }
)
SAFE_BLOCK_ERRORS = {
    "file_unavailable": "Input file is missing or unreadable.",
    "unsafe_resource": "Resource must be a supported file "
    "inside this project's workspace.",
    "schema_mismatch": "The sampled data does not match the configured schema.",
    "cast_failed": "A sampled value cannot be converted to the configured type.",
    "missing_column": "A selected column is absent from the input schema.",
    "invalid_csv": "CSV format, encoding, headers or row widths are invalid.",
    "preview_columns": "Preview requires at most 128 columns "
    "with names of at most 128 characters.",
    "preview_field_limit": "A preview field exceeds 4096 characters.",
    "invalid_json": "JSON must be an array of records "
    "with unique keys and scalar values.",
    "invalid_parquet": "Parquet metadata or sampled data is invalid or unsupported.",
    "schema_required": "Provide an explicit schema for empty or all-null JSON columns.",
    "unsupported_type": "The sampled columns must have "
    "consistent supported scalar types.",
    "preview_decode_limit": "Parquet metadata or row groups exceed "
    "the preview decoding budget. Use smaller row groups or input.",
    "preview_read_limit": "Preview reached its input-byte or record-size budget. "
    "Use a smaller sample or input.",
    "preview_limit": "The limits cannot hold a row, or a block exceeded them.",
    "invalid_inputs": "The sampled input does not match this block's port schema.",
    "invalid_outputs": "The block returned an invalid preview schema or sample.",
    "invalid_config": "The block configuration is invalid.",
    "unsupported_value": "A sampled value exceeds the supported scalar range.",
    "resource_unavailable": "The project's resource binding does not provide a file.",
}


def _ancestors(graph: GraphDraft, node_id: str) -> set[str]:
    """The selected node plus every node that feeds it, within the size limit."""
    ancestors = {node_id}
    while True:
        added = {
            edge.source.node_id
            for edge in graph.edges
            if edge.target.node_id in ancestors
        } - ancestors
        if not added:
            return ancestors
        ancestors.update(added)
        if len(ancestors) > MAX_ANCESTORS:
            raise PreviewError(
                "preview_graph_limit",
                "Preview supports at most 20 nodes on the selected input path.",
            )


def _previewable_block(node: Node, registry: BlockRegistry) -> RegisteredBlock:
    try:
        block = registry.resolve(node.block_id, node.block_version)
    except BlockError:
        raise PreviewError(
            "preview_block_unavailable",
            "A block version on the selected input path is unavailable.",
            node_id=node.id,
        ) from None
    descriptor = block.descriptor
    if not descriptor.supports_preview or descriptor.block_type in (
        "sink",
        "trigger",
        "quality",
    ):
        raise PreviewError(
            "preview_unsupported",
            descriptor.preview_reason or "This block does not support preview.",
            node_id=node.id,
        )
    if (node.block_id, node.block_version) not in SUPPORTED:
        raise PreviewError(
            "preview_unsupported",
            "This block has no bounded upstream preview policy.",
            node_id=node.id,
        )
    return block


def _check_selected_output(payload: PreviewRequest, target: RegisteredBlock) -> None:
    if not any(
        port.name == payload.output_port and port.kind == "data"
        for port in target.descriptor.outputs
    ):
        raise PreviewError(
            "preview_output_missing",
            "Select a tabular output on this node.",
            node_id=payload.node_id,
            port=payload.output_port,
        )


def _check_static_validity(subset: GraphDraft, registry: BlockRegistry) -> None:
    problems = diagnose(subset, registry)
    if problems:
        first = problems[0]
        raise PreviewError(
            "preview_invalid_graph",
            first.message,
            node_id=first.node_id,
            port=first.port,
            field=first.field,
        )


def _input_chain(
    start: str,
    nodes: dict[str, Node],
    blocks: dict[str, RegisteredBlock],
    edges: tuple[Edge, ...],
) -> list[tuple[Node, RegisteredBlock]]:
    """Walk back from the selected node to its single file source."""
    chain: list[tuple[Node, RegisteredBlock]] = []
    current = start
    while True:
        node, block = nodes[current], blocks[current]
        chain.append((node, block))
        incoming = [edge for edge in edges if edge.target.node_id == current]
        if not incoming:
            if (node.block_id, node.block_version) not in SOURCE_POLICIES:
                raise PreviewError(
                    "preview_unsupported",
                    "The input path must start at a supported file source.",
                    node_id=current,
                )
            return list(reversed(chain))
        if (
            len(incoming) != 1
            or incoming[0].source.port != "table"
            or incoming[0].target.port != "table"
        ):
            raise PreviewError(
                "preview_unsupported",
                "Preview supports a single file source input path "
                "through row-preserving transforms.",
                node_id=current,
            )
        current = incoming[0].source.node_id


def selected_plan(
    payload: PreviewRequest, registry: BlockRegistry
) -> list[tuple[Node, RegisteredBlock]]:
    graph = payload.definition
    nodes = {node.id: node for node in graph.nodes}
    if len(nodes) != len(graph.nodes) or len({edge.id for edge in graph.edges}) != len(
        graph.edges
    ):
        raise PreviewError(
            "preview_invalid_graph", "Node and connection IDs must be unique."
        )
    if payload.node_id not in nodes:
        raise PreviewError(
            "preview_node_missing", "Select a node that exists in the current draft."
        )
    ancestors = _ancestors(graph, payload.node_id)
    edges = tuple(edge for edge in graph.edges if edge.target.node_id in ancestors)
    subset = GraphDraft(
        nodes=tuple(node for node in graph.nodes if node.id in ancestors), edges=edges
    )
    # Check capability first so sinks/timers/quality gates always explain why
    # they cannot be previewed, without reading any upstream resource.
    blocks = {node.id: _previewable_block(node, registry) for node in subset.nodes}
    _check_selected_output(payload, blocks[payload.node_id])
    _check_static_validity(subset, registry)
    return _input_chain(payload.node_id, nodes, blocks, edges)


def _plan_and_bindings(
    payload: PreviewRequest, project_id: str, db: Database, registry: BlockRegistry
) -> tuple[list[tuple[Node, RegisteredBlock]], dict[str, str | None]]:
    with db.transaction() as session:
        project = session.get(Project, project_id)
        if project is None or not visible_project(project, db):
            raise PreviewError(
                "project_not_found", "Project was not found.", status=404
            )
        plan = selected_plan(payload, registry)
        refs = [
            node.config.get("resource_ref")
            for node, _ in plan
            if (node.block_id, node.block_version) in SOURCE_POLICIES
        ]
        bindings = {
            row.resource_id: row.local_path
            for row in session.scalars(
                select(WorkspaceBinding).where(
                    WorkspaceBinding.project_id == project_id,
                    WorkspaceBinding.resource_id.in_(refs),
                )
            )
        }
    return plan, bindings


def _project_root(
    workspace_root: Path | None, project_id: str, db: Database, pipeline_id: str | None
) -> Path:
    if workspace_root is None:
        raise PreviewError(
            "workspace_required",
            "Configure Workspace in Settings and prepare this project's "
            "data folder before previewing.",
        )
    try:
        if pipeline_id:
            with db.transaction() as session:
                pipeline = session.get(Pipeline, pipeline_id)
                if pipeline is None or pipeline.project_id != project_id:
                    raise PreviewError(
                        "pipeline_not_found", "Pipeline was not found.", status=404
                    )
            return pipeline_data_folder(db, pipeline_id, root=workspace_root)
        with db.transaction() as session:
            project = session.get(Project, project_id)
            if project is not None and project.directory_name is not None:
                raise PreviewError(
                    "pipeline_required",
                    "Save a named pipeline before previewing its input files.",
                )
        return project_data_folder(workspace_root, project_id)
    except ValueError:
        raise PreviewError(
            "workspace_required",
            "This project's data folder is missing "
            "or outside the configured workspace.",
        ) from None


def _resolver(root: Path, bindings: dict[str, str | None]) -> Callable[[str], Path]:
    """Map a resource reference to its bound file inside the project folder."""

    def resolve(resource: str) -> Path:
        if resource in bindings:
            path = bindings[resource]
            if path is None:
                raise BlockError("resource_unavailable", "No file binding")
            return root / path
        return root / resource

    return resolve


def _block_failure(exc: BlockError, node_id: str, timed_out: bool) -> PreviewError:
    """Translate a block failure into fixed public text (no rejected values)."""
    failure = exc.failure
    if failure.code == "cancelled":
        return PreviewError(
            "preview_timeout" if timed_out else "preview_cancelled",
            "Preview reached its time budget."
            if timed_out
            else "Preview was cancelled.",
            node_id=node_id,
        )
    code = failure.code if failure.code in SAFE_BLOCK_ERRORS else "preview_failed"
    return PreviewError(
        code,
        SAFE_BLOCK_ERRORS.get(
            code, "Preview failed. Check the input and configuration."
        ),
        node_id=node_id,
        field=failure.field,
    )


def _check_displayable(table: Table, node_id: str) -> None:
    # JSON numbers outside this range lose integer precision in the browser.
    # Reject explicitly instead of silently changing the displayed sample.
    for row in table.rows:
        for name, value in row.items():
            if type(value) is int and abs(value) > 2**53 - 1:
                raise PreviewError(
                    "preview_value_range",
                    "A sampled integer cannot be displayed exactly in the browser. "
                    "Configure this column as a string instead.",
                    node_id=node_id,
                    field=name,
                )


def preview(
    payload: PreviewRequest,
    project_id: str,
    db: Database,
    registry: BlockRegistry,
    workspace_root: Path | None,
    cancelled: Event,
) -> PreviewResult:
    started = monotonic()
    deadline = started + MAX_SECONDS

    def stopped() -> bool:
        return cancelled.is_set() or monotonic() >= deadline

    plan, bindings = _plan_and_bindings(payload, project_id, db, registry)
    root = _project_root(
        workspace_root,
        project_id,
        db,
        str(payload.pipeline_id) if payload.pipeline_id else None,
    )

    observations: list[PreviewObservation] = []
    values: PortValues = {}
    request_id = str(uuid4())
    for node, block in plan:
        context = BlockContext(
            request_id,
            node.id,
            workspace_root=root,
            resolve_resource=_resolver(root, bindings),
            is_cancelled=stopped,
            observe_preview=observations.append,
        )
        try:
            context.check_cancelled()
            values = block.preview(node.config, values, context, payload.limits)
            context.check_cancelled()
        except BlockError as exc:
            logger.info("Preview stopped at node %s: %s", node.id, exc.failure.code)
            raise _block_failure(exc, node.id, monotonic() >= deadline) from None
    table = values[payload.output_port][0]
    if not isinstance(table, Table) or len(observations) != 1:
        raise PreviewError(
            "preview_failed", "The preview did not return valid source evidence."
        )
    _check_displayable(table, payload.node_id)
    elapsed_ms = int((monotonic() - started) * 1000)
    logger.info(
        "Preview of node %s evaluated %d block(s) in %d ms",
        payload.node_id,
        len(plan),
        elapsed_ms,
    )
    return _result(payload, table, observations[0], plan, elapsed_ms)


def _result(
    payload: PreviewRequest,
    table: Table,
    observation: PreviewObservation,
    plan: list[tuple[Node, RegisteredBlock]],
    elapsed_ms: int,
) -> PreviewResult:
    return PreviewResult(
        node_id=payload.node_id,
        output_port=payload.output_port,
        data_schema=table.data_schema,
        rows=table.rows,
        sample_row_count=len(table.rows),
        sample_cell_count=len(table.rows) * len(table.data_schema.columns),
        inspected_row_count=observation.inspected_rows,
        full_row_count=observation.full_row_count,
        truncated=observation.truncated,
        schema_scope=observation.schema_scope,
        full_count_scope=observation.full_count_scope,
        nulls=tuple(
            NullSummary(
                column=column.name,
                null_count=sum(row[column.name] is None for row in table.rows),
            )
            for column in table.data_schema.columns
        ),
        effective_limits=payload.limits,
        source_read_bytes=observation.read_bytes,
        elapsed_ms=elapsed_ms,
        evaluated_node_ids=tuple(node.id for node, _ in plan),
    )
