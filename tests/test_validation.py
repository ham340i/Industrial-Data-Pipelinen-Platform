"""Execution-readiness diagnostics: logic, ordering and API contract (#21)."""

import json
import random
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import Field

from app.blocks import BlockConfig, BlockContext, BlockRegistry, Column, DataSchema
from app.blocks import Port, PortValues
from app.blocks.sample import VALUE_SCHEMA, AddConstantBlock, AddConstantConfig
from app.pipelines import validation as validation_module
from app.pipelines.api import ValidationRequest
from app.pipelines.models import GraphDraft
from app.pipelines.validation import describe_incompatibility, diagnose, validate

MATRIX = json.loads(
    (Path(__file__).parent / "fixtures" / "validation" / "matrix.json").read_text()
)["cases"]
URL = "/api/v1/pipelines/validate"


class SourceConfig(BlockConfig):
    resource_id: str = Field(min_length=1, max_length=128)


class NeverRuns(AddConstantBlock):
    def _execute(
        self, config: AddConstantConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        raise AssertionError("Validation must never execute blocks")


class SourceBlock(NeverRuns):
    config_model = SourceConfig  # type: ignore[assignment]
    descriptor = AddConstantBlock.descriptor.model_copy(
        update={"block_id": "synthetic.source", "block_type": "source", "inputs": ()}
    )


class SinkBlock(NeverRuns):
    config_model = BlockConfig  # type: ignore[assignment]
    descriptor = AddConstantBlock.descriptor.model_copy(
        update={
            "block_id": "synthetic.sink",
            "block_type": "sink",
            "outputs": (),
            "supports_preview": False,
            "preview_reason": "Sinks publish data.",
        }
    )


LABEL_SCHEMA = DataSchema(columns=(Column(name="value", dtype="string"),))


class LabelBlock(NeverRuns):
    descriptor = AddConstantBlock.descriptor.model_copy(
        update={
            "block_id": "synthetic.label",
            "inputs": (Port(name="table", data_schema=LABEL_SCHEMA),),
            "outputs": (Port(name="table", data_schema=LABEL_SCHEMA),),
        }
    )


def registry() -> BlockRegistry:
    catalog = BlockRegistry()
    for block in (SourceBlock(), NeverRuns(), SinkBlock(), LabelBlock()):
        catalog.register(block)
    return catalog


def draft(definition: dict[str, Any]) -> GraphDraft:
    return ValidationRequest.model_validate({"definition": definition}).definition


def located(report: Any) -> list[dict[str, Any]]:
    return [
        {key: item[key] for key in ("code", "node_id", "edge_id", "port", "field")}
        for item in report
    ]


@pytest.fixture
def api(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("app.pipelines.api.registry", registry())
    return client


# Unit: the full matrix, exact codes, locations and order.


@pytest.mark.parametrize("case", MATRIX, ids=[case["name"] for case in MATRIX])
def test_matrix_diagnostics(case: dict[str, Any]):
    report = validate(draft(case["definition"]), registry())
    assert report.valid is (not case["expected"])
    assert located(item.model_dump() for item in report.diagnostics) == case["expected"]
    for item in report.diagnostics:
        assert item.message.strip().endswith(".")


@pytest.mark.parametrize("case", MATRIX, ids=[case["name"] for case in MATRIX])
def test_order_is_independent_of_input_order(case: dict[str, Any]):
    expected = diagnose(draft(case["definition"]), registry())
    shuffler = random.Random(21)
    for _ in range(5):
        definition = json.loads(json.dumps(case["definition"]))
        shuffler.shuffle(definition["nodes"])
        shuffler.shuffle(definition["edges"])
        assert diagnose(draft(definition), registry()) == expected


def test_valid_matrix_case_also_passes_the_executor_gate():
    from app.pipelines import PipelineDefinition

    valid = next(case for case in MATRIX if not case["expected"])
    graph = PipelineDefinition.from_json(json.dumps(valid["definition"]))
    assert graph.validate_registry(registry()) == ("source", "add", "sink")


def test_cycle_reports_only_edges_on_the_loop():
    definition = next(case for case in MATRIX if case["name"] == "cycle")["definition"]
    report = diagnose(draft(definition), registry())
    # c -> sink is downstream of the loop but not part of it.
    assert "c-sink" not in {item.edge_id for item in report}
    assert {item.code for item in report} == {"cycle"}


def test_two_separate_cycles_are_both_reported():
    nodes = [
        {"id": key, "block_id": "synthetic.add_constant", "block_version": "1.0.0"}
        for key in "abcd"
    ]
    edges = [
        {
            "id": f"{s}{t}",
            "source": {"node_id": s, "port": "table"},
            "target": {"node_id": t, "port": "table"},
        }
        for s, t in ("ab", "ba", "cd", "dc")
    ]
    report = diagnose(draft({"nodes": nodes, "edges": edges}), registry())
    assert [item.edge_id for item in report] == ["ab", "ba", "cd", "dc"]


def test_messages_explain_the_fix_without_echoing_config_values():
    case = next(c for c in MATRIX if c["name"] == "missing_and_invalid_config")
    messages = {
        (item.node_id, item.field): item.message
        for item in diagnose(draft(case["definition"]), registry())
    }
    assert messages[("blank", "resource_id")] == "Enter a value for 'resource_id'."
    assert messages[("add", "colour")] == "Remove the unsupported setting 'colour'."
    assert "1000" in messages[("add", "amount")]
    assert "5000" not in " ".join(messages.values())
    assert "red" not in " ".join(messages.values())


def test_incompatible_ports_name_the_differing_column():
    case = next(c for c in MATRIX if c["name"] == "incompatible_port_types")
    (item,) = diagnose(draft(case["definition"]), registry())
    assert "column value is integer, expected string" in item.message


def data(name: str, schema: DataSchema = VALUE_SCHEMA, many: bool = False) -> Port:
    return Port(name=name, data_schema=schema, many=many)


@pytest.mark.parametrize(
    ("out", "expected"),
    [
        (Port(name="o", kind="control"), "sends control"),
        (data("o", many=True), "several tables"),
        (
            data("o", DataSchema(columns=(Column(name="x", dtype="integer"),))),
            "missing column(s) value; unexpected column(s) x",
        ),
        (
            data(
                "o",
                DataSchema(
                    columns=(Column(name="value", dtype="integer", nullable=True),)
                ),
            ),
            "may be empty",
        ),
        (
            data(
                "o",
                DataSchema(columns=VALUE_SCHEMA.columns, allow_extra_columns=True),
            ),
            "may add undeclared columns",
        ),
    ],
)
def test_incompatibility_descriptions(out: Port, expected: str):
    message = describe_incompatibility(out, data("i"))
    assert expected in message
    assert message.endswith("add a transform in between.")


def test_validation_does_not_mutate_the_draft():
    case = next(c for c in MATRIX if c["name"] == "missing_and_invalid_config")
    graph = draft(case["definition"])
    before = graph.model_dump()
    diagnose(graph, registry())
    assert graph.model_dump() == before


def test_large_chain_is_validated_without_recursion():
    count = 3000
    nodes = [
        {
            "id": "s",
            "block_id": "synthetic.source",
            "block_version": "1.0.0",
            "config": {"resource_id": "r"},
        }
    ] + [
        {
            "id": f"n{i:05}",
            "block_id": "synthetic.add_constant",
            "block_version": "1.0.0",
        }
        for i in range(count)
    ]
    chain = ["s"] + [f"n{i:05}" for i in range(count)]
    edges = [
        {
            "id": f"e{i:05}",
            "source": {"node_id": a, "port": "table"},
            "target": {"node_id": b, "port": "table"},
        }
        for i, (a, b) in enumerate(zip(chain, chain[1:], strict=False))
    ]
    assert diagnose(draft({"nodes": nodes, "edges": edges}), registry()) == ()
    edges.append(
        {
            "id": "loop",
            "source": {"node_id": chain[-1], "port": "table"},
            "target": {"node_id": "n00000", "port": "table"},
        }
    )
    report = diagnose(draft({"nodes": nodes, "edges": edges}), registry())
    assert {item.code for item in report} == {"cycle", "input_cardinality"}
    assert sum(item.code == "cycle" for item in report) == count


def test_every_code_has_a_rank():
    for case in MATRIX:
        for item in case["expected"]:
            assert item["code"] in validation_module._RANK


# Integration: HTTP contract.


@pytest.mark.parametrize("case", MATRIX, ids=[case["name"] for case in MATRIX])
def test_api_returns_structured_diagnostics(api: TestClient, case: dict[str, Any]):
    response = api.post(URL, json={"definition": case["definition"]})
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"valid", "diagnostics"}
    assert body["valid"] is (not case["expected"])
    assert located(body["diagnostics"]) == case["expected"]
    assert all(
        set(item) == {"code", "message", "node_id", "edge_id", "port", "field"}
        for item in body["diagnostics"]
    )


def test_api_is_deterministic_across_requests(api: TestClient):
    case = next(c for c in MATRIX if c["name"] == "missing_and_invalid_config")
    first = api.post(URL, json={"definition": case["definition"]}).json()
    assert api.post(URL, json={"definition": case["definition"]}).json() == first


def test_api_uses_the_production_catalog_by_default(client: TestClient):
    definition = {
        "schema_version": 1,
        "nodes": [
            {
                "id": "a",
                "block_id": "synthetic.add_constant",
                "block_version": "1.0.0",
                "config": {"amount": 1},
            }
        ],
        "edges": [],
    }
    body = client.post(URL, json={"definition": definition}).json()
    assert located(body["diagnostics"]) == [
        {
            "code": "missing_input",
            "node_id": "a",
            "edge_id": None,
            "port": "table",
            "field": None,
        }
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"definition": {"schema_version": 2}},
        {"definition": {"nodes": [{"id": "a"}]}},
        {"definition": {"nodes": "a"}},
        {"definition": []},
        {"definition": {}, "extra": True},
        {},
        {
            "definition": {
                "nodes": [
                    {
                        "id": "a",
                        "block_id": "synthetic.source",
                        "block_version": "1.0.0",
                        "config": {"password": "synthetic"},
                    }
                ]
            }
        },
        {
            "definition": {
                "nodes": [
                    {
                        "id": "a",
                        "block_id": "synthetic.source",
                        "block_version": "1.0.0",
                        "config": {"resource_id": "/Users/someone/data.csv"},
                    }
                ]
            }
        },
    ],
)
def test_malformed_requests_use_the_error_envelope(api: TestClient, payload: Any):
    response = api.post(URL, json=payload)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["message"].startswith("Invalid validation request.")
    assert "synthetic" not in response.text


def test_validation_does_not_touch_the_metadata_database(
    api: TestClient, monkeypatch: pytest.MonkeyPatch
):
    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Validation must not open a transaction")

    monkeypatch.setattr("app.metadata.database.Database.transaction", forbidden)
    valid = next(case for case in MATRIX if not case["expected"])
    assert api.post(URL, json={"definition": valid["definition"]}).json()["valid"]
