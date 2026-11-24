# AI contribution: 50% or more AI-generated
"""Frame-native execution matches the Table path exactly (#121).

Every frame-native block is run both ways on the same inputs: results, error
codes and lifecycle events must be identical. The executor test proves the
row-by-row Table conversions are skipped between frame-native nodes.
"""

from pathlib import Path
from typing import Any, ClassVar

import polars as pl
import pytest

from app.blocks.base import Block
from app.blocks.context import BlockContext, BlockEvent
from app.blocks.contracts import (
    BlockConfig,
    BlockDescriptor,
    Column,
    DataSchema,
    Port,
    PortValues,
    Table,
)
from app.blocks.errors import BlockError
from app.blocks.frames import Frame, FrameValues, to_frames, to_tables
from app.blocks.registry import BlockRegistry
from app.blocks.transforms import Cast, Filter, RenameColumns, SelectColumns
from app.execution import Executor
from app.pipelines.models import Edge, Node, PipelineDefinition, PortReference

SCHEMA = DataSchema(
    columns=(
        Column(name="id", dtype="integer"),
        Column(name="name", dtype="string", nullable=True),
        Column(name="reading", dtype="number", nullable=True),
        Column(name="ok", dtype="boolean"),
    )
)
ROWS = (
    {"id": 1, "name": "pump A", "reading": 12.5, "ok": True},
    {"id": 2, "name": None, "reading": -3.0, "ok": False},
    {"id": 3, "name": "vanne é", "reading": None, "ok": True},
    {"id": 4, "name": "", "reading": 0.0, "ok": False},
)


def table(rows: tuple[dict[str, Any], ...] = ROWS) -> Table:
    return Table(data_schema=SCHEMA, rows=rows)


def context(events: list[BlockEvent] | None = None) -> BlockContext:
    sink = events.append if events is not None else None
    return BlockContext(run_id="frames", node_id="node", log_sink=sink)


def both_paths(block: Block[Any], config: dict[str, Any], source: Table) -> Table:
    """Run once per path, assert equal outputs and events, return the result."""
    table_events: list[BlockEvent] = []
    frame_events: list[BlockEvent] = []
    by_table = block.run(config, {"table": (source,)}, context(table_events))
    by_frame = block.run_frames(
        config, to_frames({"table": (source,)}), context(frame_events)
    )
    assert to_tables(by_frame) == by_table
    assert [e.event for e in frame_events] == [e.event for e in table_events]
    result = by_table["table"][0]
    assert isinstance(result, Table)
    return result


CASES = [
    (SelectColumns(), {"columns": ["reading", "id"]}),
    (SelectColumns(), {"columns": ["name"]}),
    (RenameColumns(), {"columns": ["name"], "names": ["label"]}),
    (RenameColumns(), {"columns": ["id", "ok"], "names": ["ok", "id"]}),
    (Filter(), {"column": "reading", "operator": "gt", "value_text": "0"}),
    (Filter(), {"column": "name", "operator": "is_null"}),
    (Filter(), {"column": "name", "operator": "eq", "value_text": "vanne é"}),
    (Filter(), {"column": "ok", "operator": "ne", "value_text": "true"}),
]


@pytest.mark.parametrize("block,config", CASES)
def test_frame_path_matches_table_path(block: Block[Any], config: dict[str, Any]):
    both_paths(block, config, table())


@pytest.mark.parametrize("block,config", CASES)
def test_frame_path_matches_on_empty_input(block: Block[Any], config: dict[str, Any]):
    assert both_paths(block, config, table(())).rows == ()


def test_known_outputs():
    kept = both_paths(
        Filter(), {"column": "reading", "operator": "gt", "value_text": "0"}, table()
    )
    assert [row["id"] for row in kept.rows] == [1]
    renamed = both_paths(
        RenameColumns(), {"columns": ["id", "ok"], "names": ["ok", "id"]}, table()
    )
    assert [c.name for c in renamed.data_schema.columns] == [
        "ok",
        "name",
        "reading",
        "id",
    ]
    assert renamed.rows[0]["ok"] == 1


@pytest.mark.parametrize(
    "block,config,code",
    [
        (SelectColumns(), {"columns": ["missing"]}, "missing_column"),
        (RenameColumns(), {"columns": ["id"], "names": ["name"]}, "duplicate_column"),
        (
            Filter(),
            {"column": "id", "operator": "eq", "value_text": "x"},
            "invalid_filter",
        ),
        (
            Filter(),
            {"column": "ok", "operator": "lt", "value_text": "true"},
            "invalid_filter",
        ),
        (SelectColumns(), {"columns": []}, "invalid_config"),
    ],
)
def test_errors_and_failure_events_match(
    block: Block[Any], config: dict[str, Any], code: str
):
    events: dict[str, list[BlockEvent]] = {"table": [], "frame": []}
    with pytest.raises(BlockError) as by_table:
        block.run(config, {"table": (table(),)}, context(events["table"]))
    with pytest.raises(BlockError) as by_frame:
        block.run_frames(
            config, to_frames({"table": (table(),)}), context(events["frame"])
        )
    assert by_table.value.failure.code == by_frame.value.failure.code == code
    assert by_frame.value.failure.node_id == "node"
    assert [e.error_code for e in events["frame"]] == [
        e.error_code for e in events["table"]
    ]


def frame(data: pl.DataFrame, schema: DataSchema = SCHEMA) -> FrameValues:
    return {"table": (Frame(data, schema),)}


def valid_data() -> pl.DataFrame:
    return Frame.from_table(table()).data


@pytest.mark.parametrize(
    "data",
    [
        valid_data().with_columns(pl.col("id").cast(pl.Int32)),
        valid_data().with_columns(pl.lit(None, dtype=pl.Int64).alias("id")),
        valid_data().with_columns(pl.lit(float("nan")).alias("reading")),
        valid_data().with_columns(pl.lit(float("inf")).alias("reading")),
        valid_data().select("name", "id", "reading", "ok"),
    ],
    ids=["wrong dtype", "null in non-nullable", "nan", "infinity", "column order"],
)
def test_invalid_input_frames_are_rejected(data: pl.DataFrame):
    with pytest.raises(BlockError) as error:
        SelectColumns().run_frames({"columns": ["id"]}, frame(data), context())
    assert error.value.failure.code == "invalid_inputs"


def test_wrong_input_cardinality_and_payload():
    block = SelectColumns()
    with pytest.raises(BlockError, match="cardinality"):
        block.run_frames({"columns": ["id"]}, {"table": ()}, context())
    with pytest.raises(BlockError) as error:
        # A Table where a Frame is required must be rejected at the boundary.
        wrong: Any = {"table": (table(),)}
        block.run_frames({"columns": ["id"]}, wrong, context())
    assert error.value.failure.code == "invalid_inputs"


class BadOutput(SelectColumns):
    """Claims one schema and returns data that breaks it."""

    def _execute_frames(
        self, config: Any, inputs: FrameValues, context: BlockContext
    ) -> FrameValues:
        data = pl.DataFrame({"id": [1, None]}, schema={"id": pl.Int64})
        return frame(data, DataSchema(columns=(Column(name="id", dtype="integer"),)))


def test_invalid_output_frames_are_rejected():
    with pytest.raises(BlockError) as error:
        BadOutput().run_frames(
            {"columns": ["id"]}, to_frames({"table": (table(),)}), context()
        )
    assert error.value.failure.code == "invalid_outputs"


class MutatingSelect(SelectColumns):
    def _execute_frames(
        self, config: Any, inputs: FrameValues, context: BlockContext
    ) -> FrameValues:
        source = inputs["table"][0]
        assert isinstance(source, Frame)
        source.data.insert_column(0, pl.Series("extra", [0] * source.data.height))
        return super()._execute_frames(config, inputs, context)


def test_blocks_cannot_mutate_caller_frames():
    inputs = to_frames({"table": (table(),)})
    MutatingSelect().run_frames({"columns": ["id"]}, inputs, context())
    original = inputs["table"][0]
    assert isinstance(original, Frame)
    assert original.data.columns == ["id", "name", "reading", "ok"]


def test_blocks_that_are_not_frame_native_use_the_table_path():
    config = {"column": "id", "dtype": "string"}
    by_frame = Cast().run_frames(config, to_frames({"table": (table(),)}), context())
    assert to_tables(by_frame) == Cast().run(config, {"table": (table(),)}, context())


class HookedSelect(SelectColumns):
    calls: ClassVar[list[str]] = []

    def before_execute(
        self, config: Any, inputs: PortValues, context: BlockContext
    ) -> None:
        self.calls.append("before")


def test_lifecycle_hooks_keep_the_table_path():
    HookedSelect.calls.clear()
    HookedSelect().run_frames(
        {"columns": ["id"]}, to_frames({"table": (table(),)}), context()
    )
    assert HookedSelect.calls == ["before"]


class Readings(Block[BlockConfig]):
    config_model = BlockConfig
    descriptor = BlockDescriptor(
        block_id="test.readings",
        version="1",
        block_type="source",
        name="Readings",
        category="test",
        outputs=(Port(name="table", data_schema=SCHEMA),),
    )

    def _execute(
        self, config: BlockConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        return {"table": (table(),)}


def chain() -> PipelineDefinition:
    nodes = [
        Node(id="source", block_id="test.readings", block_version="1"),
        Node(
            id="select",
            block_id="transform.select",
            block_version="1.0.0",
            config={"columns": ["id", "reading"]},
        ),
        Node(
            id="rename",
            block_id="transform.rename",
            block_version="1.0.0",
            config={"columns": ["reading"], "names": ["value"]},
        ),
        Node(
            id="filter",
            block_id="transform.filter",
            block_version="1.0.0",
            config={"column": "value", "operator": "ge", "value_text": "0"},
        ),
    ]
    names = [n.id for n in nodes]
    edges = [
        Edge(
            id=f"{a}-{b}",
            source=PortReference(node_id=a, port="table"),
            target=PortReference(node_id=b, port="table"),
        )
        for a, b in zip(names, names[1:], strict=False)
    ]
    return PipelineDefinition(nodes=tuple(nodes), edges=tuple(edges))


def test_executor_skips_table_conversion_between_frame_native_nodes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    registry = BlockRegistry()
    for block in (Readings(), SelectColumns(), RenameColumns(), Filter()):
        registry.register(block)
    conversions: list[int] = []
    original = Frame.to_table

    def counting(self: Frame) -> Table:
        conversions.append(self.data.height)
        return original(self)

    monkeypatch.setattr(Frame, "to_table", counting)
    result = Executor(registry).execute(chain(), workspace_root=tmp_path)
    assert result.failures == {}
    assert conversions == []
    output = result.outputs["filter"]["table"][0]
    assert isinstance(output, Frame)
    assert output.data.to_dicts() == [
        {"id": 1, "value": 12.5},
        {"id": 4, "value": 0.0},
    ]
