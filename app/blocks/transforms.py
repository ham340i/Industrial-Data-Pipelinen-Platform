# AI contribution: 50% or more AI-generated
"""Deterministic, structured Polars row and column transforms.

Join and Aggregate live in ``app.blocks.relational``.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from typing import Any, Literal, cast

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
    PreviewLimits,
    Table,
)
from app.blocks.errors import BlockError
from app.blocks.frames import Frame, FrameValues
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
    require_schema_columns(table.data_schema, names)


def require_schema_columns(schema: DataSchema, names: list[str]) -> None:
    if set(names) - {column.name for column in schema.columns}:
        raise BlockError("missing_column", "A configured column is unavailable.")


def input_frame(inputs: FrameValues) -> Frame:
    frame = inputs["table"][0]
    assert isinstance(frame, Frame)
    return frame


def run_on_table(table: Table, transform: Callable[[Frame], Frame]) -> PortValues:
    """Run a frame transform for the Table path, with the Table path's checks."""
    result = transform(Frame(to_frame(table), table.data_schema))
    return {"table": (from_frame(result.data, result.data_schema),)}


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
        supports_preview=True,
        preview_reason=None,
    )

    def _preview(
        self,
        config: SelectConfig,
        inputs: PortValues,
        context: BlockContext,
        limits: PreviewLimits,
    ) -> PortValues:
        context.check_cancelled()
        table = input_table(inputs)
        require_columns(table, config.columns)
        columns = {column.name: column for column in table.data_schema.columns}
        count = min(limits.max_rows, limits.max_cells // len(config.columns))
        if count < 1:
            raise BlockError(
                "preview_limit", "The cell limit cannot hold one row of this schema."
            )
        rows = []
        for row in table.rows[:count]:
            context.check_cancelled()
            rows.append({name: row[name] for name in config.columns})
        return {
            "table": (
                Table(
                    data_schema=DataSchema(
                        columns=tuple(columns[name] for name in config.columns)
                    ),
                    rows=tuple(rows),
                ),
            )
        }

    frame_native = True

    @staticmethod
    def _apply(config: SelectConfig, frame: Frame) -> Frame:
        require_schema_columns(frame.data_schema, config.columns)
        columns = {column.name: column for column in frame.data_schema.columns}
        schema = DataSchema(columns=tuple(columns[name] for name in config.columns))
        return Frame(frame.data.select(config.columns), schema)

    def _execute(
        self, config: SelectConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        return run_on_table(input_table(inputs), lambda f: self._apply(config, f))

    def _execute_frames(
        self, config: SelectConfig, inputs: FrameValues, context: BlockContext
    ) -> FrameValues:
        return {"table": (self._apply(config, input_frame(inputs)),)}


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

    frame_native = True

    @staticmethod
    def _apply(config: RenameConfig, frame: Frame) -> Frame:
        require_schema_columns(frame.data_schema, config.columns)
        mapping = dict(zip(config.columns, config.names, strict=True))
        names = [mapping.get(c.name, c.name) for c in frame.data_schema.columns]
        if len(set(names)) != len(names):
            raise BlockError(
                "duplicate_column",
                "Renaming would create duplicate columns.",
                field="names",
            )
        schema = DataSchema(
            columns=tuple(
                Column(name=new, dtype=c.dtype, nullable=c.nullable)
                for new, c in zip(names, frame.data_schema.columns, strict=True)
            )
        )
        return Frame(frame.data.rename(mapping), schema)

    def _execute(
        self, config: RenameConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        return run_on_table(input_table(inputs), lambda f: self._apply(config, f))

    def _execute_frames(
        self, config: RenameConfig, inputs: FrameValues, context: BlockContext
    ) -> FrameValues:
        return {"table": (self._apply(config, input_frame(inputs)),)}


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


_FILTER_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
}


class Filter(Block[FilterConfig]):
    config_model = FilterConfig
    descriptor = BlockDescriptor(
        **descriptor_values("transform.filter", "Filter", "transform"),
        inputs=(TABLE_PORT,),
        outputs=(TABLE_PORT,),
    )

    @staticmethod
    def _literal(column: Column, config: FilterConfig) -> object:
        """Parse ``value_text`` as a literal the column's type can compare."""
        value = (
            config.value_text
            if column.dtype == "string"
            else json.loads(config.value_text)
        )
        if type(value) not in _FILTER_TYPES[column.dtype] or (
            isinstance(value, float) and not math.isfinite(value)
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
        return value

    @classmethod
    def _predicate(cls, column: Column, config: FilterConfig) -> pl.Expr:
        expr = pl.col(config.column)
        if config.operator == "is_null":
            return expr.is_null()
        if config.operator == "is_not_null":
            return expr.is_not_null()
        try:
            value = cls._literal(column, config)
            operations = {
                "eq": expr.eq,
                "ne": expr.ne,
                "lt": expr.lt,
                "le": expr.le,
                "gt": expr.gt,
                "ge": expr.ge,
            }
            return operations[config.operator](
                pl.lit(value, dtype=POLARS_TYPES[column.dtype])
            )
        except Exception:
            raise BlockError(
                "invalid_filter",
                "Filter value/operator must match the column type.",
                field="value_text",
            ) from None

    frame_native = True

    @classmethod
    def _apply(cls, config: FilterConfig, frame: Frame) -> Frame:
        schema = frame.data_schema
        require_schema_columns(schema, [config.column])
        column = next(c for c in schema.columns if c.name == config.column)
        predicate = cls._predicate(column, config)
        return Frame(frame.data.filter(predicate.fill_null(False)), schema)

    def _execute(
        self, config: FilterConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        return run_on_table(input_table(inputs), lambda f: self._apply(config, f))

    def _execute_frames(
        self, config: FilterConfig, inputs: FrameValues, context: BlockContext
    ) -> FrameValues:
        return {"table": (self._apply(config, input_frame(inputs)),)}


class CastConfig(BlockConfig):
    column: NonBlank
    dtype: Literal["string", "integer", "number", "boolean"]
    on_error: Literal["error", "null"] = "error"


class Cast(Block[CastConfig]):
    config_model = CastConfig
    descriptor = BlockDescriptor(
        **descriptor_values("transform.cast", "Cast", "transform"),
        inputs=(TABLE_PORT,),
        outputs=(TABLE_PORT,),
    )

    def _execute(
        self,
        config: CastConfig,
        inputs: PortValues,
        context: BlockContext,
    ) -> PortValues:
        table = input_table(inputs)
        require_columns(table, [config.column])

        frame = cast_column(
            to_frame(table),
            config.column,
            config.dtype,
            config.on_error,
        )

        schema = DataSchema(
            columns=tuple(
                Column(
                    name=column.name,
                    dtype=config.dtype,
                    nullable=column.nullable or config.on_error == "null",
                )
                if column.name == config.column
                else column
                for column in table.data_schema.columns
            )
        )

        return {"table": (from_frame(frame, schema),)}


class SortColumn(BlockConfig):
    column: NonBlank
    descending: bool = False
    nulls_last: bool = True


class SortConfig(BlockConfig):
    columns: list[SortColumn] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_columns(self) -> SortConfig:
        checked_names([column.column for column in self.columns])
        return self


class Sort(Block[SortConfig]):
    config_model = SortConfig
    descriptor = BlockDescriptor(
        **descriptor_values("transform.sort", "Sort", "transform"),
        inputs=(TABLE_PORT,),
        outputs=(TABLE_PORT,),
    )

    def _execute(
        self,
        config: SortConfig,
        inputs: PortValues,
        context: BlockContext,
    ) -> PortValues:
        table = input_table(inputs)
        require_columns(
            table,
            [column.column for column in config.columns],
        )

        rows = list(table.rows)

        # Python's sort is stable. Applying each configured key from
        # right-to-left gives deterministic multi-column sorting while
        # allowing null order to be independent of sort direction.
        for sort_column in reversed(config.columns):
            name = sort_column.column
            nulls_last = sort_column.nulls_last
            descending = sort_column.descending

            non_null_rows = [row for row in rows if row[name] is not None]
            null_rows = [row for row in rows if row[name] is None]

            non_null_rows.sort(
                key=lambda row: cast(Any, row[name]),
                reverse=descending,
            )

            rows = (
                non_null_rows + null_rows if nulls_last else null_rows + non_null_rows
            )

        return {
            "table": (
                Table(
                    data_schema=table.data_schema,
                    rows=tuple(rows),
                ),
            )
        }
