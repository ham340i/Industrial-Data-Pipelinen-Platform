# AI contribution: 50% or more AI-generated
"""Parser, type-checker, and derived-column tests for issue #138."""

from pathlib import Path

import polars as pl
import pytest

from app.blocks.context import BlockContext
from app.blocks.contracts import Column, DataSchema, Table
from app.blocks.errors import BlockError
from app.blocks.expressions import ExpressionError, compile_expression
from app.blocks.transforms import DerivedColumn


def schema() -> DataSchema:
    return DataSchema(
        columns=(
            Column(name="n", dtype="integer", nullable=True),
            Column(name="label", dtype="string"),
            Column(name="active", dtype="boolean"),
        )
    )


def test_arithmetic_compiles_and_infers_type():
    compiled = compile_expression('col("n") * 2 + 1', schema())

    assert compiled.dtype == "integer"
    assert compiled.nullable

    frame = pl.DataFrame({"n": [2, None]}, schema={"n": pl.Int64})
    result = frame.select(compiled.expression.alias("result"))
    assert result["result"].to_list() == [5, None]


def test_comparison_and_boolean_logic_compile():
    compiled = compile_expression(
        'col("n") >= 2 and col("n") < 5',
        schema(),
    )

    assert compiled.dtype == "boolean"
    assert compiled.nullable

    frame = pl.DataFrame({"n": [1, 3, 6, None]}, schema={"n": pl.Int64})
    result = frame.select(compiled.expression.alias("result"))
    assert result["result"].to_list() == [False, True, False, None]


def test_string_and_date_functions_compile():
    string_expression = compile_expression('upper(trim(col("label")))', schema())
    assert string_expression.dtype == "string"

    string_frame = pl.DataFrame({"label": ["  kiln  "]})
    assert (
        string_frame.select(string_expression.expression.alias("result"))["result"][0]
        == "KILN"
    )

    date_expression = compile_expression('year(col("label"))', schema())
    assert date_expression.dtype == "integer"

    date_frame = pl.DataFrame({"label": ["2026-03-14"]})
    assert (
        date_frame.select(date_expression.expression.alias("result"))["result"][0]
        == 2026
    )


@pytest.mark.parametrize(
    "source",
    [
        'unknown("x")',
        '__import__("os")',
        'col("n").__class__',
        'col("n")[0]',
        'col("n") + "text"',
    ],
)
def test_unsafe_or_mistyped_expressions_are_rejected(source: str):
    with pytest.raises(ExpressionError) as error:
        compile_expression(source, schema())

    assert error.value.position >= 1


def test_error_position_points_to_unknown_function():
    with pytest.raises(ExpressionError) as error:
        compile_expression("1 + unknown(2)", schema())

    assert error.value.position == 5


def test_derived_column_appends_column_and_preserves_input(tmp_path: Path):
    source = Table(
        data_schema=schema(),
        rows=(
            {"n": 2, "label": "a", "active": True},
            {"n": None, "label": "b", "active": False},
        ),
    )
    block = DerivedColumn()
    outputs = block.run(
        {"name": "calculated", "expression": 'coalesce(col("n"), 0) * 2'},
        {"table": (source,)},
        BlockContext("expression-test", "derived", workspace_root=tmp_path),
    )

    result = outputs["table"][0]
    assert isinstance(result, Table)
    assert [column.name for column in result.data_schema.columns] == [
        "n",
        "label",
        "active",
        "calculated",
    ]
    assert result.data_schema.columns[-1].dtype == "integer"
    assert not result.data_schema.columns[-1].nullable
    assert [row["calculated"] for row in result.rows] == [4, 0]
    assert source == Table(
        data_schema=schema(),
        rows=(
            {"n": 2, "label": "a", "active": True},
            {"n": None, "label": "b", "active": False},
        ),
    )


def test_derived_column_rejects_bad_expression_before_execution():
    source = Table(
        data_schema=schema(),
        rows=({"n": 2, "label": "a", "active": True},),
    )

    with pytest.raises(BlockError) as error:
        DerivedColumn().validate(
            {"name": "calculated", "expression": 'col("n") + "text"'},
            {"table": (source,)},
        )

    assert error.value.failure.code == "invalid_expression"
    assert error.value.failure.field == "expression"
    assert error.value.failure.position == 1
