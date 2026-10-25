"""Bounded CSV → selection → Parquet proof using the shared SDK and DAG."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import polars as pl
import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
from pydantic import Field, field_validator

from app.blocks.base import Block
from app.blocks.context import BlockContext, BlockEvent
from app.blocks.contracts import (
    BlockConfig,
    BlockDescriptor,
    Column,
    DataSchema,
    NonBlank,
    Port,
    PortValues,
    Scalar,
    Table,
)
from app.blocks.errors import BlockError
from app.blocks.registry import BlockRegistry
from app.pipelines.models import PipelineDefinition

FIXTURES = Path(__file__).parent / "fixtures"
TABLE_PORT = Port(
    name="table", data_schema=DataSchema(columns=(), allow_extra_columns=True)
)


class ResourceConfig(BlockConfig):
    resource: NonBlank


class SelectConfig(BlockConfig):
    columns: list[NonBlank] = Field(min_length=1)

    @field_validator("columns")
    @classmethod
    def unique_columns(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("Selected columns must be unique")
        return value


def resource_path(context: BlockContext, name: str) -> Path:
    if context.resolve_resource is None:
        raise BlockError("resource_unavailable", "Resource resolver is required.")
    return context.resolve_resource(name)


class CsvSource(Block[ResourceConfig]):
    config_model = ResourceConfig
    descriptor = BlockDescriptor(
        block_id="spike.csv",
        version="1.0.0",
        block_type="source",
        name="Spike CSV",
        category="spike",
        outputs=(TABLE_PORT,),
    )

    def _execute(
        self, config: ResourceConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        with resource_path(context, config.resource).open(
            newline="", encoding="utf-8"
        ) as stream:
            reader = csv.reader(stream, strict=True)
            header = next(reader, [])
            if (
                not header
                or any(not name.strip() for name in header)
                or len(set(header)) != len(header)
            ):
                raise BlockError("invalid_csv", "CSV requires unique nonblank headers.")
            rows: list[dict[str, Scalar]] = []
            for values in reader:
                if len(values) != len(header):
                    raise BlockError(
                        "invalid_csv", "CSV row width differs from header."
                    )
                rows.append(dict(zip(header, values, strict=True)))
        schema = DataSchema(
            columns=tuple(Column(name=name, dtype="string") for name in header)
        )
        return {"table": (Table(data_schema=schema, rows=tuple(rows)),)}


class SelectColumns(Block[SelectConfig]):
    config_model = SelectConfig
    descriptor = BlockDescriptor(
        block_id="spike.select",
        version="1.0.0",
        block_type="transform",
        name="Spike Select Columns",
        category="spike",
        inputs=(TABLE_PORT,),
        outputs=(TABLE_PORT,),
    )

    def _execute(
        self, config: SelectConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        table = inputs["table"][0]
        assert isinstance(table, Table)
        columns = {column.name: column for column in table.data_schema.columns}
        if set(config.columns) - columns.keys():
            raise BlockError("missing_column", "A selected column is unavailable.")
        frame = pl.DataFrame(
            list(table.rows),
            schema={
                c.name: {
                    "string": pl.String,
                    "integer": pl.Int64,
                    "number": pl.Float64,
                    "boolean": pl.Boolean,
                }[c.dtype]
                for c in table.data_schema.columns
            },
        ).select(config.columns)
        return {
            "table": (
                Table(
                    data_schema=DataSchema(
                        columns=tuple(columns[name] for name in config.columns)
                    ),
                    rows=tuple(frame.to_dicts()),
                ),
            )
        }


class ParquetSink(Block[ResourceConfig]):
    config_model = ResourceConfig
    descriptor = BlockDescriptor(
        block_id="spike.parquet",
        version="1.0.0",
        block_type="sink",
        name="Spike Parquet",
        category="spike",
        inputs=(TABLE_PORT,),
    )

    def _execute(
        self, config: ResourceConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        table = inputs["table"][0]
        assert isinstance(table, Table)
        types = {
            "string": pa.string(),
            "integer": pa.int64(),
            "number": pa.float64(),
            "boolean": pa.bool_(),
        }
        schema = pa.schema(
            [
                pa.field(c.name, types[c.dtype], nullable=c.nullable)
                for c in table.data_schema.columns
            ]
        )
        arrow = pa.Table.from_pylist(list(table.rows), schema=schema)
        path = resource_path(context, config.resource)
        # Exclusive creation is outside cleanup: never remove an existing file.
        stream = path.open("xb")
        try:
            with stream:
                pq.write_table(arrow, stream)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return {}


def registry() -> BlockRegistry:
    result = BlockRegistry()
    for block in (CsvSource(), SelectColumns(), ParquetSink()):
        result.register(block)
    return result


def execute(
    definition: PipelineDefinition, resources: dict[str, Path], events: list[BlockEvent]
) -> dict[str, PortValues]:
    """Run a detached, validated DAG; stop on the first SDK failure."""
    graph = PipelineDefinition.from_json(definition.to_json())
    blocks = registry()
    order = graph.validate_registry(blocks)
    nodes = {node.id: node for node in graph.nodes}
    results: dict[str, PortValues] = {}
    for node_id in order:
        node = nodes[node_id]
        inputs: PortValues = {}
        for edge in graph.edges:
            if edge.target.node_id == node_id:
                inputs[edge.target.port] = (
                    inputs.get(edge.target.port, ())
                    + results[edge.source.node_id][edge.source.port]
                )
        context = BlockContext(
            run_id="headless-proof",
            node_id=node_id,
            log_sink=events.append,
            resolve_resource=resources.__getitem__,
        )
        results[node_id] = blocks.resolve(node.block_id, node.block_version).run(
            node.config, inputs, context
        )
    return results


def demo() -> dict[str, Any]:
    graph = PipelineDefinition.from_json((FIXTURES / "pipeline.json").read_text())
    expected = json.loads((FIXTURES / "expected.json").read_text())
    events: list[BlockEvent] = []
    with TemporaryDirectory(prefix="headless-etl-") as directory:
        output = Path(directory) / "result.parquet"
        execute(graph, {"input": FIXTURES / "input.csv", "output": output}, events)
        actual = pq.read_table(output)
        assert actual.column_names == expected["columns"]
        assert actual.to_pylist() == expected["rows"]
        assert all(
            field.type == pa.string() and not field.nullable for field in actual.schema
        )
        return {
            "verified": True,
            "rows": actual.num_rows,
            "columns": actual.column_names,
            "events": [event.model_dump(mode="json") for event in events],
        }


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True))
