"""Deterministic, structured Polars column operations (#18)."""

from __future__ import annotations

import json
import math
from typing import Literal

import polars as pl
from pydantic import Field, field_validator, model_validator

from app.blocks.base import Block
from app.blocks.context import BlockContext
from app.blocks.contracts import (
    BlockConfig,
    BlockDescriptor,
    Column,
    DataSchema,
    NonBlank,
    PortValues,
    Table,
)
from app.blocks.errors import BlockError
from app.blocks.tabular import (
    POLARS_TYPES,
    TABLE_PORT,
    cast_column,
    checked_names,
    descriptor_values,
    from_frame,
    to_frame,
)


def input_table(inputs: PortValues) -> Table:
    table = inputs["table"][0]
    assert isinstance(table, Table)
    return table


def require_columns(table: Table, names: list[str]) -> None:
    if set(names) - {column.name for column in table.data_schema.columns}:
        raise BlockError("missing_column", "A configured column is unavailable.")


class SelectConfig(BlockConfig):
    columns: list[NonBlank] = Field(min_length=1, max_length=1000)

    @field_validator("columns")
    @classmethod
    def unique_columns(cls, value: list[str]) -> list[str]:
        return checked_names(value)


class SelectColumns(Block[SelectConfig]):
    config_model = SelectConfig
    descriptor = BlockDescriptor(
        **descriptor_values("transform.select", "Select Columns", "transform"),
        inputs=(TABLE_PORT,),
        outputs=(TABLE_PORT,),
    )

    def _execute(
        self, config: SelectConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        table = input_table(inputs)
        require_columns(table, config.columns)
        columns = {column.name: column for column in table.data_schema.columns}
        schema = DataSchema(columns=tuple(columns[name] for name in config.columns))
        return {"table": (from_frame(to_frame(table).select(config.columns), schema),)}


class RenameConfig(BlockConfig):
    columns: list[NonBlank] = Field(min_length=1, max_length=1000)
    names: list[NonBlank] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def matching_names(self) -> RenameConfig:
        checked_names(self.columns)
        checked_names(self.names)
        if len(self.columns) != len(self.names):
            raise ValueError("Rename lists must have matching lengths")
        return self


class RenameColumns(Block[RenameConfig]):
    config_model = RenameConfig
    descriptor = BlockDescriptor(
        **descriptor_values("transform.rename", "Rename Columns", "transform"),
        inputs=(TABLE_PORT,),
        outputs=(TABLE_PORT,),
    )

    def _execute(
        self, config: RenameConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        table = input_table(inputs)
        require_columns(table, config.columns)
        mapping = dict(zip(config.columns, config.names, strict=True))
        names = [mapping.get(c.name, c.name) for c in table.data_schema.columns]
        if len(set(names)) != len(names):
            raise BlockError(
                "duplicate_column",
                "Renaming would create duplicate columns.",
                field="names",
            )
        schema = DataSchema(
            columns=tuple(
                Column(
                    name=mapping.get(c.name, c.name),
                    dtype=c.dtype,
                    nullable=c.nullable,
                )
                for c in table.data_schema.columns
            )
        )
        return {"table": (from_frame(to_frame(table).rename(mapping), schema),)}


class FilterConfig(BlockConfig):
    column: NonBlank
    operator: Literal["eq", "ne", "lt", "le", "gt", "ge", "is_null", "is_not_null"] = (
        "eq"
    )
    value_text: str = Field(
        default="",
        max_length=10000,
        description=(
            "Literal string, or JSON scalar text matching the column type. "
            "Ignored for null operators."
        ),
    )


class Filter(Block[FilterConfig]):
    config_model = FilterConfig
    descriptor = BlockDescriptor(
        **descriptor_values("transform.filter", "Filter", "transform"),
        inputs=(TABLE_PORT,),
        outputs=(TABLE_PORT,),
    )

    def _execute(
        self, config: FilterConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        table = input_table(inputs)
        require_columns(table, [config.column])
        column = next(c for c in table.data_schema.columns if c.name == config.column)
        expr = pl.col(config.column)

        if config.operator == "is_null":
            predicate = expr.is_null()
        elif config.operator == "is_not_null":
            predicate = expr.is_not_null()
        else:
            try:
                value = (
                    config.value_text
                    if column.dtype == "string"
                    else json.loads(config.value_text)
                )
                expected = {
                    "string": (str,),
                    "integer": (int,),
                    "number": (int, float),
                    "boolean": (bool,),
                }[column.dtype]

                if (
                    type(value) not in expected
                    or isinstance(value, float)
                    and not math.isfinite(value)
                ):
                    raise ValueError("Type mismatch")

                if column.dtype == "integer" and (
                    not isinstance(value, int) or not -(2**63) <= value < 2**63
                ):
                    raise ValueError("Integer out of range")

                if column.dtype == "boolean" and config.operator not in ("eq", "ne"):
                    raise ValueError("Booleans support equality only")

                if (
                    column.dtype == "number"
                    and type(value) is int
                    and int(float(value)) != value
                ):
                    raise ValueError("Filter integer loses Float64 precision")

                operations = {
                    "eq": expr.eq,
                    "ne": expr.ne,
                    "lt": expr.lt,
                    "le": expr.le,
                    "gt": expr.gt,
                    "ge": expr.ge,
                }

                predicate = operations[config.operator](
                    pl.lit(value, dtype=POLARS_TYPES[column.dtype])
                )
            except Exception:
                raise BlockError(
                    "invalid_filter",
                    "Filter value/operator must match the column type.",
                    field="value_text",
                ) from None

        frame = to_frame(table).filter(predicate.fill_null(False))
        return {"table": (from_frame(frame, table.data_schema),)}


class CastConfig(BlockConfig):
    column: NonBlank
    dtype: Literal["string", "integer", "number", "boolean"]
    on_error: Literal["error", "null"] = "error"


class JoinConfig(BlockConfig):
    left_on: list[NonBlank] = Field(min_length=1, max_length=100)
    right_on: list[NonBlank] = Field(min_length=1, max_length=100)
    how: Literal["inner", "left", "outer"] = "inner"
    cardinality: Literal[
        "many_to_many",
        "one_to_one",
        "one_to_many",
        "many_to_one",
    ] = "many_to_many"

    @model_validator(mode="after")
    def validate_keys(self) -> JoinConfig:
        checked_names(self.left_on)
        checked_names(self.right_on)
        if len(self.left_on) != len(self.right_on):
            raise ValueError("Join key lists must have matching lengths")
        return self


class AggregateOperation(BlockConfig):
    column: NonBlank
    function: Literal["count", "sum", "min", "max", "mean"]
    output_name: NonBlank


class AggregateConfig(BlockConfig):
    group_by: list[NonBlank] = Field(default_factory=list, max_length=100)
    operations: list[AggregateOperation] = Field(
        min_length=1,
        max_length=100,
    )

    @field_validator("group_by")
    @classmethod
    def unique_group_columns(cls, value: list[str]) -> list[str]:
        return checked_names(value)

    @model_validator(mode="after")
    def unique_output_names(self) -> AggregateConfig:
        names = [operation.output_name for operation in self.operations]
        checked_names(names)
        return self


class SortColumn(BlockConfig):
    column: NonBlank
    descending: bool = False
    nulls_last: bool = True


class SortConfig(BlockConfig):
    columns: list[SortColumn] = Field(min_length=1, max_length=100)


class Cast(Block[CastConfig]):
    config_model = CastConfig
    descriptor = BlockDescriptor(
        **descriptor_values("transform.cast", "Cast", "transform"),
        inputs=(TABLE_PORT,),
        outputs=(TABLE_PORT,),
    )

    def _execute(
        self, config: CastConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        table = input_table(inputs)
        require_columns(table, [config.column])
        frame = cast_column(
            to_frame(table), config.column, config.dtype, config.on_error
        )
        schema = DataSchema(
            columns=tuple(
                Column(
                    name=c.name,
                    dtype=config.dtype,
                    nullable=c.nullable or config.on_error == "null",
                )
                if c.name == config.column
                else c
                for c in table.data_schema.columns
            )
        )
        return {"table": (from_frame(frame, schema),)}
