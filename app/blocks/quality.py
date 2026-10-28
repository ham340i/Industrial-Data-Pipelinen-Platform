"""Explicit null policies and required/optional data-quality gates (#25)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.blocks.base import Block
from app.blocks.context import BlockContext, BlockEvent
from app.blocks.contracts import (
    BlockConfig,
    BlockDescriptor,
    Column,
    DataSchema,
    NonBlank,
    PortValues,
    Scalar,
    Table,
)
from app.blocks.errors import BlockError, QualityDiagnostic
from app.blocks.tabular import TABLE_PORT, checked_names, descriptor_values, to_frame
from app.blocks.transforms import input_table, require_columns


def descriptor(
    block_id: str, name: str, kind: Literal["transform", "quality"] = "quality"
) -> BlockDescriptor:
    return BlockDescriptor(
        **descriptor_values(block_id, name, kind),
        inputs=(TABLE_PORT,),
        outputs=(TABLE_PORT,),
        preview_reason="Whole-input quality checks run without returning preview rows.",
    )


def report(
    block: BlockDescriptor,
    context: BlockContext,
    diagnostics: tuple[QualityDiagnostic, ...],
    required: bool = True,
) -> None:
    context.check_cancelled()
    context.emit(
        BlockEvent(
            run_id=context.run_id,
            node_id=context.node_id,
            block_id=block.block_id,
            version=block.version,
            event="quality",
            diagnostics=diagnostics,
        )
    )
    if required and any(item.status == "fail" for item in diagnostics):
        raise BlockError(
            "quality_failed",
            "Required data-quality validation failed.",
            diagnostics=diagnostics,
        )


def status(valid: bool, required: bool) -> Literal["pass", "fail", "warning"]:
    if valid:
        return "pass"
    return "fail" if required else "warning"


class ColumnSelection(BlockConfig):
    columns: list[NonBlank] = Field(default_factory=list, max_length=1000)

    @field_validator("columns")
    @classmethod
    def unique_columns(cls, value: list[str]) -> list[str]:
        return checked_names(value)


def selected(table: Table, config: ColumnSelection) -> list[str]:
    names = config.columns or [column.name for column in table.data_schema.columns]
    require_columns(table, names)
    return names


def null_rows(table: Table, names: list[str]) -> tuple[int, tuple[int, ...]]:
    """Count all matching rows while retaining only the first 20 indices."""
    count = 0
    indices: list[int] = []
    for index, row in enumerate(table.rows):
        if any(row[name] is None for name in names):
            count += 1
            if len(indices) < 20:
                indices.append(index)
    return count, tuple(indices)


class NullHandlingConfig(ColumnSelection):
    policy: Literal["fill", "drop"]
    fill_values: dict[NonBlank, Scalar] = Field(default_factory=dict)

    @model_validator(mode="after")
    def explicit_policy(self) -> NullHandlingConfig:
        if self.policy == "drop" and self.fill_values:
            raise ValueError("Drop does not accept fill values")
        if self.policy == "fill" and not self.fill_values:
            raise ValueError("Fill requires explicit values")
        if any(value is None for value in self.fill_values.values()):
            raise ValueError("A fill value cannot be null")
        return self


def matches_type(value: Scalar, column: Column) -> bool:
    expected = {
        "string": (str,),
        "integer": (int,),
        "number": (int, float),
        "boolean": (bool,),
    }[column.dtype]
    return type(value) in expected


class NullHandling(Block[NullHandlingConfig]):
    config_model = NullHandlingConfig
    descriptor = descriptor("transform.null_handling", "Null Handling", "transform")

    def _execute(
        self, config: NullHandlingConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        table = input_table(inputs)
        names = selected(table, config)
        columns = {column.name: column for column in table.data_schema.columns}
        if config.policy == "fill":
            if set(config.fill_values) != set(names):
                raise BlockError(
                    "invalid_fill", "Supply one fill for each selected column."
                )
            if any(
                not matches_type(value, columns[name])
                for name, value in config.fill_values.items()
            ):
                raise BlockError(
                    "invalid_fill", "Fill values must match declared types."
                )
        affected, row_indices = null_rows(table, names)
        if config.policy == "drop":
            rows = tuple(
                dict(row)
                for row in table.rows
                if all(row[name] is not None for name in names)
            )
        else:
            rows = tuple(
                {
                    name: config.fill_values[name]
                    if name in config.fill_values and value is None
                    else value
                    for name, value in row.items()
                }
                for row in table.rows
            )
        schema = DataSchema(
            columns=tuple(
                column.model_copy(update={"nullable": False})
                if column.name in names
                else column
                for column in table.data_schema.columns
            ),
            allow_extra_columns=table.data_schema.allow_extra_columns,
        )
        output = Table(data_schema=schema, rows=rows)
        # Match the actual Int64/Float64 platform without silently losing precision.
        to_frame(output)
        report(
            self.descriptor,
            context,
            (
                QualityDiagnostic(
                    code=f"null_{config.policy}",
                    status="pass",
                    observed=affected,
                    row_indices=row_indices,
                ),
            ),
        )
        return {"table": (output,)}


class SchemaValidationConfig(BlockConfig):
    columns: list[Column] = Field(min_length=1, max_length=1000)
    allow_extra_columns: bool = False
    required: bool = True

    @model_validator(mode="after")
    def unique_schema(self) -> SchemaValidationConfig:
        checked_names([column.name for column in self.columns])
        return self


class SchemaValidation(Block[SchemaValidationConfig]):
    """One implementation, displayed as Validate Schema in discovery."""

    config_model = SchemaValidationConfig
    descriptor = descriptor("quality.schema_validation", "Validate Schema")

    def _execute(
        self, config: SchemaValidationConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        table = input_table(inputs)
        actual = {column.name: column for column in table.data_schema.columns}
        expected = {column.name: column for column in config.columns}
        diagnostics: list[QualityDiagnostic] = []
        bad = status(False, config.required)
        for name, column in expected.items():
            if name not in actual:
                diagnostics.append(
                    QualityDiagnostic(
                        code="missing_column",
                        status=bad,
                        column=name,
                        expected_type=column.dtype,
                    )
                )
                continue
            if actual[name].dtype != column.dtype:
                diagnostics.append(
                    QualityDiagnostic(
                        code="type_mismatch",
                        status=bad,
                        column=name,
                        expected_type=column.dtype,
                        actual_type=actual[name].dtype,
                    )
                )
            if actual[name].nullable != column.nullable:
                diagnostics.append(
                    QualityDiagnostic(
                        code="nullability_mismatch",
                        status=bad,
                        column=name,
                        expected_nullable=column.nullable,
                        actual_nullable=actual[name].nullable,
                    )
                )
            if not column.nullable:
                count, row_indices = null_rows(table, [name])
                if count:
                    diagnostics.append(
                        QualityDiagnostic(
                            code="unexpected_null",
                            status=bad,
                            column=name,
                            observed=count,
                            maximum=0,
                            row_indices=row_indices,
                        )
                    )
        if not config.allow_extra_columns:
            for name in sorted(actual.keys() - expected.keys()):
                diagnostics.append(
                    QualityDiagnostic(
                        code="extra_column",
                        status=bad,
                        column=name,
                        actual_type=actual[name].dtype,
                    )
                )
        if not diagnostics:
            diagnostics.append(QualityDiagnostic(code="schema_valid", status="pass"))
        report(self.descriptor, context, tuple(diagnostics), config.required)
        return {"table": (table,)}


class NullCheckConfig(ColumnSelection):
    max_nulls: int = Field(default=0, ge=0)
    required: bool = True


class NullCheck(Block[NullCheckConfig]):
    config_model = NullCheckConfig
    descriptor = descriptor("quality.null_check", "Null Check")

    def _execute(
        self, config: NullCheckConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        table = input_table(inputs)
        diagnostics = []
        for name in selected(table, config):
            count, row_indices = null_rows(table, [name])
            diagnostics.append(
                QualityDiagnostic(
                    code="null_count",
                    column=name,
                    observed=count,
                    maximum=config.max_nulls,
                    row_indices=row_indices,
                    status=status(count <= config.max_nulls, config.required),
                )
            )
        if not diagnostics:
            diagnostics.append(QualityDiagnostic(code="null_count", status="pass"))
        report(self.descriptor, context, tuple(diagnostics), config.required)
        return {"table": (table,)}


class RowCountConfig(BlockConfig):
    min_rows: int = Field(default=0, ge=0)
    max_rows: int | None = Field(default=None, ge=0)
    required: bool = True

    @model_validator(mode="after")
    def ordered_bounds(self) -> RowCountConfig:
        if self.max_rows is not None and self.max_rows < self.min_rows:
            raise ValueError("Maximum must be at least minimum")
        return self


class RowCount(Block[RowCountConfig]):
    config_model = RowCountConfig
    descriptor = descriptor("quality.row_count", "Row Count")

    def _execute(
        self, config: RowCountConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        table = input_table(inputs)
        count = len(table.rows)
        valid = count >= config.min_rows and (
            config.max_rows is None or count <= config.max_rows
        )
        report(
            self.descriptor,
            context,
            (
                QualityDiagnostic(
                    code="row_count",
                    status=status(valid, config.required),
                    observed=count,
                    minimum=config.min_rows,
                    maximum=config.max_rows,
                ),
            ),
            config.required,
        )
        return {"table": (table,)}
