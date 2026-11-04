"""Bounded SDK/Polars adapter shared by the Iteration 2 file blocks."""

from typing import Any, Literal

import polars as pl

from app.blocks.contracts import Column, DataSchema, Port, Table
from app.blocks.errors import BlockError

TABLE_PORT = Port(
    name="table", data_schema=DataSchema(columns=(), allow_extra_columns=True)
)
DType = Literal["string", "integer", "number", "boolean"]
POLARS_TYPES: dict[DType, type[pl.DataType]] = {
    "string": pl.String,
    "integer": pl.Int64,
    "number": pl.Float64,
    "boolean": pl.Boolean,
}


def to_frame(table: Table) -> pl.DataFrame:
    try:
        for column in table.data_schema.columns:
            if column.dtype == "number":
                for row in table.rows:
                    value = row[column.name]
                    if type(value) is int and int(float(value)) != value:
                        raise ValueError("Integer loses precision in Float64")
        return pl.DataFrame(
            list(table.rows),
            schema={c.name: POLARS_TYPES[c.dtype] for c in table.data_schema.columns},
            strict=True,
        )
    except Exception:
        raise BlockError(
            "unsupported_value", "Values exceed the supported scalar type range."
        ) from None


def from_frame(frame: pl.DataFrame, schema: DataSchema | None = None) -> Table:
    if schema is None:
        columns = []
        for name, dtype in frame.schema.items():
            kind = next((k for k, v in POLARS_TYPES.items() if v == dtype), None)
            if kind is None:
                if dtype.is_integer():
                    kind = "integer"
                elif dtype.is_float():
                    kind = "number"
                elif dtype == pl.Null:
                    kind = "string"
                else:
                    raise BlockError(
                        "unsupported_type", "Only SDK scalar columns are supported."
                    )
            columns.append(
                Column(name=name, dtype=kind, nullable=frame[name].null_count() > 0)
            )
        schema = DataSchema(columns=tuple(columns))
    try:
        result = Table(data_schema=schema, rows=tuple(frame.to_dicts()))
        # The SDK integer domain is bounded by the processing engine's Int64.
        to_frame(result)
        return result
    except BlockError:
        raise
    except Exception:
        raise BlockError(
            "schema_mismatch", "Data does not match the declared scalar schema."
        ) from None


def cast_column(
    frame: pl.DataFrame, name: str, kind: DType, failure: str = "error"
) -> pl.DataFrame:
    original = frame[name]
    try:
        if kind == "boolean" and original.dtype == pl.String:
            converted = original.replace_strict(
                {"true": True, "false": False}, default=None, return_dtype=pl.Boolean
            )
        else:
            converted = original.cast(POLARS_TYPES[kind], strict=False)
        invalid = original.is_not_null() & converted.is_null()
        if kind == "boolean" and original.dtype.is_numeric():
            invalid = invalid | (~original.is_in([0, 1])).fill_null(False)
        if kind == "integer" and original.dtype.is_float():
            invalid = invalid | (original != converted.cast(original.dtype)).fill_null(
                False
            )
        if kind == "number":
            invalid = invalid | (~converted.is_finite()).fill_null(False)
        # Converting large integers to float must not silently lose precision.
        if kind == "number" and original.dtype.is_integer():
            bad: list[bool] = []
            for source, target in zip(original, converted, strict=True):
                bad.append(
                    source is not None and target is not None and int(target) != source
                )
            invalid = invalid | pl.Series(bad, dtype=pl.Boolean)
        if invalid.any():
            if failure == "error":
                raise BlockError(
                    "cast_failed", "A value cannot be cast without loss.", field=name
                )
            converted = converted.zip_with(~invalid, pl.Series([None] * len(frame)))
        return frame.with_columns(converted.alias(name))
    except BlockError:
        raise
    except Exception:
        raise BlockError(
            "cast_failed", "Column conversion is unsupported.", field=name
        ) from None


def checked_names(names: list[str]) -> list[str]:
    if any(not name.strip() for name in names) or len(set(names)) != len(names):
        raise ValueError("Column names must be nonblank and unique")
    return names


def descriptor_values(block_id: str, name: str, block_type: str) -> dict[str, Any]:
    return {
        "block_id": block_id,
        "version": "1.0.0",
        "name": name,
        "block_type": block_type,
        "category": block_type,
    }
