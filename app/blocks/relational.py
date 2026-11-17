# AI contribution: below 50% AI-generated
"""Deterministic Join and Aggregate blocks that combine or reduce tables (#24)."""

from __future__ import annotations

from collections.abc import Mapping
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
    Port,
    PortValues,
    Table,
)
from app.blocks.errors import BlockError
from app.blocks.tabular import (
    TABLE_PORT,
    checked_names,
    descriptor_values,
    from_frame,
    to_frame,
)

from app.blocks.transforms import input_table, require_columns

INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1


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

    @staticmethod
    def _check_keys(
        config: JoinConfig,
        left_columns: dict[str, Column],
        right_columns: dict[str, Column],
    ) -> None:
        for left_name, right_name in zip(config.left_on, config.right_on, strict=True):
            if left_columns[left_name].dtype != right_columns[right_name].dtype:
                raise BlockError(
                    "join_key_type_mismatch",
                    "Join key types must match.",
                    field=left_name,
                )
        duplicate_names = (set(right_columns) - set(config.right_on)) & set(
            left_columns
        )
        if duplicate_names:
            raise BlockError(
                "duplicate_column",
                "Join would create duplicate output columns.",
                field=sorted(duplicate_names)[0],
            )

    @classmethod
    def _check_cardinality(cls, config: JoinConfig, left: Table, right: Table) -> None:
        left_duplicates = cls._duplicate_keys(left, config.left_on)
        right_duplicates = cls._duplicate_keys(right, config.right_on)
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

    @staticmethod
    def _coalesce_keys(
        frame: pl.DataFrame, config: JoinConfig, left_columns: dict[str, Column]
    ) -> pl.DataFrame:
        # A full/outer join can produce a right-only row. In that case,
        # Polars leaves the retained left key null and stores the right key
        # separately. Coalesce each key pair so right-only keys are preserved.
        expressions: list[pl.Expr] = []
        for left_name, right_name in zip(config.left_on, config.right_on, strict=True):
            right_joined_name = (
                f"{right_name}__right" if right_name in left_columns else right_name
            )
            if right_joined_name not in frame.columns:
                raise BlockError(
                    "join_failed",
                    "The joined key columns could not be constructed.",
                    field=right_name,
                )
            expressions.append(
                pl.coalesce([pl.col(left_name), pl.col(right_joined_name)]).alias(
                    left_name
                )
            )
        try:
            return frame.with_columns(expressions)
        except Exception:
            raise BlockError(
                "join_failed",
                "The joined key columns could not be coalesced.",
            ) from None

    @staticmethod
    def _output_schema(
        config: JoinConfig,
        left: Table,
        right_columns: dict[str, Column],
        right_value_names: list[str],
    ) -> DataSchema:
        output_columns = [
            Column(
                name=column.name,
                dtype=column.dtype,
                nullable=column.nullable or config.how == "outer",
            )
            for column in left.data_schema.columns
        ]
        for name in right_value_names:
            column = right_columns[name]
            output_columns.append(
                Column(
                    name=name,
                    dtype=column.dtype,
                    nullable=column.nullable or config.how in ("left", "outer"),
                )
            )
        return DataSchema(columns=tuple(output_columns))

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
        self._check_keys(config, left_columns, right_columns)
        self._check_cardinality(config, left, right)

        try:
            frame = to_frame(left).join(
                to_frame(right),
                left_on=config.left_on,
                right_on=config.right_on,
                how="full" if config.how == "outer" else config.how,
                suffix="__right",
                maintain_order="left",
            )
        except Exception:
            raise BlockError(
                "join_failed",
                "The configured tables could not be joined.",
            ) from None
        if config.how == "outer":
            frame = self._coalesce_keys(frame, config, left_columns)

        right_key_names = set(config.right_on)
        right_value_names = [
            name for name in right_columns if name not in right_key_names
        ]
        try:
            frame = frame.select([*left_columns, *right_value_names])
        except Exception:
            raise BlockError(
                "join_failed",
                "The join output columns could not be constructed.",
            ) from None

        schema = self._output_schema(config, left, right_columns, right_value_names)
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

    @staticmethod
    def _expression(
        table: Table,
        config: AggregateConfig,
        operation: AggregateOperation,
        source: Column,
    ) -> pl.Expr:
        function = operation.function
        if function in ("sum", "mean") and source.dtype not in ("integer", "number"):
            raise BlockError(
                "invalid_aggregate",
                f"{function.capitalize()} requires an integer or number column.",
                field=operation.column,
            )
        if function == "sum" and source.dtype == "integer":
            check_integer_sum_overflow(
                table, operation.column, config.group_by, operation.output_name
            )
        column = pl.col(operation.column)
        aggregations = {
            "count": column.count,
            "sum": column.sum,
            "min": column.min,
            "max": column.max,
            "mean": column.mean,
        }
        return aggregations[function]().alias(operation.output_name)

    def _output_schema(
        self, config: AggregateConfig, columns: dict[str, Column]
    ) -> DataSchema:
        output_columns = [columns[name] for name in config.group_by]
        for operation in config.operations:
            source = columns[operation.column]
            output_columns.append(
                Column(
                    name=operation.output_name,
                    dtype=self._operation_dtype(source, operation.function),
                    nullable=self._operation_nullable(
                        source, operation.function, bool(config.group_by)
                    ),
                )
            )
        return DataSchema(columns=tuple(output_columns))

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

        output_names = [operation.output_name for operation in config.operations]
        if set(config.group_by).intersection(output_names):
            raise BlockError(
                "duplicate_column",
                "Aggregate output names cannot match group columns.",
                field="operations",
            )

        expressions = [
            self._expression(table, config, operation, columns[operation.column])
            for operation in config.operations
        ]
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

        schema = self._output_schema(config, columns)
        return {"table": (from_frame(result, schema),)}
