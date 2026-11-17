# AI contribution: 50% or more AI-generated
"""Bounded CSV prefix preview, independent of the execution reader (#26)."""

from __future__ import annotations

import csv
from collections.abc import Iterator

import polars as pl

from app.blocks.context import BlockContext
from app.blocks.contracts import (
    Column,
    DataSchema,
    PortValues,
    PreviewLimits,
    PreviewObservation,
    Table,
)
from app.blocks.errors import BlockError
from app.blocks.preview_policy import (
    MAX_COLUMN_CHARS,
    MAX_COLUMNS,
    MAX_FIELD_CHARS,
    MAX_READ_BYTES,
    CsvLines,
)
from app.blocks.resources import CsvConfig, resource_path
from app.blocks.tabular import cast_column, checked_names, from_frame

Row = dict[str, str | None]


def _checked_header(reader: Iterator[list[str]], config: CsvConfig) -> list[str]:
    header = next(reader, [])
    if not header or len(header) > min(config.max_columns, MAX_COLUMNS):
        raise BlockError(
            "preview_columns",
            "CSV preview requires 1 to 128 columns within the source limit.",
        )
    checked_names(header)
    if any(len(name) > MAX_COLUMN_CHARS for name in header):
        raise BlockError(
            "preview_columns",
            "CSV preview column names exceed the supported length.",
        )
    if config.columns and header != config.columns:
        raise BlockError(
            "schema_mismatch",
            "Declared columns must match source order and names.",
            field="columns",
        )
    return header


def _row_budget(width: int, config: CsvConfig, limits: PreviewLimits) -> int:
    count = min(
        limits.max_rows,
        limits.max_cells // width,
        config.max_rows,
        config.max_cells // width,
    )
    if count < 1:
        raise BlockError(
            "preview_limit",
            "The cell limit cannot hold one row of this schema.",
        )
    return count


def _sample(
    reader: Iterator[list[str]],
    lines: CsvLines,
    header: list[str],
    config: CsvConfig,
    count: int,
) -> tuple[list[Row], int, bool]:
    """Read up to ``count`` rows; return them, rows inspected and truncation."""
    rows: list[Row] = []
    inspected = 0
    while True:
        lines.next_record()
        values = next(reader, None)
        if values is None:
            return rows, inspected, False
        inspected += 1
        if len(values) != len(header):
            raise BlockError("invalid_csv", "CSV row width differs from its header.")
        if any(len(value) > MAX_FIELD_CHARS for value in values):
            raise BlockError(
                "preview_field_limit",
                "A CSV preview field exceeds 4096 characters.",
            )
        if len(rows) == count:
            return rows, inspected, True
        rows.append(
            {
                name: None if value == config.null_value else value
                for name, value in zip(header, values, strict=True)
            }
        )


def _typed_table(
    rows: list[Row], header: list[str], config: CsvConfig, context: BlockContext
) -> Table:
    frame = pl.DataFrame(rows, schema={name: pl.String for name in header})
    if config.columns:
        for name, kind in zip(config.columns, config.types, strict=True):
            context.check_cancelled()
            frame = cast_column(frame, name, kind)
        return from_frame(frame, config.declared_schema())
    # A prefix cannot establish whole-file non-nullability.
    schema = DataSchema(
        columns=tuple(
            Column(name=name, dtype="string", nullable=True) for name in header
        )
    )
    return from_frame(frame, schema)


def _read_preview(
    config: CsvConfig, context: BlockContext, limits: PreviewLimits
) -> PortValues:
    path = resource_path(context, config.resource_ref, ".csv")
    if not path.is_file():
        raise OSError
    with path.open("rb", buffering=0) as stream:
        lines = CsvLines(
            stream,
            config.encoding,
            min(config.max_bytes, MAX_READ_BYTES),
            context,
        )
        reader = csv.reader(lines, strict=True)
        header = _checked_header(reader, config)
        count = _row_budget(len(header), config, limits)
        rows, inspected, truncated = _sample(reader, lines, header, config, count)
        context.check_cancelled()
        table = _typed_table(rows, header, config, context)
        context.check_cancelled()
        if context.observe_preview is not None:
            context.observe_preview(
                PreviewObservation(
                    inspected_rows=inspected,
                    full_row_count=None if truncated else len(rows),
                    truncated=truncated,
                    schema_scope="declared" if config.columns else "header",
                    full_count_scope="unknown" if truncated else "observed",
                    read_bytes=lines.read_bytes,
                )
            )
        return {"table": (table,)}


def preview_csv(
    config: CsvConfig, context: BlockContext, limits: PreviewLimits
) -> PortValues:
    context.check_cancelled()
    try:
        return _read_preview(config, context, limits)
    except BlockError:
        raise
    except OSError:
        raise BlockError(
            "file_unavailable",
            "Input file is missing or unreadable.",
            field="resource_ref",
        ) from None
    except Exception:
        raise BlockError(
            "invalid_csv",
            "CSV format, encoding, headers or scalar values are invalid.",
        ) from None
