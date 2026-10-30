"""Deterministic, structured Polars transform operations."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
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
    Port,
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

INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1


def input_table(inputs: PortValues) -> Table:
    table = inputs["table"][0]
    assert isinstance(table, Table)
    return table


def require_columns(table: Table, names: list[str]) -> None:
    if set(names) - {column.name for column in table.data_schema.columns}:
        raise BlockError("missing_column", "A configured column is unavailable.")


def check_integer_sum_overflow(
    table: Table,
    column: str,
    group_by: list[str],
    output_name: str,
) -> None:
    totals: dict[tuple[object, ...], int] = {}

    for row in table.rows:
        value = row[column]

        if value is None:
            continue

        if not isinstance(value, int):
            raise BlockError(
                "aggregate_failed",
                "Integer sum received a non-integer value.",
                field=column,
            )

        key = tuple(row[name] for name in group_by) if group_by else ()
        totals[key] = totals.get(key, 0) + value

    if any(total < INT64_MIN or total > INT64_MAX for total in totals.values()):
        raise BlockError(
            "aggregate_overflow",
            "The integer aggregate result is outside the supported range.",
            field=output_name,
        )


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


class Join(Block[JoinConfig]):
    config_model = JoinConfig
    descriptor = BlockDescriptor(
        **descriptor_values("transform.join", "Join", "transform"),
        inputs=(
            Port(name="left", data_schema=TABLE_PORT.data_schema),
            Port(name="right", data_schema=TABLE_PORT.data_schema),
        ),
        outputs=(
            Port(
                name="table",
                data_schema=DataSchema(
                    columns=(),
                    allow_extra_columns=True,
                ),
            ),
        ),
    )

    @staticmethod
    def _key_tuple(
        row: Mapping[str, object],
        columns: list[str],
    ) -> tuple[object, ...]:
        return tuple(row[column] for column in columns)

    @classmethod
    def _duplicate_keys(
        cls,
        table: Table,
        columns: list[str],
    ) -> set[tuple[object, ...]]:
        counts: dict[tuple[object, ...], int] = {}

        for row in table.rows:
            key = cls._key_tuple(row, columns)

            if any(value is None for value in key):
                continue

            counts[key] = counts.get(key, 0) + 1

        return {key for key, count in counts.items() if count > 1}

    @staticmethod
    def _column_map(table: Table) -> dict[str, Column]:
        return {column.name: column for column in table.data_schema.columns}

    def _execute(
        self,
        config: JoinConfig,
        inputs: PortValues,
        context: BlockContext,
    ) -> PortValues:
        left = inputs["left"][0]
        right = inputs["right"][0]
        assert isinstance(left, Table)
        assert isinstance(right, Table)

        require_columns(left, config.left_on)
        require_columns(right, config.right_on)

        left_columns = self._column_map(left)
        right_columns = self._column_map(right)

        for left_name, right_name in zip(
            config.left_on,
            config.right_on,
            strict=True,
        ):
            if left_columns[left_name].dtype != right_columns[right_name].dtype:
                raise BlockError(
                    "join_key_type_mismatch",
                    "Join key types must match.",
                    field=left_name,
                )

        right_key_names = set(config.right_on)
        left_names = set(left_columns)
        duplicate_names = (set(right_columns) - right_key_names) & left_names

        if duplicate_names:
            raise BlockError(
                "duplicate_column",
                "Join would create duplicate output columns.",
                field=sorted(duplicate_names)[0],
            )

        left_duplicates = self._duplicate_keys(left, config.left_on)
        right_duplicates = self._duplicate_keys(right, config.right_on)

        if config.cardinality == "one_to_one" and (left_duplicates or right_duplicates):
            raise BlockError(
                "invalid_cardinality",
                "The join configuration requires unique keys on both inputs.",
            )

        if config.cardinality == "one_to_many" and left_duplicates:
            raise BlockError(
                "invalid_cardinality",
                "The left input contains duplicate join keys.",
            )

        if config.cardinality == "many_to_one" and right_duplicates:
            raise BlockError(
                "invalid_cardinality",
                "The right input contains duplicate join keys.",
            )

        join_how = "full" if config.how == "outer" else config.how

        try:
            frame = to_frame(left).join(
                to_frame(right),
                left_on=config.left_on,
                right_on=config.right_on,
                how=join_how,
                suffix="__right",
                maintain_order="left",
            )
        except Exception:
            raise BlockError(
                "join_failed",
                "The configured tables could not be joined.",
            ) from None

        # A full/outer join can produce a right-only row. In that case,
        # Polars leaves the retained left key null and stores the right key
        # separately. Coalesce each key pair so right-only keys are preserved.
        if config.how == "outer":
            coalesced_key_expressions: list[pl.Expr] = []

            for left_name, right_name in zip(
                config.left_on,
                config.right_on,
                strict=True,
            ):
                right_joined_name = (
                    f"{right_name}__right" if right_name in left_columns else right_name
                )

                if right_joined_name not in frame.columns:
                    raise BlockError(
                        "join_failed",
                        "The joined key columns could not be constructed.",
                        field=right_name,
                    )

                coalesced_key_expressions.append(
                    pl.coalesce(
                        [
                            pl.col(left_name),
                            pl.col(right_joined_name),
                        ]
                    ).alias(left_name)
                )

            try:
                frame = frame.with_columns(coalesced_key_expressions)
            except Exception:
                raise BlockError(
                    "join_failed",
                    "The joined key columns could not be coalesced.",
                ) from None

        output_names = list(left_columns)
        right_value_names = [
            name for name in right_columns if name not in right_key_names
        ]
        output_names.extend(right_value_names)

        try:
            frame = frame.select(output_names)
        except Exception:
            raise BlockError(
                "join_failed",
                "The join output columns could not be constructed.",
            ) from None

        output_columns: list[Column] = []

        for column in left.data_schema.columns:
            output_columns.append(
                Column(
                    name=column.name,
                    dtype=column.dtype,
                    nullable=column.nullable or config.how == "outer",
                )
            )

        for name in right_value_names:
            column = right_columns[name]
            output_columns.append(
                Column(
                    name=name,
                    dtype=column.dtype,
                    nullable=column.nullable or config.how in ("left", "outer"),
                )
            )

        schema = DataSchema(columns=tuple(output_columns))
        return {"table": (from_frame(frame, schema),)}


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


class Aggregate(Block[AggregateConfig]):
    config_model = AggregateConfig
    descriptor = BlockDescriptor(
        **descriptor_values("transform.aggregate", "Aggregate", "transform"),
        inputs=(TABLE_PORT,),
        outputs=(
            Port(
                name="table",
                data_schema=DataSchema(
                    columns=(),
                    allow_extra_columns=True,
                ),
            ),
        ),
    )

    @staticmethod
    def _column_map(table: Table) -> dict[str, Column]:
        return {column.name: column for column in table.data_schema.columns}

    @staticmethod
    def _operation_dtype(
        source: Column,
        function: str,
    ) -> Literal["string", "integer", "number", "boolean"]:
        if function == "count":
            return "integer"

        if function == "mean":
            return "number"

        return source.dtype

    @staticmethod
    def _operation_nullable(
        source: Column,
        function: str,
        has_group_by: bool,
    ) -> bool:
        if function == "count":
            return False

        return source.nullable or not has_group_by

    def _execute(
        self,
        config: AggregateConfig,
        inputs: PortValues,
        context: BlockContext,
    ) -> PortValues:
        table = input_table(inputs)
        columns = self._column_map(table)

        require_columns(table, config.group_by)
        require_columns(
            table,
            [operation.column for operation in config.operations],
        )

        group_names = set(config.group_by)
        output_names = [operation.output_name for operation in config.operations]

        if group_names.intersection(output_names):
            raise BlockError(
                "duplicate_column",
                "Aggregate output names cannot match group columns.",
                field="operations",
            )

        expressions: list[pl.Expr] = []

        for operation in config.operations:
            source = columns[operation.column]

            if operation.function == "count":
                expression = pl.col(operation.column).count()
            elif operation.function == "sum":
                if source.dtype not in ("integer", "number"):
                    raise BlockError(
                        "invalid_aggregate",
                        "Sum requires an integer or number column.",
                        field=operation.column,
                    )

                if source.dtype == "integer":
                    check_integer_sum_overflow(
                        table,
                        operation.column,
                        config.group_by,
                        operation.output_name,
                    )

                expression = pl.col(operation.column).sum()
            elif operation.function == "min":
                expression = pl.col(operation.column).min()
            elif operation.function == "max":
                expression = pl.col(operation.column).max()
            elif operation.function == "mean":
                if source.dtype not in ("integer", "number"):
                    raise BlockError(
                        "invalid_aggregate",
                        "Mean requires an integer or number column.",
                        field=operation.column,
                    )
                expression = pl.col(operation.column).mean()
            else:
                raise BlockError(
                    "invalid_aggregate",
                    "The aggregate operation is unsupported.",
                    field="operations",
                )

            expressions.append(expression.alias(operation.output_name))

        frame = to_frame(table)

        try:
            if config.group_by:
                result = frame.group_by(
                    config.group_by,
                    maintain_order=True,
                ).agg(expressions)
            else:
                result = frame.select(expressions)
        except Exception:
            raise BlockError(
                "aggregate_failed",
                "The configured aggregate operations could not be applied.",
            ) from None

        output_columns = [columns[name] for name in config.group_by]

        for operation in config.operations:
            source = columns[operation.column]
            output_columns.append(
                Column(
                    name=operation.output_name,
                    dtype=self._operation_dtype(
                        source,
                        operation.function,
                    ),
                    nullable=self._operation_nullable(
                        source,
                        operation.function,
                        bool(config.group_by),
                    ),
                )
            )

        schema = DataSchema(columns=tuple(output_columns))
        return {"table": (from_frame(result, schema),)}


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
