"""Golden, empty, null, type, precision and unsafe-config cases (#18)."""

from pathlib import Path
from typing import Any

import pytest

from app.blocks.contracts import Column, DataSchema, Table
from app.blocks.errors import BlockError
from app.blocks.transforms import Cast, Filter, RenameColumns, SelectColumns
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
