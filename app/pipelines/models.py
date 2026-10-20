"""Versioned authoring models and deterministic, headless DAG validation."""

from __future__ import annotations

import heapq
import json
from typing import Annotated, Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from app.blocks.contracts import (
    Contract,
    NonBlank,
    ports_compatible,
    require_public_json,
)
from app.blocks.errors import BlockError
from app.blocks.registry import BlockRegistry
from app.metadata.portable import portable_definition

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")]


class GraphError(ValueError):
    """Safe graph diagnostics independent of the API and execution engine."""

    def __init__(self, code: str, message: str, *, node_id: str | None = None) -> None:
        self.code = code
        self.node_id = node_id
        super().__init__(message)


class Node(Contract):
    id: Identifier
    block_id: NonBlank = Field(max_length=128)
    block_version: NonBlank = Field(max_length=32)
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("config", mode="before")
    @classmethod
    def check_config(cls, value: Any) -> dict[str, Any]:
        # Share the storage boundary, and additionally apply the SDK's public
        # policy (e.g. username and refresh_token). Neither function performs I/O.
        require_public_json(value)
        return portable_definition(value)


class PortReference(Contract):
    node_id: Identifier
    port: NonBlank = Field(max_length=128)


class Edge(Contract):
    id: Identifier
    source: PortReference
    target: PortReference


class Position(Contract):
    x: float = Field(allow_inf_nan=False)
    y: float = Field(allow_inf_nan=False)


class Layout(Contract):
    """Optional presentation data; never used for scheduling or compatibility."""

    positions: dict[Identifier, Position] = Field(default_factory=dict)


class PipelineDefinition(Contract):
    schema_version: Literal[1] = 1
    nodes: tuple[Node, ...] = ()
    edges: tuple[Edge, ...] = ()
    layout: Layout | None = None

    @field_validator("schema_version", mode="before")
    @classmethod
    def check_version(cls, value: Any) -> int:
        if type(value) is not int or value != 1:
            raise ValueError("Only integer schema_version 1 is supported.")
        return value

    @model_validator(mode="after")
    def check_structure(self) -> PipelineDefinition:
        node_ids = [node.id for node in self.nodes]
        if len(set(node_ids)) != len(node_ids):
            raise GraphError("duplicate_node", "Node IDs must be unique.")
        edge_ids = [edge.id for edge in self.edges]
        if len(set(edge_ids)) != len(edge_ids):
            raise GraphError("duplicate_edge", "Edge IDs must be unique.")
        known = set(node_ids)
        connections: set[tuple[str, str, str, str]] = set()
        for edge in self.edges:
            if edge.source.node_id not in known or edge.target.node_id not in known:
                raise GraphError("dangling_node", "An edge references an unknown node.")
            key = (
                edge.source.node_id,
                edge.source.port,
                edge.target.node_id,
                edge.target.port,
            )
            if key in connections:
                raise GraphError("duplicate_connection", "Connections must be unique.")
            connections.add(key)
        if self.layout is not None and self.layout.positions.keys() - known:
            raise GraphError("dangling_layout", "Layout references an unknown node.")
        self.topological_order()
        return self

    @classmethod
    def from_json(cls, value: str) -> PipelineDefinition:
        """Strict model JSON loading; unsupported schema versions are rejected."""
        return cls.model_validate_json(value)

    def to_dict(self, *, include_layout: bool = True) -> dict[str, Any]:
        """Export a detached, revalidated JSON object for storage or interchange.

        Revalidation catches mutations of dictionaries inside frozen models.
        Layout is optional; semantic exports always retain schema_version.
        """
        # Inspect originals before serialization can coerce tuples, runtime
        # objects or nonfinite values into otherwise-valid JSON representations.
        for node in self.nodes:
            require_public_json(node.config)
            portable_definition(node.config)
        if self.layout is not None:
            # Frozen models still contain mutable dictionaries. Validate the
            # original keys before JSON can turn e.g. integer 1 into string "1".
            Layout(positions=self.layout.positions)
        checked = type(self).model_validate_json(self.model_dump_json())
        result = checked.model_dump(mode="json", exclude_none=True)
        if not include_layout:
            result.pop("layout", None)
        return portable_definition(result)

    def to_json(self, *, include_layout: bool = True) -> str:
        return json.dumps(
            self.to_dict(include_layout=include_layout),
            sort_keys=True,
            allow_nan=False,
            separators=(",", ":"),
        )

    def topological_order(self) -> tuple[str, ...]:
        """Kahn's algorithm, choosing the lexicographically smallest ready ID.

        Multiple port edges between the same nodes form one scheduling dependency.
        Empty and disconnected DAGs are valid; this does not execute any blocks.
        """
        outgoing: dict[str, set[str]] = {node.id: set() for node in self.nodes}
        indegree = dict.fromkeys(outgoing, 0)
        for edge in self.edges:
            source, target = edge.source.node_id, edge.target.node_id
            if source not in outgoing or target not in outgoing:
                raise GraphError("dangling_node", "An edge references an unknown node.")
            if target not in outgoing[source]:
                outgoing[source].add(target)
                indegree[target] += 1
        ready = [node for node, degree in indegree.items() if degree == 0]
        heapq.heapify(ready)
        ordered: list[str] = []
        while ready:
            node = heapq.heappop(ready)
            ordered.append(node)
            for target in sorted(outgoing[node]):
                indegree[target] -= 1
                if indegree[target] == 0:
                    heapq.heappush(ready, target)
        if len(ordered) != len(outgoing):
            raise GraphError("cycle", "Pipeline graph contains a cycle.")
        return tuple(ordered)

    def validate_registry(self, registry: BlockRegistry) -> tuple[str, ...]:
        """Validate a complete graph against exact SDK versions, without running.

        Authoring models can load before a registry is available. Call this
        additional check before handing a complete definition to an executor.
        """
        graph = type(self).from_json(self.to_json())
        blocks = {}
        for node in graph.nodes:
            try:
                block = registry.resolve(node.block_id, node.block_version)
                block.config_model.model_validate(node.config)
            except (BlockError, ValidationError, ValueError, TypeError):
                raise GraphError(
                    "invalid_block_config",
                    "Block version or configuration is invalid.",
                    node_id=node.id,
                ) from None
            blocks[node.id] = block
        incoming: dict[tuple[str, str], int] = {}
        for edge in graph.edges:
            outputs = {
                port.name: port
                for port in blocks[edge.source.node_id].descriptor.outputs
            }
            inputs = {
                port.name: port
                for port in blocks[edge.target.node_id].descriptor.inputs
            }
            out = outputs.get(edge.source.port)
            inp = inputs.get(edge.target.port)
            if out is None or inp is None:
                raise GraphError("unknown_port", "An edge references an unknown port.")
            if not ports_compatible(out, inp) or (out.many and not inp.many):
                raise GraphError(
                    "incompatible_ports", "Connected port contracts differ."
                )
            key = (edge.target.node_id, edge.target.port)
            incoming[key] = incoming.get(key, 0) + 1
            if incoming[key] > 1 and not inp.many:
                raise GraphError(
                    "input_cardinality", "An input has too many connections."
                )
        for node in graph.nodes:
            for port in blocks[node.id].descriptor.inputs:
                if port.required and (node.id, port.name) not in incoming:
                    raise GraphError(
                        "missing_input",
                        "A required input is unconnected.",
                        node_id=node.id,
                    )
        return graph.topological_order()
