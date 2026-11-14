"""Strict public preview contracts, independent of persistence and execution."""

import json
from typing import Any, Literal

from pydantic import Field, field_validator

from app.blocks.contracts import Contract, DataSchema, PreviewLimits, Scalar
from app.pipelines.models import Edge, GraphDraft, Identifier, Node

MAX_REQUEST_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_ANCESTORS = 20
MAX_SECONDS = 5.0
MAX_CONCURRENT = 2


class PreviewGraph(GraphDraft):
    nodes: tuple[Node, ...] = Field(min_length=1, max_length=100)
    edges: tuple[Edge, ...] = Field(default=(), max_length=200)
    layout: None = None


class PreviewRequest(Contract):
    definition: PreviewGraph
    node_id: Identifier
    output_port: str = Field(default="table", min_length=1, max_length=128)
    limits: PreviewLimits = Field(default_factory=PreviewLimits)

    @field_validator("definition", mode="before")
    @classmethod
    def graph(cls, value: Any) -> PreviewGraph:
        if isinstance(value, PreviewGraph):
            return value
        if not isinstance(value, dict):
            raise ValueError("Expected a semantic graph")
        return PreviewGraph.model_validate_json(json.dumps(value))


class NullSummary(Contract):
    column: str
    null_count: int = Field(ge=0)


class PreviewResult(Contract):
    node_id: str
    output_port: str
    data_schema: DataSchema
    rows: tuple[dict[str, Scalar], ...]
    sample_row_count: int
    sample_cell_count: int
    inspected_row_count: int
    full_row_count: int | None
    truncated: bool
    sampling_method: Literal["leading_rows"] = "leading_rows"
    schema_scope: Literal["declared", "header", "sample", "file_metadata"]
    full_count_scope: Literal["unknown", "observed", "file_metadata"]
    null_scope: Literal["returned_sample"] = "returned_sample"
    nulls: tuple[NullSummary, ...]
    effective_limits: PreviewLimits
    source_read_bytes: int
    elapsed_ms: int
    evaluated_node_ids: tuple[str, ...]
