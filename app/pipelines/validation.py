"""Static execution-readiness diagnostics for a pipeline graph (#21).

This is the one rule set for "can this definition run?": the API returns every
diagnostic, and ``PipelineDefinition.validate_registry`` raises the first one.
Nothing here executes blocks, reads data or performs I/O. Data-dependent
quality checks happen at runtime and are out of scope.
"""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import Field, ValidationError

from app.blocks.contracts import Contract, Port, ports_compatible
from app.blocks.errors import BlockError
from app.blocks.registry import BlockRegistry, RegisteredBlock
from app.pipelines.models import GraphDraft, kahn_order


class Diagnostic(Contract):
    """One problem, located precisely enough for the editor to highlight it."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    node_id: str | None = None
    edge_id: str | None = None
    port: str | None = None
    field: str | None = None


class ValidationReport(Contract):
    valid: bool
    diagnostics: tuple[Diagnostic, ...]


# Diagnostics are grouped in this order, then sorted by location, so the same
# graph always yields the same list regardless of node or edge order.
_RANK = {
    code: rank
    for rank, codes in enumerate(
        (
            (
                "empty_pipeline",
                "duplicate_node",
                "duplicate_edge",
                "dangling_edge",
                "duplicate_connection",
                "dangling_layout",
            ),
            ("cycle",),
            ("block_unavailable", "version_unavailable", "invalid_block"),
            ("missing_config", "invalid_config", "unknown_config"),
            ("unknown_port", "incompatible_ports"),
            ("input_cardinality",),
            ("missing_input",),
        )
    )
    for code in codes
}


def _sort_key(item: Diagnostic) -> tuple[int, str, str, str, str, str, str]:
    return (
        _RANK[item.code],
        item.node_id or "",
        item.edge_id or "",
        item.port or "",
        item.field or "",
        item.code,
        item.message,
    )


def validate(draft: GraphDraft, registry: BlockRegistry) -> ValidationReport:
    diagnostics = diagnose(draft, registry)
    return ValidationReport(valid=not diagnostics, diagnostics=diagnostics)


def diagnose(draft: GraphDraft, registry: BlockRegistry) -> tuple[Diagnostic, ...]:
    found: list[Diagnostic] = []
    if not draft.nodes:
        found.append(
            Diagnostic(
                code="empty_pipeline",
                message="Add at least one block before running the pipeline.",
            )
        )

    # Later duplicates are reported; the first occurrence is checked further.
    nodes = {}
    for node in draft.nodes:
        if node.id in nodes:
            found.append(
                Diagnostic(
                    code="duplicate_node",
                    message="Another node already uses this ID. Give each node "
                    "a unique ID.",
                    node_id=node.id,
                )
            )
        else:
            nodes[node.id] = node

    edges = []
    edge_ids: set[str] = set()
    connections: set[tuple[str, str, str, str]] = set()
    for edge in sorted(draft.edges, key=lambda e: e.id):
        if edge.id in edge_ids:
            found.append(
                Diagnostic(
                    code="duplicate_edge",
                    message="Another connection already uses this ID.",
                    edge_id=edge.id,
                )
            )
            continue
        edge_ids.add(edge.id)
        missing = [
            end.node_id
            for end in (edge.source, edge.target)
            if end.node_id not in nodes
        ]
        if missing:
            found.append(
                Diagnostic(
                    code="dangling_edge",
                    message=f"This connection references node '{missing[0]}', "
                    "which does not exist. Delete the connection.",
                    edge_id=edge.id,
                )
            )
            continue
        key = (
            edge.source.node_id,
            edge.source.port,
            edge.target.node_id,
            edge.target.port,
        )
        if key in connections:
            found.append(
                Diagnostic(
                    code="duplicate_connection",
                    message="These ports are already connected. Delete the "
                    "repeated connection.",
                    node_id=edge.target.node_id,
                    edge_id=edge.id,
                )
            )
            continue
        connections.add(key)
        edges.append(edge)

    if draft.layout is not None:
        for node_id in sorted(draft.layout.positions.keys() - nodes.keys()):
            found.append(
                Diagnostic(
                    code="dangling_layout",
                    message=f"The layout positions node '{node_id}', which does "
                    "not exist.",
                    node_id=node_id,
                )
            )

    # Cycles: reuse the scheduler's ordering, then name exactly the edges that
    # lie on a loop (not those merely downstream of one).
    pairs = [(edge.source.node_id, edge.target.node_id) for edge in edges]
    _, blocked = kahn_order(nodes, pairs)
    if blocked:
        component = _components(blocked, pairs)
        for edge in edges:
            source, target = edge.source.node_id, edge.target.node_id
            if source in component and component.get(target) == component[source]:
                found.append(
                    Diagnostic(
                        code="cycle",
                        message="This connection is part of a cycle. Remove a "
                        "connection in the loop so data flows one way.",
                        node_id=source,
                        edge_id=edge.id,
                    )
                )

    blocks: dict[str, RegisteredBlock] = {}
    for node in nodes.values():
        try:
            block = registry.resolve(node.block_id, node.block_version)
        except BlockError as exc:
            found.append(_block_failure(exc.failure.code, node.id, node.block_id))
            continue
        blocks[node.id] = block
        found.extend(_config_diagnostics(block, node.id, node.config))

    incoming: dict[tuple[str, str], list[str]] = {}
    for edge in edges:
        source_block = blocks.get(edge.source.node_id)
        target_block = blocks.get(edge.target.node_id)
        if source_block is None or target_block is None:
            continue  # Already reported as an unavailable block.
        out = _port(source_block.descriptor.outputs, edge.source.port)
        inp = _port(target_block.descriptor.inputs, edge.target.port)
        for end, port, direction in (
            (edge.source, out, "output"),
            (edge.target, inp, "input"),
        ):
            if port is None:
                found.append(
                    Diagnostic(
                        code="unknown_port",
                        message=f"This block has no {direction} named "
                        f"'{end.port}'. Delete the connection and reconnect it.",
                        node_id=end.node_id,
                        edge_id=edge.id,
                        port=end.port,
                    )
                )
        if out is None or inp is None:
            continue
        incoming.setdefault((edge.target.node_id, inp.name), []).append(edge.id)
        if not ports_compatible(out, inp) or (out.many and not inp.many):
            found.append(
                Diagnostic(
                    code="incompatible_ports",
                    message=describe_incompatibility(out, inp),
                    node_id=edge.target.node_id,
                    edge_id=edge.id,
                    port=inp.name,
                )
            )

    for node_id, block in blocks.items():
        for port in block.descriptor.inputs:
            connected = sorted(incoming.get((node_id, port.name), ()))
            if port.required and not connected:
                found.append(
                    Diagnostic(
                        code="missing_input",
                        message=f"Connect an upstream output to the required "
                        f"input '{port.name}'.",
                        node_id=node_id,
                        port=port.name,
                    )
                )
            if not port.many:
                for edge_id in connected[1:]:
                    found.append(
                        Diagnostic(
                            code="input_cardinality",
                            message=f"Input '{port.name}' accepts one "
                            "connection. Delete the extra connection.",
                            node_id=node_id,
                            edge_id=edge_id,
                            port=port.name,
                        )
                    )

    return tuple(sorted(found, key=_sort_key))


def _port(ports: tuple[Port, ...], name: str) -> Port | None:
    return next((port for port in ports if port.name == name), None)


def _block_failure(code: str, node_id: str, block_id: str) -> Diagnostic:
    messages = {
        "version_unavailable": f"This version of '{block_id}' is not installed. "
        "Replace the node with an available version.",
        "block_unavailable": f"Block '{block_id}' is not installed. Replace or "
        "delete this node.",
    }
    return Diagnostic(
        code=code if code in messages else "invalid_block",
        message=messages.get(code, "This block's declaration is invalid."),
        node_id=node_id,
    )


def _config_diagnostics(
    block: RegisteredBlock, node_id: str, config: dict[str, object]
) -> list[Diagnostic]:
    try:
        block.config_model.model_validate(config)
    except ValidationError as exc:
        errors = exc.errors(include_input=False, include_url=False)
    except (ValueError, TypeError):
        return [
            Diagnostic(
                code="invalid_config",
                message="This block's configuration is invalid.",
                node_id=node_id,
            )
        ]
    else:
        return []
    found = []
    for error in errors:
        field = ".".join(str(part) for part in error["loc"]) or None
        label = f"'{field}'" if field else "the configuration"
        blank = error["type"] == "string_too_short" and (
            error.get("ctx", {}).get("min_length") == 1
        )
        if error["type"] == "missing" or blank:
            code, message = "missing_config", f"Enter a value for {label}."
        elif error["type"] == "extra_forbidden":
            code, message = "unknown_config", f"Remove the unsupported setting {label}."
        else:
            # Pydantic messages describe the constraint, never the input value.
            code, message = "invalid_config", f"Fix {label}: {error['msg']}."
        found.append(
            Diagnostic(code=code, message=message, node_id=node_id, field=field)
        )
    return found


def describe_incompatibility(out: Port, inp: Port) -> str:
    """Explain why ``ports_compatible`` rejected a connection, with a fix."""
    prefix = f"Output '{out.name}' cannot feed input '{inp.name}': "
    fix = " Connect a compatible output or add a transform in between."
    if out.kind != inp.kind:
        return f"{prefix}it sends {out.kind} but the input expects {inp.kind}.{fix}"
    if out.many and not inp.many:
        return f"{prefix}it produces several tables but the input accepts one.{fix}"
    if out.data_schema is None or inp.data_schema is None:
        return f"{prefix}their port contracts differ.{fix}"
    produced = {column.name: column for column in out.data_schema.columns}
    expected = {column.name: column for column in inp.data_schema.columns}
    reasons = []
    missing = [name for name in expected if name not in produced]
    if missing:
        reasons.append(f"missing column(s) {', '.join(missing)}")
    for name, column in expected.items():
        actual = produced.get(name)
        if actual is None:
            continue
        if actual.dtype != column.dtype:
            reasons.append(f"column {name} is {actual.dtype}, expected {column.dtype}")
        elif actual.nullable and not column.nullable:
            reasons.append(f"column {name} may be empty but the input requires values")
    if not inp.data_schema.allow_extra_columns:
        extra = [name for name in produced if name not in expected]
        if extra:
            reasons.append(f"unexpected column(s) {', '.join(extra)}")
        if out.data_schema.allow_extra_columns:
            reasons.append("it may add undeclared columns")
    detail = "; ".join(reasons) or "their table schemas differ"
    return f"{prefix}{detail}.{fix}"


def _components(
    nodes: Iterable[str], pairs: Iterable[tuple[str, str]]
) -> dict[str, int]:
    """Kosaraju's strongly connected components, iterative and deterministic."""
    members = set(nodes)
    forward: dict[str, list[str]] = {node: [] for node in members}
    backward: dict[str, list[str]] = {node: [] for node in members}
    for source, target in pairs:
        if source in members and target in members:
            forward[source].append(target)
            backward[target].append(source)
    finished: list[str] = []
    seen: set[str] = set()
    for start in sorted(members):
        if start in seen:
            continue
        seen.add(start)
        stack = [(start, iter(sorted(forward[start])))]
        while stack:
            node, children = stack[-1]
            for child in children:
                if child not in seen:
                    seen.add(child)
                    stack.append((child, iter(sorted(forward[child]))))
                    break
            else:
                stack.pop()
                finished.append(node)
    component: dict[str, int] = {}
    for index, start in enumerate(reversed(finished)):
        if start in component:
            continue
        component[start] = index
        pending = [start]
        while pending:
            for parent in backward[pending.pop()]:
                if parent not in component:
                    component[parent] = index
                    pending.append(parent)
    return component
