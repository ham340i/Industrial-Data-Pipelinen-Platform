"""Golden, empty, null, type, precision and unsafe-config cases (#18)."""

from pathlib import Path
from typing import Any

import pytest

from app.blocks.context import BlockContext
from app.blocks.contracts import Column, DataSchema, Table
from app.blocks.errors import BlockError
from app.blocks.transforms import (
    Aggregate,
    Cast,
    Filter,
    Join,
    RenameColumns,
    SelectColumns,
    Sort,
)
from tests.test_file_blocks import run


def numbers(empty: bool = False) -> Table:
    return Table(
        data_schema=DataSchema(
            columns=(
                Column(name="n", dtype="integer", nullable=True),
                Column(name="label", dtype="string"),
            )
        ),
        rows=()
        if empty
        else (
            {"n": -1, "label": "a"},
            {"n": 0, "label": "b"},
            {"n": 1, "label": "c"},
            {"n": None, "label": "d"},
        ),
    )


@pytest.mark.parametrize(
    "operator,expected",
    [
        ("eq", [0]),
        ("ne", [-1, 1]),
        ("lt", [-1]),
        ("le", [-1, 0]),
        ("gt", [1]),
        ("ge", [0, 1]),
        ("is_null", [None]),
        ("is_not_null", [-1, 0, 1]),
    ],
)
def test_filter_operators(tmp_path: Path, operator: str, expected: list[int | None]):
    table = run(
        Filter(),
        tmp_path,
        {"column": "n", "operator": operator, "value_text": "0"},
        numbers(),
    )
    assert [row["n"] for row in table.rows] == expected
    assert table.data_schema == numbers().data_schema


@pytest.mark.parametrize(
    "value",
    [
        "null",
        "true",
        '"0"',
        "[]",
        "{}",
        "NaN",
        "Infinity",
        "0; import os",
        "__import__('os').system('x')",
        str(2**63),
    ],
)
def test_filter_rejects_invalid_typed_literals(tmp_path: Path, value: str):
    with pytest.raises(BlockError) as error:
        run(Filter(), tmp_path, {"column": "n", "value_text": value}, numbers())
    assert error.value.failure.code == "invalid_filter"


def test_string_filter_is_literal_and_bad_operator_rejected(tmp_path: Path):
    dangerous = "__import__('os').system('x')"
    table = run(
        Filter(), tmp_path, {"column": "label", "value_text": dangerous}, numbers()
    )
    assert table.rows == ()
    with pytest.raises(BlockError) as error:
        run(
            Filter(),
            tmp_path,
            {"column": "label", "operator": "eval", "value_text": "x"},
            numbers(),
        )
    assert error.value.failure.code == "invalid_config"


def test_number_filter_rejects_false_precision_tie(tmp_path: Path):
    source = Table(
        data_schema=DataSchema(columns=(Column(name="n", dtype="number"),)),
        rows=({"n": float(2**53)},),
    )
    with pytest.raises(BlockError) as error:
        run(Filter(), tmp_path, {"column": "n", "value_text": str(2**53 + 1)}, source)
    assert error.value.failure.code == "invalid_filter"
    actual = run(Filter(), tmp_path, {"column": "n", "value_text": str(2**53)}, source)
    assert actual == source


@pytest.mark.parametrize(
    "block,config",
    [
        (SelectColumns(), {"columns": ["missing"]}),
        (RenameColumns(), {"columns": ["missing"], "names": ["new"]}),
        (Filter(), {"column": "missing", "value_text": "0"}),
        (Cast(), {"column": "missing", "dtype": "string"}),
    ],
)
def test_missing_columns(tmp_path: Path, block: Any, config: dict[str, Any]):
    with pytest.raises(BlockError) as error:
        run(block, tmp_path, config, numbers())
    assert error.value.failure.code == "missing_column"


@pytest.mark.parametrize(
    "block,config",
    [
        (SelectColumns(), {"columns": []}),
        (SelectColumns(), {"columns": ["n", "n"]}),
        (RenameColumns(), {"columns": ["n", "n"], "names": ["a", "b"]}),
        (RenameColumns(), {"columns": ["n", "label"], "names": ["a", "a"]}),
        (RenameColumns(), {"columns": ["n"], "names": ["a", "b"]}),
    ],
)
def test_invalid_column_configuration(
    tmp_path: Path, block: Any, config: dict[str, Any]
):
    with pytest.raises(BlockError) as error:
        run(block, tmp_path, config, numbers())
    assert error.value.failure.code == "invalid_config"


def test_select_order_rename_collision_and_swap(tmp_path: Path):
    source = numbers()
    selected = run(SelectColumns(), tmp_path, {"columns": ["label", "n"]}, source)
    assert [c.name for c in selected.data_schema.columns] == ["label", "n"]
    assert selected.rows == source.rows
    with pytest.raises(BlockError) as error:
        run(RenameColumns(), tmp_path, {"columns": ["n"], "names": ["label"]}, source)
    assert error.value.failure.code == "duplicate_column"
    swapped = run(
        RenameColumns(),
        tmp_path,
        {"columns": ["n", "label"], "names": ["label", "n"]},
        source,
    )
    assert swapped.rows[0] == {"label": -1, "n": "a"}
    assert swapped.data_schema.columns[0].dtype == "integer"
    assert source == numbers()


@pytest.mark.parametrize(
    "block,config",
    [
        (SelectColumns(), {"columns": ["n"]}),
        (RenameColumns(), {"columns": ["n"], "names": ["value"]}),
        (Filter(), {"column": "n", "value_text": "0"}),
        (Cast(), {"column": "n", "dtype": "string"}),
    ],
)
def test_empty_transform_preserves_schema(
    tmp_path: Path, block: Any, config: dict[str, Any]
):
    table = run(block, tmp_path, config, numbers(True))
    assert table.rows == ()
    assert table.data_schema.columns


@pytest.mark.parametrize(
    "kind,values,target,expected",
    [
        ("string", ["1", None, "-2"], "integer", [1, None, -2]),
        ("string", ["true", None, "false"], "boolean", [True, None, False]),
        ("string", ["1.25", None, "-2.5"], "number", [1.25, None, -2.5]),
        ("integer", [0, None, 1], "boolean", [False, None, True]),
        ("integer", [1, None, -2], "number", [1.0, None, -2.0]),
        ("number", [1.0, None, -2.0], "integer", [1, None, -2]),
    ],
)
def test_valid_casts(
    tmp_path: Path, kind: Any, values: list[Any], target: str, expected: list[Any]
):
    source = Table(
        data_schema=DataSchema(columns=(Column(name="v", dtype=kind, nullable=True),)),
        rows=tuple({"v": v} for v in values),
    )
    actual = run(Cast(), tmp_path, {"column": "v", "dtype": target}, source)
    assert [r["v"] for r in actual.rows] == expected
    assert actual.data_schema.columns[0].dtype == target
    assert actual.data_schema.columns[0].nullable


@pytest.mark.parametrize(
    "kind,value,target",
    [
        ("string", "bad", "integer"),
        ("string", "1.5", "integer"),
        ("string", "yes", "boolean"),
        ("string", "NaN", "number"),
        ("string", str(2**63), "integer"),
        ("number", 1.5, "integer"),
        ("integer", 2**53 + 1, "number"),
        ("integer", 2, "boolean"),
    ],
)
def test_cast_failure_and_explicit_null_policy(
    tmp_path: Path, kind: Any, value: Any, target: str
):
    source = Table(
        data_schema=DataSchema(columns=(Column(name="v", dtype=kind),)),
        rows=({"v": value},),
    )
    with pytest.raises(BlockError) as error:
        run(Cast(), tmp_path, {"column": "v", "dtype": target}, source)
    assert error.value.failure.code == "cast_failed"
    assert error.value.failure.field == "v"
    actual = run(
        Cast(), tmp_path, {"column": "v", "dtype": target, "on_error": "null"}, source
    )
    assert actual.rows == ({"v": None},)
    assert actual.data_schema.columns[0].nullable

    # ---------------------------------------------------------------------------
    # Issue #24: Join transform
    # ---------------------------------------------------------------------------


def join_left_table() -> Table:
    return Table(
        data_schema=DataSchema(
            columns=(
                Column(name="customer_id", dtype="integer"),
                Column(name="region", dtype="string"),
                Column(name="customer_name", dtype="string"),
            )
        ),
        rows=(
            {
                "customer_id": 1,
                "region": "east",
                "customer_name": "Alpha",
            },
            {
                "customer_id": 1,
                "region": "east",
                "customer_name": "Alpha",
            },
            {
                "customer_id": 2,
                "region": "west",
                "customer_name": "Beta",
            },
            {
                "customer_id": 3,
                "region": "north",
                "customer_name": "Gamma",
            },
        ),
    )


def join_right_table() -> Table:
    return Table(
        data_schema=DataSchema(
            columns=(
                Column(name="customer_id", dtype="integer"),
                Column(name="amount", dtype="number", nullable=True),
                Column(name="segment", dtype="string"),
            )
        ),
        rows=(
            {
                "customer_id": 1,
                "amount": 10.0,
                "segment": "industrial",
            },
            {
                "customer_id": 1,
                "amount": 12.5,
                "segment": "industrial",
            },
            {
                "customer_id": 2,
                "amount": 5.0,
                "segment": "commercial",
            },
            {
                "customer_id": 4,
                "amount": None,
                "segment": "unknown",
            },
        ),
    )


def run_join(
    tmp_path: Path,
    config: dict[str, Any],
    left: Table | None = None,
    right: Table | None = None,
) -> Table:
    outputs = Join().run(
        config,
        {
            "left": (join_left_table() if left is None else left,),
            "right": (join_right_table() if right is None else right,),
        },
        BlockContext(
            run_id="join-test",
            node_id="join",
            workspace_root=tmp_path,
        ),
    )

    value = outputs["table"][0]
    assert isinstance(value, Table)
    return value


def test_join_inner_multiples_duplicate_keys(tmp_path: Path):
    actual = run_join(
        tmp_path,
        {
            "left_on": ["customer_id"],
            "right_on": ["customer_id"],
            "how": "inner",
            "cardinality": "many_to_many",
        },
    )

    assert actual.rows == (
        {
            "customer_id": 1,
            "region": "east",
            "customer_name": "Alpha",
            "amount": 10.0,
            "segment": "industrial",
        },
        {
            "customer_id": 1,
            "region": "east",
            "customer_name": "Alpha",
            "amount": 12.5,
            "segment": "industrial",
        },
        {
            "customer_id": 1,
            "region": "east",
            "customer_name": "Alpha",
            "amount": 10.0,
            "segment": "industrial",
        },
        {
            "customer_id": 1,
            "region": "east",
            "customer_name": "Alpha",
            "amount": 12.5,
            "segment": "industrial",
        },
        {
            "customer_id": 2,
            "region": "west",
            "customer_name": "Beta",
            "amount": 5.0,
            "segment": "commercial",
        },
    )

    assert actual.data_schema.columns == (
        Column(name="customer_id", dtype="integer"),
        Column(name="region", dtype="string"),
        Column(name="customer_name", dtype="string"),
        Column(name="amount", dtype="number", nullable=True),
        Column(name="segment", dtype="string"),
    )


def test_join_left_preserves_unmatched_left_rows(tmp_path: Path):
    actual = run_join(
        tmp_path,
        {
            "left_on": ["customer_id"],
            "right_on": ["customer_id"],
            "how": "left",
            "cardinality": "many_to_many",
        },
    )

    assert actual.rows[-1] == {
        "customer_id": 3,
        "region": "north",
        "customer_name": "Gamma",
        "amount": None,
        "segment": None,
    }

    amount_column = next(
        column for column in actual.data_schema.columns if column.name == "amount"
    )
    segment_column = next(
        column for column in actual.data_schema.columns if column.name == "segment"
    )

    assert amount_column.nullable
    assert segment_column.nullable


def test_join_rejects_missing_key(tmp_path: Path):
    with pytest.raises(BlockError) as error:
        run_join(
            tmp_path,
            {
                "left_on": ["missing"],
                "right_on": ["customer_id"],
                "how": "inner",
                "cardinality": "many_to_many",
            },
        )

    assert error.value.failure.code == "missing_column"


def test_join_rejects_mismatched_key_lengths(tmp_path: Path):
    with pytest.raises(BlockError) as error:
        run_join(
            tmp_path,
            {
                "left_on": ["customer_id", "region"],
                "right_on": ["customer_id"],
                "how": "inner",
                "cardinality": "many_to_many",
            },
        )

    assert error.value.failure.code == "invalid_config"


def test_join_rejects_invalid_one_to_one_cardinality(tmp_path: Path):
    with pytest.raises(BlockError) as error:
        run_join(
            tmp_path,
            {
                "left_on": ["customer_id"],
                "right_on": ["customer_id"],
                "how": "inner",
                "cardinality": "one_to_one",
            },
        )

    assert error.value.failure.code == "invalid_cardinality"


def test_join_rejects_duplicate_output_columns(tmp_path: Path):
    right = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="customer_id", dtype="integer"),
                Column(name="region", dtype="string"),
            )
        ),
        rows=(
            {
                "customer_id": 1,
                "region": "duplicate",
            },
        ),
    )

    with pytest.raises(BlockError) as error:
        run_join(
            tmp_path,
            {
                "left_on": ["customer_id"],
                "right_on": ["customer_id"],
                "how": "inner",
                "cardinality": "many_to_many",
            },
            right=right,
        )

    assert error.value.failure.code == "duplicate_column"


def test_join_rejects_mismatched_key_types(tmp_path: Path):
    right = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="customer_id", dtype="string"),
                Column(name="amount", dtype="number"),
            )
        ),
        rows=(
            {
                "customer_id": "1",
                "amount": 10.0,
            },
        ),
    )

    with pytest.raises(BlockError) as error:
        run_join(
            tmp_path,
            {
                "left_on": ["customer_id"],
                "right_on": ["customer_id"],
                "how": "inner",
                "cardinality": "many_to_many",
            },
            right=right,
        )

    assert error.value.failure.code == "join_key_type_mismatch"


def test_join_outer_preserves_right_only_key(tmp_path: Path):
    left = Table(
        data_schema=DataSchema(columns=(Column(name="id", dtype="integer"),)),
        rows=({"id": 1},),
    )
    right = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="id", dtype="integer"),
                Column(name="value", dtype="string"),
            )
        ),
        rows=({"id": 2, "value": "right-only"},),
    )

    actual = run_join(
        tmp_path,
        {
            "left_on": ["id"],
            "right_on": ["id"],
            "how": "outer",
            "cardinality": "many_to_many",
        },
        left=left,
        right=right,
    )

    assert {row["id"] for row in actual.rows} == {1, 2}
    assert {row["value"] for row in actual.rows} == {None, "right-only"}


def test_join_outer_coalesces_different_key_names(tmp_path: Path):
    left = Table(
        data_schema=DataSchema(columns=(Column(name="id", dtype="integer"),)),
        rows=({"id": 1},),
    )
    right = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="right_id", dtype="integer"),
                Column(name="value", dtype="string"),
            )
        ),
        rows=({"right_id": 2, "value": "right-only"},),
    )

    actual = run_join(
        tmp_path,
        {
            "left_on": ["id"],
            "right_on": ["right_id"],
            "how": "outer",
            "cardinality": "many_to_many",
        },
        left=left,
        right=right,
    )

    assert {row["id"] for row in actual.rows} == {1, 2}
    assert [column.name for column in actual.data_schema.columns] == [
        "id",
        "value",
    ]


def test_join_outer_coalesces_composite_keys(tmp_path: Path):
    left = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="tenant_id", dtype="integer"),
                Column(name="record_id", dtype="integer"),
            )
        ),
        rows=({"tenant_id": 1, "record_id": 10},),
    )
    right = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="tenant", dtype="integer"),
                Column(name="record", dtype="integer"),
                Column(name="value", dtype="string"),
            )
        ),
        rows=({"tenant": 2, "record": 20, "value": "right-only"},),
    )

    actual = run_join(
        tmp_path,
        {
            "left_on": ["tenant_id", "record_id"],
            "right_on": ["tenant", "record"],
            "how": "outer",
            "cardinality": "many_to_many",
        },
        left=left,
        right=right,
    )

    assert {(row["tenant_id"], row["record_id"]) for row in actual.rows} == {
        (1, 10),
        (2, 20),
    }


def test_join_outer_preserves_right_rows_when_left_is_empty(tmp_path: Path):
    left = Table(
        data_schema=DataSchema(columns=(Column(name="id", dtype="integer"),)),
        rows=(),
    )
    right = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="id", dtype="integer"),
                Column(name="value", dtype="string"),
            )
        ),
        rows=({"id": 2, "value": "right-only"},),
    )

    actual = run_join(
        tmp_path,
        {
            "left_on": ["id"],
            "right_on": ["id"],
            "how": "outer",
            "cardinality": "many_to_many",
        },
        left=left,
        right=right,
    )

    assert actual.rows == ({"id": 2, "value": "right-only"},)


def run_aggregate(
    tmp_path: Path,
    config: dict[str, Any],
    table: Table,
) -> Table:
    outputs = Aggregate().run(
        config,
        {"table": (table,)},
        BlockContext(
            run_id="aggregate-test",
            node_id="aggregate",
            workspace_root=tmp_path,
        ),
    )

    value = outputs["table"][0]
    assert isinstance(value, Table)
    return value


def aggregate_table() -> Table:
    return Table(
        data_schema=DataSchema(
            columns=(
                Column(name="region", dtype="string"),
                Column(name="amount", dtype="number", nullable=True),
                Column(name="units", dtype="integer"),
            )
        ),
        rows=(
            {"region": "east", "amount": 10.0, "units": 2},
            {"region": "east", "amount": 12.5, "units": 3},
            {"region": "west", "amount": 5.0, "units": 1},
            {"region": "west", "amount": None, "units": 4},
        ),
    )


def test_aggregate_grouped_sum_and_count(tmp_path: Path):
    actual = run_aggregate(
        tmp_path,
        {
            "group_by": ["region"],
            "operations": [
                {
                    "column": "amount",
                    "function": "sum",
                    "output_name": "amount_sum",
                },
                {
                    "column": "amount",
                    "function": "count",
                    "output_name": "amount_count",
                },
            ],
        },
        aggregate_table(),
    )

    assert actual.rows == (
        {
            "region": "east",
            "amount_sum": 22.5,
            "amount_count": 2,
        },
        {
            "region": "west",
            "amount_sum": 5.0,
            "amount_count": 1,
        },
    )

    assert [column.name for column in actual.data_schema.columns] == [
        "region",
        "amount_sum",
        "amount_count",
    ]


def test_aggregate_mean_ignores_null_values(tmp_path: Path):
    actual = run_aggregate(
        tmp_path,
        {
            "group_by": ["region"],
            "operations": [
                {
                    "column": "amount",
                    "function": "mean",
                    "output_name": "amount_mean",
                },
            ],
        },
        aggregate_table(),
    )

    assert actual.rows == (
        {"region": "east", "amount_mean": 11.25},
        {"region": "west", "amount_mean": 5.0},
    )


def test_aggregate_empty_input_preserves_schema(tmp_path: Path):
    source = Table(
        data_schema=aggregate_table().data_schema,
        rows=(),
    )

    actual = run_aggregate(
        tmp_path,
        {
            "group_by": ["region"],
            "operations": [
                {
                    "column": "amount",
                    "function": "sum",
                    "output_name": "amount_sum",
                },
                {
                    "column": "units",
                    "function": "count",
                    "output_name": "units_count",
                },
            ],
        },
        source,
    )

    assert actual.rows == ()
    assert [column.name for column in actual.data_schema.columns] == [
        "region",
        "amount_sum",
        "units_count",
    ]


def test_aggregate_rejects_missing_group_column(tmp_path: Path):
    with pytest.raises(BlockError) as error:
        run_aggregate(
            tmp_path,
            {
                "group_by": ["missing"],
                "operations": [
                    {
                        "column": "amount",
                        "function": "sum",
                        "output_name": "amount_sum",
                    },
                ],
            },
            aggregate_table(),
        )

    assert error.value.failure.code == "missing_column"


def test_aggregate_rejects_missing_operation_column(tmp_path: Path):
    with pytest.raises(BlockError) as error:
        run_aggregate(
            tmp_path,
            {
                "group_by": ["region"],
                "operations": [
                    {
                        "column": "missing",
                        "function": "sum",
                        "output_name": "total",
                    },
                ],
            },
            aggregate_table(),
        )

    assert error.value.failure.code == "missing_column"


def test_aggregate_rejects_duplicate_output_names(tmp_path: Path):
    with pytest.raises(BlockError) as error:
        run_aggregate(
            tmp_path,
            {
                "group_by": ["region"],
                "operations": [
                    {
                        "column": "amount",
                        "function": "sum",
                        "output_name": "value",
                    },
                    {
                        "column": "units",
                        "function": "count",
                        "output_name": "value",
                    },
                ],
            },
            aggregate_table(),
        )

    assert error.value.failure.code == "invalid_config"


def test_aggregate_rejects_integer_sum_overflow(tmp_path: Path):
    source = Table(
        data_schema=DataSchema(columns=(Column(name="value", dtype="integer"),)),
        rows=(
            {"value": 2**63 - 1},
            {"value": 1},
        ),
    )

    with pytest.raises(BlockError) as error:
        run_aggregate(
            tmp_path,
            {
                "group_by": [],
                "operations": [
                    {
                        "column": "value",
                        "function": "sum",
                        "output_name": "total",
                    }
                ],
            },
            source,
        )

    assert error.value.failure.code == "aggregate_overflow"


def test_aggregate_rejects_grouped_integer_sum_overflow(tmp_path: Path):
    source = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="group", dtype="string"),
                Column(name="value", dtype="integer"),
            )
        ),
        rows=(
            {"group": "a", "value": 2**63 - 1},
            {"group": "a", "value": 1},
        ),
    )

    with pytest.raises(BlockError) as error:
        run_aggregate(
            tmp_path,
            {
                "group_by": ["group"],
                "operations": [
                    {
                        "column": "value",
                        "function": "sum",
                        "output_name": "total",
                    }
                ],
            },
            source,
        )

    assert error.value.failure.code == "aggregate_overflow"


def test_aggregate_accepts_integer_sum_upper_boundary(tmp_path: Path):
    source = Table(
        data_schema=DataSchema(columns=(Column(name="value", dtype="integer"),)),
        rows=({"value": 2**63 - 1},),
    )

    actual = run_aggregate(
        tmp_path,
        {
            "group_by": [],
            "operations": [
                {
                    "column": "value",
                    "function": "sum",
                    "output_name": "total",
                }
            ],
        },
        source,
    )

    assert actual.rows == ({"total": 2**63 - 1},)


def test_aggregate_accepts_integer_sum_lower_boundary(tmp_path: Path):
    source = Table(
        data_schema=DataSchema(columns=(Column(name="value", dtype="integer"),)),
        rows=({"value": -(2**63)},),
    )

    actual = run_aggregate(
        tmp_path,
        {
            "group_by": [],
            "operations": [
                {
                    "column": "value",
                    "function": "sum",
                    "output_name": "total",
                }
            ],
        },
        source,
    )

    assert actual.rows == ({"total": -(2**63)},)


def run_sort(
    tmp_path: Path,
    config: dict[str, Any],
    table: Table,
) -> Table:
    outputs = Sort().run(
        config,
        {"table": (table,)},
        BlockContext(
            run_id="sort-test",
            node_id="sort",
            workspace_root=tmp_path,
        ),
    )

    value = outputs["table"][0]
    assert isinstance(value, Table)
    return value


def sort_table() -> Table:
    return Table(
        data_schema=DataSchema(
            columns=(
                Column(name="priority", dtype="integer", nullable=True),
                Column(name="sequence", dtype="integer"),
                Column(name="label", dtype="string"),
            )
        ),
        rows=(
            {
                "priority": None,
                "sequence": 1,
                "label": "null-first",
            },
            {
                "priority": 1,
                "sequence": 2,
                "label": "first",
            },
            {
                "priority": 1,
                "sequence": 3,
                "label": "second",
            },
            {
                "priority": None,
                "sequence": 4,
                "label": "null-second",
            },
        ),
    )


def test_sort_is_stable_and_places_nulls_last(tmp_path: Path):
    actual = run_sort(
        tmp_path,
        {
            "columns": [
                {
                    "column": "priority",
                    "descending": False,
                    "nulls_last": True,
                },
            ],
        },
        sort_table(),
    )

    assert actual.rows == (
        {
            "priority": 1,
            "sequence": 2,
            "label": "first",
        },
        {
            "priority": 1,
            "sequence": 3,
            "label": "second",
        },
        {
            "priority": None,
            "sequence": 1,
            "label": "null-first",
        },
        {
            "priority": None,
            "sequence": 4,
            "label": "null-second",
        },
    )

    assert actual.data_schema == sort_table().data_schema


def test_sort_supports_descending_nulls_first(tmp_path: Path):
    source = Table(
        data_schema=DataSchema(
            columns=(Column(name="value", dtype="integer", nullable=True),)
        ),
        rows=(
            {"value": 1},
            {"value": None},
            {"value": 3},
            {"value": 2},
        ),
    )

    actual = run_sort(
        tmp_path,
        {
            "columns": [
                {
                    "column": "value",
                    "descending": True,
                    "nulls_last": False,
                },
            ],
        },
        source,
    )

    assert actual.rows == (
        {"value": None},
        {"value": 3},
        {"value": 2},
        {"value": 1},
    )


def test_sort_supports_multiple_columns(tmp_path: Path):
    source = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="group", dtype="string"),
                Column(name="value", dtype="integer"),
                Column(name="sequence", dtype="integer"),
            )
        ),
        rows=(
            {"group": "b", "value": 1, "sequence": 1},
            {"group": "a", "value": 2, "sequence": 2},
            {"group": "a", "value": 1, "sequence": 3},
            {"group": "a", "value": 1, "sequence": 4},
        ),
    )

    actual = run_sort(
        tmp_path,
        {
            "columns": [
                {
                    "column": "group",
                    "descending": False,
                    "nulls_last": True,
                },
                {
                    "column": "value",
                    "descending": True,
                    "nulls_last": True,
                },
            ],
        },
        source,
    )

    assert actual.rows == (
        {"group": "a", "value": 2, "sequence": 2},
        {"group": "a", "value": 1, "sequence": 3},
        {"group": "a", "value": 1, "sequence": 4},
        {"group": "b", "value": 1, "sequence": 1},
    )


def test_sort_empty_input_preserves_schema(tmp_path: Path):
    source = Table(
        data_schema=DataSchema(
            columns=(
                Column(name="value", dtype="integer", nullable=True),
                Column(name="label", dtype="string"),
            )
        ),
        rows=(),
    )

    actual = run_sort(
        tmp_path,
        {
            "columns": [
                {
                    "column": "value",
                    "descending": False,
                    "nulls_last": True,
                },
            ],
        },
        source,
    )

    assert actual.rows == ()
    assert actual.data_schema == source.data_schema


def test_sort_rejects_missing_column(tmp_path: Path):
    with pytest.raises(BlockError) as error:
        run_sort(
            tmp_path,
            {
                "columns": [
                    {
                        "column": "missing",
                        "descending": False,
                        "nulls_last": True,
                    },
                ],
            },
            sort_table(),
        )

    assert error.value.failure.code == "missing_column"


def test_sort_rejects_duplicate_columns(tmp_path: Path):
    with pytest.raises(BlockError) as error:
        run_sort(
            tmp_path,
            {
                "columns": [
                    {
                        "column": "priority",
                        "descending": False,
                        "nulls_last": True,
                    },
                    {
                        "column": "priority",
                        "descending": True,
                        "nulls_last": False,
                    },
                ],
            },
            sort_table(),
        )

    assert error.value.failure.code == "invalid_config"
