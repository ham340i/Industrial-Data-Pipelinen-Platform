"""Requirements-derived typed/null/boundary and diagnostic cases for #25."""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.blocks.catalog import registry
from app.blocks.context import BlockContext, BlockEvent
from app.blocks.contracts import Column, DataSchema, Table, PortValues
from app.blocks.tabular import DType
from app.blocks.errors import BlockError
from app.blocks.quality import NullCheck, NullHandling, RowCount, SchemaValidation
from app.blocks.registry import RegisteredBlock
from app.main import app


def sample(rows: tuple[dict[str, Any], ...] | None = None) -> Table:
    return Table(
        data_schema=DataSchema(
            columns=(
                Column(name="name", dtype="string"),
                Column(name="value", dtype="integer", nullable=True),
            )
        ),
        rows=rows
        if rows is not None
        else (
            {"name": "private-one", "value": None},
            {"name": "private-two", "value": 0},
            {"name": "private-three", "value": None},
        ),
    )


def run(
    block: RegisteredBlock,
    config: dict[str, Any],
    table: Table,
    events: list[BlockEvent] | None = None,
) -> Table:
    result = block.run(
        config,
        {"table": (table,)},
        BlockContext(
            "test",
            "quality",
            log_sink=events.append if events is not None else None,
        ),
    )["table"][0]
    assert isinstance(result, Table)
    return result


def test_null_fill_and_drop_hand_worked_rows():
    original = sample()
    filled = run(
        NullHandling(),
        {"policy": "fill", "columns": ["value"], "fill_values": {"value": -7}},
        original,
    )
    assert filled.rows == (
        {"name": "private-one", "value": -7},
        {"name": "private-two", "value": 0},
        {"name": "private-three", "value": -7},
    )
    assert filled.data_schema.columns[1].nullable is False
    dropped = run(NullHandling(), {"policy": "drop"}, original)
    assert dropped.rows == ({"name": "private-two", "value": 0},)
    assert original.rows[0]["value"] is None


@pytest.mark.parametrize(
    "dtype,value",
    [
        ("integer", 4),
        ("number", 1.25),
        ("number", 2),
        ("boolean", False),
        ("string", ""),
    ],
)
def test_fill_typed_values(dtype: DType, value: Any):
    table = Table(
        data_schema=DataSchema(columns=(Column(name="x", dtype=dtype, nullable=True),)),
        rows=({"x": None},),
    )
    output = run(NullHandling(), {"policy": "fill", "fill_values": {"x": value}}, table)
    assert output.rows == ({"x": value},)
    assert type(output.rows[0]["x"]) is type(value)


@pytest.mark.parametrize("value", [True, 1.5, "0"])
def test_fill_never_coerces_integer(value: Any):
    block, table = NullHandling(), sample()
    with pytest.raises(BlockError, match="declared types") as exc:
        run(
            block,
            {"policy": "fill", "columns": ["value"], "fill_values": {"value": value}},
            table,
        )
    assert exc.value.failure.code == "invalid_fill"


@pytest.mark.parametrize(
    "block,config",
    [
        (NullHandling(), {"policy": "guess"}),
        (NullHandling(), {"policy": "fill"}),
        (NullHandling(), {"policy": "fill", "fill_values": {"value": None}}),
        (NullHandling(), {"policy": "drop", "fill_values": {"value": 0}}),
        (NullHandling(), {"policy": "drop", "columns": ["value", "value"]}),
        (NullCheck(), {"max_nulls": -1}),
        (NullCheck(), {"max_nulls": True}),
        (NullCheck(), {"required": "false"}),
        (NullCheck(), {"columns": [""]}),
        (RowCount(), {"min_rows": 3, "max_rows": 2}),
        (RowCount(), {"min_rows": -1}),
        (RowCount(), {"max_rows": 1.5}),
        (SchemaValidation(), {"columns": []}),
        (SchemaValidation(), {"columns": [{"name": "x", "dtype": "integer"}] * 2}),
        (SchemaValidation(), {"columns": [{"name": "x", "dtype": "date"}]}),
        (RowCount(), {"unknown": 5}),
    ],
)
def test_invalid_configuration_rejected(block: RegisteredBlock, config: dict[str, Any]):
    table = sample()
    with pytest.raises(BlockError) as exc:
        run(block, config, table)
    assert exc.value.failure.code == "invalid_config"


@pytest.mark.parametrize(
    "block,config",
    [
        (NullCheck(), {"columns": ["missing"]}),
        (NullHandling(), {"policy": "drop", "columns": ["missing"]}),
        (
            NullHandling(),
            {
                "policy": "fill",
                "columns": ["value"],
                "fill_values": {"name": "private-fill"},
            },
        ),
    ],
)
def test_unavailable_or_mismatched_selection(
    block: RegisteredBlock, config: dict[str, Any]
):
    table = sample()
    with pytest.raises(BlockError):
        run(block, config, table)


@pytest.mark.parametrize("maximum,expected", [(1, "fail"), (2, "pass"), (3, "pass")])
def test_null_threshold_boundary(maximum: int, expected: str):
    events: list[BlockEvent] = []
    block, table = NullCheck(), sample()
    if expected == "fail":
        with pytest.raises(BlockError) as exc:
            run(block, {"max_nulls": maximum}, table, events)
        assert exc.value.failure.diagnostics[-1].row_indices == (0, 2)
    else:
        assert run(NullCheck(), {"max_nulls": maximum}, sample(), events) == sample()
    diagnostic = [e for e in events if e.event == "quality"][0].diagnostics[-1]
    assert (diagnostic.observed, diagnostic.maximum, diagnostic.status) == (
        2,
        maximum,
        expected,
    )


@pytest.mark.parametrize("count,valid", [(0, False), (1, True), (2, True), (3, False)])
def test_row_count_inclusive_bounds(count: int, valid: bool):
    table = sample(tuple({"name": "a", "value": i} for i in range(count)))
    block = RowCount()
    if valid:
        assert run(RowCount(), {"min_rows": 1, "max_rows": 2}, table) == table
    else:
        with pytest.raises(BlockError) as exc:
            run(block, {"min_rows": 1, "max_rows": 2}, table)
        diagnostic = exc.value.failure.diagnostics[0]
        assert (diagnostic.minimum, diagnostic.maximum, diagnostic.observed) == (
            1,
            2,
            count,
        )


def test_empty_inputs_keep_schema_and_zero_boundaries():
    table = sample(())
    assert run(RowCount(), {"max_rows": 0}, table) == table
    assert run(NullCheck(), {}, table) == table
    assert run(NullHandling(), {"policy": "drop"}, table).rows == ()
    assert (
        run(
            SchemaValidation(),
            {"columns": [c.model_dump() for c in table.data_schema.columns]},
            table,
        )
        == table
    )
    all_null = sample(({"name": "a", "value": None},))
    assert run(NullHandling(), {"policy": "drop"}, all_null).rows == ()


def test_schema_checks_metadata_values_and_extra_columns():
    block, original = SchemaValidation(), sample()
    config = {
        "columns": [
            {"name": "name", "dtype": "integer"},
            {"name": "missing", "dtype": "string"},
            {"name": "value", "dtype": "integer"},
        ]
    }
    with pytest.raises(BlockError) as exc:
        run(block, config, original)
    assert [d.code for d in exc.value.failure.diagnostics] == [
        "type_mismatch",
        "missing_column",
        "unexpected_null",
    ]
    assert exc.value.failure.node_id == "quality"
    with pytest.raises(BlockError) as extra:
        run(
            block,
            {"columns": [{"name": "name", "dtype": "string"}]},
            original,
        )
    assert extra.value.failure.diagnostics[0].code == "extra_column"
    assert (
        run(
            SchemaValidation(),
            {
                "columns": [{"name": "name", "dtype": "string"}],
                "allow_extra_columns": True,
            },
            sample(),
        )
        == sample()
    )
    # Nullable declaration can contain zero actual nulls; no coercion is needed.
    table = sample(({"name": "a", "value": 2},))
    assert (
        run(
            SchemaValidation(),
            {
                "columns": [
                    {"name": "name", "dtype": "string"},
                    {"name": "value", "dtype": "integer"},
                ]
            },
            table,
        )
        == table
    )


@pytest.mark.parametrize(
    "block,config",
    [
        (NullCheck(), {}),
        (RowCount(), {"min_rows": 4}),
        (SchemaValidation(), {"columns": [{"name": "absent", "dtype": "string"}]}),
    ],
)
def test_optional_violation_is_warning(block: RegisteredBlock, config: dict[str, Any]):
    events: list[BlockEvent] = []
    assert run(block, {**config, "required": False}, sample(), events) == sample()
    assert any(d.status == "warning" for e in events for d in e.diagnostics)
    assert events[-1].event == "succeeded"


def test_diagnostics_bounded_redacted_and_enforced_without_observer():
    table = sample(
        tuple({"name": "synthetic-private", "value": None} for _ in range(35))
    )
    events: list[BlockEvent] = []
    block = NullCheck()
    with pytest.raises(BlockError) as exc:
        run(block, {}, table, events)
    diagnostic = exc.value.failure.diagnostics[-1]
    assert diagnostic.observed == 35
    assert diagnostic.row_indices == tuple(range(20))
    assert events[-1].event == "failed"
    public = exc.value.failure.model_dump_json() + json.dumps(
        [e.model_dump() for e in events]
    )
    assert "synthetic-private" not in public

    def broken_observer(event: BlockEvent) -> None:
        raise RuntimeError("logging unavailable")

    context = BlockContext("test", "quality", log_sink=broken_observer)
    with pytest.raises(BlockError) as no_logger:
        block.run({}, {"table": (table,)}, context)
    assert no_logger.value.failure.code == "quality_failed"


def test_catalog_has_one_schema_implementation_and_safe_preview():
    response = TestClient(app).get("/api/v1/blocks")
    assert response.status_code == 200
    catalog = response.json()
    expected = {
        "transform.null_handling",
        "quality.schema_validation",
        "quality.null_check",
        "quality.row_count",
    }
    assert expected <= {entry["block_id"] for entry in catalog}
    assert [
        entry["name"]
        for entry in catalog
        if entry["block_id"] == "quality.schema_validation"
    ] == ["Validate Schema"]
    for name in expected:
        block = registry.resolve(name, "1.0.0")
        assert block.public_metadata()["config_schema"]["additionalProperties"] is False
        inputs: PortValues = {"table": (sample(),)}
        context = BlockContext("test", "preview")
        with pytest.raises(BlockError) as exc:
            block.preview({}, inputs, context)
        assert exc.value.failure.code == "preview_unsupported"


def test_selected_drop_preserves_other_null_columns_and_repeated_names():
    table = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="x", dtype="integer", nullable=True),
                Column(name="y", dtype="integer", nullable=True),
            )
        ),
        rows=({"x": 1, "y": None}, {"x": None, "y": 2}, {"x": 1, "y": None}),
    )
    output = run(NullHandling(), {"policy": "drop", "columns": ["x"]}, table)
    assert output.rows == ({"x": 1, "y": None}, {"x": 1, "y": None})
    assert [c.nullable for c in output.data_schema.columns] == [False, True]


@pytest.mark.parametrize("dtype,value", [("integer", 2**63), ("number", 2**53 + 1)])
def test_fill_rejects_platform_overflow_or_precision_loss(dtype: DType, value: int):
    table = Table(
        data_schema=DataSchema(columns=(Column(name="x", dtype=dtype, nullable=True),)),
        rows=({"x": None},),
    )
    block = NullHandling()
    with pytest.raises(BlockError):
        run(block, {"policy": "fill", "fill_values": {"x": value}}, table)


def test_empty_table_still_validates_declared_types():
    block, table = SchemaValidation(), sample(())
    with pytest.raises(BlockError) as exc:
        run(
            block,
            {
                "columns": [
                    {"name": "name", "dtype": "integer"},
                    {"name": "value", "dtype": "integer", "nullable": True},
                ]
            },
            table,
        )
    assert exc.value.failure.diagnostics[0].code == "type_mismatch"


def test_cancelled_quality_never_reports_success():
    events: list[BlockEvent] = []
    block = RowCount()
    inputs: PortValues = {"table": (sample(),)}
    context = BlockContext(
        "test", "cancelled", log_sink=events.append, is_cancelled=lambda: True
    )
    with pytest.raises(BlockError) as exc:
        block.run({}, inputs, context)
    assert exc.value.failure.code == "cancelled"
    assert all(e.event != "succeeded" for e in events)
