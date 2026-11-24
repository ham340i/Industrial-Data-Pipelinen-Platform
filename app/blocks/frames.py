# AI contribution: 50% or more AI-generated
"""Lossless SDK v1 scalar-schema adapters for eager Polars execution.

Frames are the runtime representation of tables. Frame-native blocks (#121)
receive and return them directly, so ``checked_frame`` enforces the same
rules ``Table`` validates row by row: exact column types, no nulls in
non-nullable columns and only finite numbers.
"""

from dataclasses import dataclass

import polars as pl

from app.blocks.contracts import (
    ControlSignal,
    DataSchema,
    PortValues,
    Table,
    schemas_compatible,
)
from app.blocks.errors import BlockError

_DTYPES = {
    "string": pl.String(),
    "integer": pl.Int64(),
    "number": pl.Float64(),
    "boolean": pl.Boolean(),
}


@dataclass(frozen=True)
class Frame:
    data: pl.DataFrame
    data_schema: DataSchema

    @classmethod
    def from_table(cls, table: Table) -> "Frame":
        try:
            checked = Table.model_validate(table.model_dump())
            # Polars cannot represent nonempty zero-column tables faithfully.
            if checked.rows and not checked.data_schema.columns:
                raise ValueError("Zero-column rows are unsupported")
            data = pl.DataFrame(
                list(checked.rows),
                schema={c.name: _DTYPES[c.dtype] for c in checked.data_schema.columns},
                strict=True,
            )
            if tuple(data.to_dicts()) != checked.rows:
                raise ValueError("Conversion would lose values")
            return cls(data, checked.data_schema)
        except Exception:
            raise BlockError(
                "invalid_frame", "Table cannot be represented by the runtime."
            ) from None

    def to_table(self) -> Table:
        try:
            expected = {c.name: _DTYPES[c.dtype] for c in self.data_schema.columns}
            if list(self.data.schema.items()) != list(expected.items()):
                raise ValueError("Frame schema changed")
            return Table(data_schema=self.data_schema, rows=tuple(self.data.to_dicts()))
        except Exception:
            raise BlockError(
                "invalid_frame", "Runtime frame violates its declared schema."
            ) from None


FrameValues = dict[str, tuple[Frame | ControlSignal, ...]]


def to_frames(values: PortValues) -> FrameValues:
    return {
        name: tuple(Frame.from_table(v) if isinstance(v, Table) else v for v in items)
        for name, items in values.items()
    }


def to_tables(values: FrameValues) -> PortValues:
    return {
        name: tuple(v.to_table() if isinstance(v, Frame) else v for v in items)
        for name, items in values.items()
    }


def _frame_violation(frame: Frame) -> str | None:
    """Return why ``frame`` breaks its declared schema, or None when it is valid."""
    data, columns = frame.data, frame.data_schema.columns
    expected = [(c.name, _DTYPES[c.dtype]) for c in columns]
    if list(data.schema.items()) != expected:
        return "Frame columns do not match the declared schema."
    if data.height and not data.width:
        return "Zero-column rows are unsupported."
    for column in columns:
        series = data[column.name]
        if not column.nullable and series.null_count():
            return "Null in a non-nullable column."
        if column.dtype == "number" and not series.is_finite().fill_null(True).all():
            return "Non-finite numbers are unsupported."
    return None


def checked_frame(item: object, expected: DataSchema, code: str, field: str) -> Frame:
    """Validate a frame at a port boundary and detach it from the caller's frame."""
    if not isinstance(item, Frame):
        raise BlockError(code, "Expected a table.", field=field)
    reason = _frame_violation(item)
    if reason is not None:
        raise BlockError(code, reason, field=field)
    if not schemas_compatible(item.data_schema, expected):
        raise BlockError(code, "Table schema is incompatible.", field=field)
    # Polars clones share buffers; in-place edits on the clone stay local.
    return Frame(item.data.clone(), item.data_schema)
