"""Headless topology, serialization, portability and SDK integration for #9."""

import json
import os
import subprocess
import sys
from itertools import permutations
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.blocks import BlockContext, BlockRegistry, Column, DataSchema, Port, PortValues
from app.blocks.sample import VALUE_SCHEMA, AddConstantBlock, AddConstantConfig
from app.metadata.database import Database
from app.metadata.migrate import upgrade
from app.metadata.models import Pipeline, PipelineRevision, Project
from app.pipelines import (
    Edge,
    GraphError,
    Layout,
    Node,
    PipelineDefinition,
    PortReference,
    Position,
)


def node(identity: str, *, source: bool = False) -> Node:
    return Node(
        id=identity,
        block_id="synthetic.source" if source else "synthetic.add_constant",
        block_version="1.0.0",
    )


def edge(source: str, target: str, identity: str = "edge") -> Edge:
    return Edge(
        id=identity,
        source=PortReference(node_id=source, port="table"),
        target=PortReference(node_id=target, port="table"),
    )


def registry() -> BlockRegistry:
    class Source(AddConstantBlock):
        descriptor = AddConstantBlock.descriptor.model_copy(
            update={"block_id": "synthetic.source", "inputs": ()}
        )

        def _execute(
            self, config: AddConstantConfig, inputs: PortValues, context: BlockContext
        ) -> PortValues:
            raise AssertionError("Graph validation must never execute blocks")

    catalog = BlockRegistry()
    catalog.register(Source())
    catalog.register(AddConstantBlock())
    return catalog


def test_json_roundtrip_and_layout_independence():
    graph = PipelineDefinition(
        nodes=(node("a", source=True), node("b")),
        edges=(edge("a", "b"),),
        layout=Layout(positions={"a": Position(x=10, y=-20)}),
    )
    assert PipelineDefinition.from_json(graph.to_json()) == graph
    semantic = PipelineDefinition.from_json(graph.to_json(include_layout=False))
    assert semantic.layout is None
    assert semantic.topological_order() == graph.topological_order() == ("a", "b")
    exported = graph.to_dict()
    exported["nodes"][0]["config"]["amount"] = 5
    assert graph.nodes[0].config == {}
    assert graph.validate_registry(registry()) == ("a", "b")


def test_order_is_stable_across_input_permutations():
    nodes = (node("z"), node("b"), node("a"), node("c"))
    edges = (edge("a", "c", "ac"), edge("b", "c", "bc"))
    for reordered in permutations(nodes):
        for connections in permutations(edges):
            graph = PipelineDefinition(nodes=reordered, edges=connections)
            assert graph.topological_order() == ("a", "b", "c", "z")


def test_empty_and_disconnected_graphs():
    assert PipelineDefinition().topological_order() == ()
    assert PipelineDefinition(nodes=(node("b"), node("a"))).topological_order() == (
        "a",
        "b",
    )


@pytest.mark.parametrize(
    "nodes,edges,reason",
    [
        ((node("a"), node("a")), (), "Node IDs"),
        ((node("a"), node("b")), (edge("a", "b"), edge("b", "a")), "Edge IDs"),
        (
            (node("a"), node("b")),
            (edge("a", "b", "one"), edge("a", "b", "two")),
            "Connections",
        ),
        ((node("a"),), (edge("a", "missing"),), "unknown node"),
        ((node("a"),), (edge("a", "a"),), "cycle"),
        ((node("a"), node("b")), (edge("a", "b", "ab"), edge("b", "a", "ba")), "cycle"),
    ],
)
def test_invalid_graphs_are_rejected(nodes: Any, edges: Any, reason: str):
    with pytest.raises(ValidationError, match=reason):
        PipelineDefinition(nodes=nodes, edges=edges)


def test_parallel_port_edges_are_one_scheduling_dependency():
    other = Edge(
        id="other",
        source=PortReference(node_id="a", port="second"),
        target=PortReference(node_id="b", port="second"),
    )
    graph = PipelineDefinition(
        nodes=(node("a"), node("b")), edges=(edge("a", "b"), other)
    )
    assert graph.topological_order() == ("a", "b")


@pytest.mark.parametrize("version", [0, 2, True, "1", 1.0, None])
def test_unsupported_schema_versions(version: Any):
    with pytest.raises(ValidationError):
        PipelineDefinition.from_json(json.dumps({"schema_version": version}))


@pytest.mark.parametrize(
    "config",
    [
        {"nested": {"password": "synthetic"}},
        {"options": [{"API-Key": "synthetic"}]},
        {"username": "synthetic"},
        {"refresh_token": "synthetic"},
        {"secret_reference": "synthetic"},
        {"local_path": "relative.csv"},
        {"resource_id": "C:\\private\\data.csv"},
        {"resource_id": "/private/data.csv"},
        {"resource_id": "\\\\server\\share"},
        {"resource_id": "file:///private/data.csv"},
        {"value": float("nan")},
        {"value": object()},
        {"value": (1, 2)},
        {1: "bad-key"},
    ],
)
def test_nonportable_config(config: Any):
    with pytest.raises((ValidationError, ValueError, TypeError)):
        Node(id="source", block_id="source", block_version="1", config=config)


def test_valid_public_config_preserves_nulls_and_detaches():
    config: dict[str, Any] = {
        "resource_id": "measurements",
        "options": [None, True, 3, ""],
    }
    item = Node(id="source", block_id="source", block_version="1", config=config)
    config["options"].append(4)
    graph = PipelineDefinition(nodes=(item,))
    assert graph.to_dict()["nodes"][0]["config"]["options"] == [None, True, 3, ""]


def test_mutated_config_rechecked_at_export_and_registry_boundary():
    graph = PipelineDefinition(nodes=(node("a", source=True),))
    graph.nodes[0].config["password"] = "synthetic-private"
    for operation in (graph.to_json, lambda: graph.validate_registry(registry())):
        with pytest.raises((ValidationError, ValueError)):
            operation()


@pytest.mark.parametrize("value", [(1, 2), float("nan"), Path("runtime.csv")])
def test_mutation_cannot_be_coerced_by_json_export(value: Any):
    graph = PipelineDefinition(nodes=(node("a", source=True),))
    graph.nodes[0].config["value"] = value
    with pytest.raises((ValueError, TypeError)):
        graph.to_json()


def test_layout_rejects_unknown_nodes_and_nonfinite_coordinates():
    with pytest.raises(ValidationError, match="unknown node"):
        PipelineDefinition(layout=Layout(positions={"missing": Position(x=0, y=0)}))
    with pytest.raises(ValidationError):
        Position(x=float("inf"), y=0)


def test_unknown_fields_and_malformed_json():
    with pytest.raises(ValidationError):
        PipelineDefinition.from_json('{"schema_version":1,"execution_code":"x"}')
    with pytest.raises(ValidationError):
        PipelineDefinition.from_json('{"nodes":')


@pytest.mark.parametrize(
    "change",
    [
        {"block_version": "missing"},
        {"block_id": "missing"},
        {"config": {"amount": "bad"}},
    ],
)
def test_exact_registry_resolution_and_config_validation(change: dict[str, Any]):
    definition = node("a", source=True).model_dump() | change
    graph = PipelineDefinition(nodes=(Node.model_validate(definition),))
    with pytest.raises(GraphError) as caught:
        graph.validate_registry(registry())
    assert caught.value.code == "invalid_block_config"
    assert caught.value.node_id == "a"
    assert "bad" not in str(caught.value)


def test_unknown_port_and_missing_required_input():
    graph = PipelineDefinition(nodes=(node("a", source=True), node("b")))
    with pytest.raises(GraphError) as caught:
        graph.validate_registry(registry())
    assert caught.value.code == "missing_input"
    connection = edge("a", "b").model_dump()
    connection["source"]["port"] = "missing"
    graph = PipelineDefinition(
        nodes=graph.nodes, edges=(Edge.model_validate(connection),)
    )
    with pytest.raises(GraphError) as caught:
        graph.validate_registry(registry())
    assert caught.value.code == "unknown_port"


def test_multiple_connections_to_single_input_rejected():
    graph = PipelineDefinition(
        nodes=(node("a", source=True), node("b", source=True), node("c")),
        edges=(edge("a", "c", "ac"), edge("b", "c", "bc")),
    )
    with pytest.raises(GraphError) as caught:
        graph.validate_registry(registry())
    assert caught.value.code == "input_cardinality"


@pytest.mark.parametrize("control", [False, True])
def test_control_ports_remain_distinct(control: bool):
    class Trigger(AddConstantBlock):
        descriptor = AddConstantBlock.descriptor.model_copy(
            update={
                "block_id": "synthetic.trigger",
                "block_type": "trigger",
                "inputs": (),
                "outputs": (Port(name="table", kind="control"),),
            }
        )

    class Receiver(AddConstantBlock):
        descriptor = AddConstantBlock.descriptor.model_copy(
            update={"inputs": (Port(name="table", kind="control"),)}
        )

    catalog = BlockRegistry()
    catalog.register(Trigger())
    catalog.register(Receiver() if control else AddConstantBlock())
    graph = PipelineDefinition(
        nodes=(
            Node(id="a", block_id="synthetic.trigger", block_version="1.0.0"),
            node("b"),
        ),
        edges=(edge("a", "b"),),
    )
    if control:
        assert graph.validate_registry(catalog) == ("a", "b")
    else:
        with pytest.raises(GraphError) as caught:
            graph.validate_registry(catalog)
        assert caught.value.code == "incompatible_ports"


def test_definition_persists_in_existing_revision_schema(tmp_path: Any):
    graph = PipelineDefinition(nodes=(node("a", source=True),))
    database = Database(tmp_path / "metadata.sqlite3")
    try:
        upgrade(database)
        with database.transaction() as session:
            revision = PipelineRevision(
                id="revision",
                revision=1,
                definition=graph.to_dict(),
                pipeline=Pipeline(name="Example", project=Project(name="Synthetic")),
            )
            session.add(revision)
        with database.transaction() as session:
            loaded = session.get(PipelineRevision, "revision")
            assert loaded is not None
            assert PipelineDefinition.from_json(json.dumps(loaded.definition)) == graph
    finally:
        database.close()


@pytest.mark.parametrize("variant", ["open", "nullable", "wrong-type", "many"])
def test_registry_rejects_unsafe_output_guarantees(variant: str):
    schema = DataSchema(
        columns=(
            Column(
                name="value",
                dtype="string" if variant == "wrong-type" else "integer",
                nullable=variant == "nullable",
            ),
        ),
        allow_extra_columns=variant == "open",
    )

    class Source(AddConstantBlock):
        descriptor = AddConstantBlock.descriptor.model_copy(
            update={
                "block_id": "synthetic.source",
                "inputs": (),
                "outputs": (
                    Port(name="table", data_schema=schema, many=variant == "many"),
                ),
            }
        )

    catalog = BlockRegistry()
    catalog.register(Source())
    catalog.register(AddConstantBlock())
    graph = PipelineDefinition(
        nodes=(node("a", source=True), node("b")),
        edges=(edge("a", "b"),),
    )
    with pytest.raises(GraphError) as caught:
        graph.validate_registry(catalog)
    assert caught.value.code == "incompatible_ports"


def test_optional_and_many_input_connections():
    catalog = registry()

    class Receiver(AddConstantBlock):
        descriptor = AddConstantBlock.descriptor.model_copy(
            update={
                "block_id": "synthetic.receiver",
                "inputs": (
                    Port(
                        name="table",
                        data_schema=VALUE_SCHEMA,
                        many=True,
                        required=False,
                    ),
                ),
            }
        )

    catalog.register(Receiver())
    target = Node(id="c", block_id="synthetic.receiver", block_version="1.0.0")
    assert PipelineDefinition(nodes=(target,)).validate_registry(catalog) == ("c",)
    graph = PipelineDefinition(
        nodes=(node("a", source=True), node("b", source=True), target),
        edges=(edge("a", "c", "ac"), edge("b", "c", "bc")),
    )
    assert graph.validate_registry(catalog) == ("a", "b", "c")


def test_headless_import_does_not_initialize_database(tmp_path: Path):
    path = tmp_path / "not-created" / "metadata.sqlite3"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.pipelines import PipelineDefinition; "
            "assert PipelineDefinition().topological_order() == ()",
        ],
        cwd=tmp_path,
        env=dict(
            os.environ,
            PYTHONPATH=str(Path(__file__).resolve().parents[1]),
            LPS_METADATA_PATH=str(path),
        ),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not path.parent.exists()


@pytest.mark.parametrize("key", [1, True, None, 1.0])
@pytest.mark.parametrize("operation", ["dict", "json", "semantic", "registry"])
def test_mutated_layout_keys_are_checked_before_json_coercion(key: Any, operation: str):
    graph = PipelineDefinition(
        nodes=tuple(
            node(identity, source=True) for identity in ("1", "true", "null", "1.0")
        ),
        layout=Layout(positions={"1": Position(x=0, y=0)}),
    )
    assert graph.layout is not None
    graph.layout.positions.clear()
    graph.layout.positions[key] = Position(x=0, y=0)
    with pytest.raises(ValidationError):
        if operation == "dict":
            graph.to_dict()
        elif operation == "json":
            graph.to_json()
        elif operation == "semantic":
            graph.to_json(include_layout=False)
        else:
            graph.validate_registry(registry())


def test_mutated_valid_layout_positions_still_roundtrip():
    graph = PipelineDefinition(
        nodes=(node("1", source=True),),
        layout=Layout(positions={"1": Position(x=0, y=0)}),
    )
    assert graph.layout is not None
    graph.layout.positions["1"] = Position(x=40, y=60)
    assert PipelineDefinition.from_json(graph.to_json()) == graph
    assert graph.validate_registry(registry()) == ("1",)
