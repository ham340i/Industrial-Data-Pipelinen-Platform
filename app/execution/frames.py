"""Lossless SDK v1 scalar-schema adapters for eager Polars execution."""

from dataclasses import dataclass

import polars as pl

from app.blocks.contracts import ControlSignal, DataSchema, PortValues, Table
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
