"""Issue #22 scheduling, failure isolation and shared primitive integration."""

import json
from pathlib import Path

import polars as pl
import pytest

from app.blocks.base import Block
from app.blocks.context import BlockContext
from app.blocks.contracts import (
    BlockConfig,
    BlockDescriptor,
    Column,
    ControlSignal,
    DataSchema,
    Port,
    PortValues,
    Table,
)
from app.blocks.errors import BlockError
from app.blocks.registry import BlockRegistry
from app.blocks.sample import AddConstantBlock, VALUE_SCHEMA
from app.execution import (
    Cancellation,
    ExecutionLimits,
    Executor,
    Frame,
    InvalidPipeline,
)
from app.pipelines.models import Edge, Node, PipelineDefinition, PortReference


class Source(Block[BlockConfig]):
    config_model = BlockConfig
    descriptor = BlockDescriptor(
        block_id="test.source",
        version="1",
        block_type="source",
        name="Source",
        category="test",
        outputs=(Port(name="table", data_schema=VALUE_SCHEMA),),
    )

    def _execute(
        self, config: BlockConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        return {"table": (Table(data_schema=VALUE_SCHEMA, rows=({"value": 2},)),)}


class Join(Block[BlockConfig]):
    config_model = BlockConfig
    descriptor = BlockDescriptor(
        block_id="test.join",
        version="1",
        block_type="transform",
        name="Join",
        category="test",
        inputs=(Port(name="table", data_schema=VALUE_SCHEMA, many=True),),
        outputs=(Port(name="table", data_schema=VALUE_SCHEMA),),
    )

    def _execute(
        self, config: BlockConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        tables = [value for value in inputs["table"] if isinstance(value, Table)]
        frame = pl.concat([Frame.from_table(table).data for table in tables])
        return {"table": (Frame(frame, VALUE_SCHEMA).to_table(),)}


def node(name: str, block: str = "test.source", version: str = "1") -> Node:
    return Node(id=name, block_id=block, block_version=version)


def edge(name: str, source: str, target: str) -> Edge:
    return Edge(
        id=name,
        source=PortReference(node_id=source, port="table"),
        target=PortReference(node_id=target, port="table"),
    )


def registry() -> BlockRegistry:
    result = BlockRegistry()
    for block in (Source(), Join(), AddConstantBlock()):
        result.register(block)
    return result


def diamond() -> PipelineDefinition:
    return PipelineDefinition(
        nodes=(
            node("source"),
            node("left", "synthetic.add_constant", "1.0.0"),
            Node(
                id="right",
                block_id="synthetic.add_constant",
                block_version="1.0.0",
                config={"amount": 5},
            ),
            node("join", "test.join"),
        ),
        edges=(
            edge("a", "source", "left"),
            edge("b", "source", "right"),
            edge("d", "left", "join"),
            edge("c", "right", "join"),
        ),
    )


def test_diamond_order_schema_and_isolated_runs():
    engine = Executor(registry())
    graph = diamond()
    first = engine.execute(graph)
    second = engine.execute(
        PipelineDefinition(nodes=graph.nodes[::-1], edges=graph.edges[::-1])
    )
    assert first.state == second.state == "completed"
    assert first.run_id != second.run_id
    assert [e.node_id for e in first.history if e.state == "running"] == [
        None,
        "source",
        "left",
        "right",
        "join",
    ]
    output = first.outputs["join"]["table"][0]
    assert isinstance(output, Frame)
    assert output.data.to_dicts() == [{"value": 7}, {"value": 3}]
    assert output.data_schema == VALUE_SCHEMA
    assert output.data.schema == {"value": pl.Int64}
    other = second.outputs["join"]["table"][0]
    assert isinstance(other, Frame) and output.data.equals(other.data)
    output.data.drop_in_place("value")
    assert other.data.columns == ["value"]
    for name in first.node_states:
        assert [e.state for e in first.history if e.node_id == name] == [
            "queued",
            "running",
            "completed",
        ]
    assert len(first.block_events) == 8


class Failing(Source):
    def before_execute(
        self, config: BlockConfig, inputs: PortValues, context: BlockContext
    ) -> None:
        raise BlockError("source_failed", "Synthetic source failed.", field="resource")


def test_failure_skips_transitive_dependents_but_runs_independent_branch():
    blocks = BlockRegistry()
    blocks.register(Failing())
    blocks.register(AddConstantBlock())
    blocks.register(Join())

    # Disconnected join with no required input is not valid; use a separate source type.
    class Independent(Source):
        descriptor = Source.descriptor.model_copy(
            update={"block_id": "test.independent"}
        )

    blocks.register(Independent())
    graph = diamond()
    graph = PipelineDefinition(
        nodes=(*graph.nodes, node("z", "test.independent")), edges=graph.edges
    )
    result = Executor(blocks).execute(graph)
    assert result.state == "failed"
    assert result.node_states == {
        "source": "failed",
        "left": "skipped",
        "right": "skipped",
        "join": "skipped",
        "z": "completed",
    }
    assert result.failures["source"].field == "resource"
    assert result.failures["join"].code == "dependency_failed"
    assert set(result.outputs) == {"z"}
    assert [e.event for e in result.block_events] == [
        "started",
        "failed",
        "started",
        "succeeded",
    ]


def test_validation_happens_before_any_execution():
    events: list[object] = []
    graph = PipelineDefinition(nodes=(node("a"), node("b", "missing")))
    with pytest.raises(InvalidPipeline) as error:
        Executor(registry()).execute(graph, on_state=events.append)
    assert error.value.diagnostics[0].code == "block_unavailable"
    assert events == []
    with pytest.raises(InvalidPipeline):
        Executor(registry()).execute(PipelineDefinition())


def test_cancellation_and_observer_failure():
    cancellation = Cancellation()

    def observe(event):
        if event.node_id == "source" and event.state == "completed":
            cancellation.cancel()
        raise RuntimeError("observer must not break execution")

    result = Executor(registry()).execute(
        diamond(), cancellation=cancellation, on_state=observe
    )
    assert result.node_states["source"] == "completed"
    assert result.node_states["join"] == "skipped"
    assert result.failures["left"].code == "cancelled"
    assert result.state == "failed"
    context = BlockContext("run", "node", is_cancelled=cancellation.is_cancelled)
    with pytest.raises(BlockError, match="cancelled"):
        context.check_cancelled()


def test_limits_fail_cleanly():
    with pytest.raises(BlockError, match="graph budget"):
        Executor(registry(), ExecutionLimits(max_nodes=1)).execute(diamond())
    result = Executor(registry(), ExecutionLimits(max_rows=1)).execute(diamond())
    assert result.node_states["source"] == "completed"
    assert result.failures["left"].code == "data_limit"
    assert result.node_states["join"] == "skipped"
    assert set(result.inputs) == {"source"}


@pytest.mark.parametrize("rows", [(), ({"s": None, "n": None, "b": None, "f": None},)])
def test_empty_and_null_schema_round_trip(rows):
    schema = DataSchema(
        columns=(
            Column(name="s", dtype="string", nullable=True),
            Column(name="n", dtype="integer", nullable=True),
            Column(name="b", dtype="boolean", nullable=True),
            Column(name="f", dtype="number", nullable=True),
        )
    )
    table = Table(data_schema=schema, rows=rows)
    frame = Frame.from_table(table)
    assert frame.to_table() == table
    assert frame.data.dtypes == [pl.String, pl.Int64, pl.Boolean, pl.Float64]


def test_primitive_golden_contract(tmp_path: Path):
    # Exact #10 definitions and implementations, now driven by the real executor.
    from experiments.headless_etl.spike import FIXTURES, registry as proof_registry

    graph = PipelineDefinition.from_json((FIXTURES / "pipeline.json").read_text())
    resources = {"input": FIXTURES / "input.csv", "output": tmp_path / "result.parquet"}
    result = Executor(proof_registry()).execute(
        graph, resolve_resource=resources.__getitem__
    )
    expected = json.loads((FIXTURES / "expected.json").read_text())
    actual = pl.read_parquet(resources["output"])
    assert result.state == "completed"
    assert actual.columns == expected["columns"]
    assert actual.to_dicts() == expected["rows"]


def test_raw_exception_redacted_and_no_partial_output():
    class Broken(Source):
        def after_execute(
            self, config: BlockConfig, outputs: PortValues, context: BlockContext
        ) -> None:
            raise RuntimeError("private-resource-path")

    blocks = BlockRegistry()
    blocks.register(Broken())
    result = Executor(blocks).execute(PipelineDefinition(nodes=(node("source"),)))
    assert result.outputs == {}
    assert result.failures["source"].code == "execution_failed"
    assert "private-resource" not in repr(result)


def test_control_signals_are_not_frames():
    class Trigger(Source):
        descriptor = BlockDescriptor(
            block_id="test.trigger",
            version="1",
            block_type="trigger",
            name="Trigger",
            category="test",
            outputs=(Port(name="table", kind="control"),),
        )

        def _execute(
            self, config: BlockConfig, inputs: PortValues, context: BlockContext
        ) -> PortValues:
            return {"table": (ControlSignal(),)}

    blocks = BlockRegistry()
    blocks.register(Trigger())
    result = Executor(blocks).execute(
        PipelineDefinition(nodes=(node("t", "test.trigger"),))
    )
    assert result.state == "completed"
    assert result.outputs["t"]["table"] == (ControlSignal(),)


def test_fanout_input_mutation_is_isolated():
    class Mutating(AddConstantBlock):
        def before_execute(self, config, inputs, context):
            table = inputs["table"][0]
            assert isinstance(table, Table)
            table.rows[0]["value"] = 100

    blocks = BlockRegistry()
    blocks.register(Source())
    blocks.register(Mutating())
    blocks.register(Join())
    result = Executor(blocks).execute(diamond())
    source = result.outputs["source"]["table"][0]
    saved_input = result.inputs["left"]["table"][0]
    assert isinstance(source, Frame) and isinstance(saved_input, Frame)
    assert source.data.to_dicts() == saved_input.data.to_dicts() == [{"value": 2}]


def test_runtime_schema_failure_blocks_downstream():
    class BadSchema(Source):
        def _execute(self, config, inputs, context):
            return {
                "table": (
                    Table(
                        data_schema=DataSchema(
                            columns=(Column(name="value", dtype="string"),)
                        ),
                        rows=({"value": "wrong type"},),
                    ),
                )
            }

    blocks = BlockRegistry()
    blocks.register(BadSchema())
    blocks.register(AddConstantBlock())
    blocks.register(Join())
    result = Executor(blocks).execute(diamond())
    assert result.failures["source"].code == "invalid_outputs"
    assert result.node_states["join"] == "skipped"
    assert result.outputs == {}


def test_lifecycle_and_definition_snapshot():
    calls = []

    class Hooks(Source):
        def before_execute(self, config, inputs, context):
            calls.append("before")

        def _execute(self, config, inputs, context):
            calls.append("execute")
            return super()._execute(config, inputs, context)

        def after_execute(self, config, outputs, context):
            calls.append("after")

    blocks = BlockRegistry()
    blocks.register(Hooks())
    blocks.register(AddConstantBlock())
    blocks.register(Join())
    graph = diamond()

    def observe(event):
        graph.nodes[1].config["amount"] = 99

    result = Executor(blocks).execute(graph, on_state=observe)
    assert calls == ["before", "execute", "after"]
    left = result.outputs["left"]["table"][0]
    assert isinstance(left, Frame) and left.data.to_dicts() == [{"value": 3}]


@pytest.mark.parametrize("dtype,value", [("integer", 2**70), ("number", 2**53 + 1)])
def test_unrepresentable_values_rejected(dtype, value):
    table = Table(
        data_schema=DataSchema(columns=(Column(name="v", dtype=dtype),)),
        rows=({"v": value},),
    )
    with pytest.raises(BlockError, match="represented"):
        Frame.from_table(table)
