"""Audited linear preview plans. Never call Executor, run(), sinks or timers."""

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
from app.pipelines.models import GraphDraft, Node
from app.pipelines.validation import diagnose
from app.preview.errors import PreviewError
from app.preview.models import (
    MAX_ANCESTORS,
    MAX_SECONDS,
    NullSummary,
    PreviewRequest,
    PreviewResult,
)

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
    ancestors = {payload.node_id}
    while True:
        added = {
            edge.source.node_id
            for edge in graph.edges
            if edge.target.node_id in ancestors
        } - ancestors
        if not added:
            break
        ancestors.update(added)
        if len(ancestors) > MAX_ANCESTORS:
            raise PreviewError(
                "preview_graph_limit",
                "Preview supports at most 20 nodes on the selected input path.",
            )
    edges = tuple(edge for edge in graph.edges if edge.target.node_id in ancestors)
    subset = GraphDraft(
        nodes=tuple(node for node in graph.nodes if node.id in ancestors), edges=edges
    )
    # Check capability first so sinks/timers/quality gates always explain why
    # they cannot be previewed, without reading any upstream resource.
    blocks: dict[str, RegisteredBlock] = {}
    for node in subset.nodes:
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
        blocks[node.id] = block
    target = blocks[payload.node_id]
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
    chain: list[tuple[Node, RegisteredBlock]] = []
    current = payload.node_id
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
            break
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
    return list(reversed(chain))


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

    with db.transaction() as session:
        if session.get(Project, project_id) is None:
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
    if workspace_root is None:
        raise PreviewError(
            "workspace_required",
            "Configure Workspace in Settings and prepare this project's "
            "data folder before previewing.",
        )
    try:
        base = workspace_root.resolve(strict=True)
        root = (base / project_id).resolve(strict=True)
        root.relative_to(base)
        if root == base or not root.is_dir() or root != base / project_id:
            raise ValueError("Project workspace must not alias another directory")
    except (OSError, ValueError):
        raise PreviewError(
            "workspace_required",
            "This project's data folder is missing "
            "or outside the configured workspace.",
        ) from None

    def resolve(resource: str) -> Path:
        if resource in bindings:
            path = bindings[resource]
            if path is None:
                raise BlockError("resource_unavailable", "No file binding")
            return root / path
        return root / resource

    observations: list[PreviewObservation] = []
    values: PortValues = {}
    request_id = str(uuid4())
    for node, block in plan:
        context = BlockContext(
            request_id,
            node.id,
            workspace_root=root,
            resolve_resource=resolve,
            is_cancelled=stopped,
            observe_preview=observations.append,
        )
        try:
            context.check_cancelled()
            values = block.preview(node.config, values, context, payload.limits)
            context.check_cancelled()
        except BlockError as exc:
            failure = exc.failure
            if failure.code == "cancelled":
                timed_out = monotonic() >= deadline
                raise PreviewError(
                    "preview_timeout" if timed_out else "preview_cancelled",
                    "Preview reached its time budget."
                    if timed_out
                    else "Preview was cancelled.",
                    node_id=node.id,
                ) from None
            code = (
                failure.code if failure.code in SAFE_BLOCK_ERRORS else "preview_failed"
            )
            raise PreviewError(
                code,
                SAFE_BLOCK_ERRORS.get(
                    code, "Preview failed. Check the input and configuration."
                ),
                node_id=node.id,
                field=failure.field,
            ) from None
    table = values[payload.output_port][0]
    if not isinstance(table, Table) or len(observations) != 1:
        raise PreviewError(
            "preview_failed", "The preview did not return valid source evidence."
        )
    observation = observations[0]
    # JSON numbers outside this range lose integer precision in the browser.
    # Reject explicitly instead of silently changing the displayed sample.
    for row in table.rows:
        for name, value in row.items():
            if type(value) is int and abs(value) > 2**53 - 1:
                raise PreviewError(
                    "preview_value_range",
                    "A sampled integer cannot be displayed exactly in the browser. "
                    "Configure this column as a string instead.",
                    node_id=payload.node_id,
                    field=name,
                )
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
        elapsed_ms=int((monotonic() - started) * 1000),
        evaluated_node_ids=tuple(node.id for node, _ in plan),
    )
