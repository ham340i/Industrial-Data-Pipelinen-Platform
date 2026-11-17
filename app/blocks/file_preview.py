# AI contribution: below 50% AI-generated
"""Bounded Parquet batches and the preview checks shared with JSON previews.

JSON record framing lives in app/blocks/json_preview.py and CSV in
app/blocks/csv_preview.py; both are independent of the execution readers.

Parquet limits bound reads and declared decoding work, not native allocator RSS.
Corrupt metadata/codec behavior is not a hard process-isolation boundary.
"""

from __future__ import annotations

import io
import math
from typing import Any, BinaryIO

import pyarrow.parquet as pq

from app.blocks.context import BlockContext
from app.blocks.contracts import (
    DataSchema,
    PortValues,
    PreviewLimits,
    PreviewObservation,
    Scalar,
    Table,
)
from app.blocks.errors import BlockError
from app.blocks.files import SourceConfig, resource_path
from app.blocks.parquet_decode import (
    decoded_bytes,
    group_uncompressed_bytes,
    parquet_schema,
    string_columns,
)
from app.blocks.preview_policy import (
    MAX_COLUMN_CHARS,
    MAX_COLUMNS,
    MAX_FIELD_CHARS,
    MAX_READ_BYTES,
    MAX_RECORD_BYTES,
)
from app.blocks.tabular import cast_column, checked_names, from_frame, to_frame

MAX_FOOTER_BYTES = 256 * 1024
MAX_DECODE_BYTES = 8 * 1024 * 1024
MAX_ROW_GROUPS = 1024


def names_and_limit(
    names: list[str], config: SourceConfig, limits: PreviewLimits
) -> int:
    checked_names(names)
    for name in names:
        name.encode("utf-8")
    if (
        not names
        or len(names) > min(config.max_columns, MAX_COLUMNS)
        or any(len(name) > MAX_COLUMN_CHARS for name in names)
    ):
        raise BlockError("preview_columns", "Preview column bounds exceeded.")
    if config.columns and names != config.columns:
        raise BlockError(
            "schema_mismatch",
            "Configured columns differ from the source.",
            field="columns",
        )
    count = min(
        limits.max_rows,
        config.max_rows,
        limits.max_cells // len(names),
        config.max_cells // len(names),
    )
    if count < 1:
        raise BlockError("preview_limit", "The cell budget cannot hold a row.")
    return count


def check_values(row: dict[str, Any]) -> None:
    for value in row.values():
        if value is not None and type(value) not in (str, int, float, bool):
            raise BlockError("unsupported_type", "Only scalar values are supported.")
        if isinstance(value, str) and len(value) > MAX_FIELD_CHARS:
            raise BlockError(
                "preview_field_limit", "A field exceeds the preview limit."
            )
        if isinstance(value, str):
            value.encode("utf-8")
        if type(value) is float and not math.isfinite(value):
            raise BlockError("unsupported_value", "Non-finite values are unsupported.")


def configured_table(
    table: Table, config: SourceConfig, context: BlockContext
) -> Table:
    frame = to_frame(table)
    if config.columns:
        for name, kind in zip(config.columns, config.types, strict=True):
            context.check_cancelled()
            frame = cast_column(frame, name, kind)
        table = from_frame(frame, config.declared_schema())
    # Casts can create strings; apply field limits to the final values as well.
    for row in table.rows:
        check_values(row)
    return table


class BudgetFile(io.RawIOBase):
    """Seekable Arrow input counting every read, including repeated footer reads."""

    def __init__(self, stream: BinaryIO, budget: int, context: BlockContext) -> None:
        super().__init__()
        self.stream, self.budget, self.context = stream, budget, context
        self.read_bytes = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.stream.tell()

    def seek(self, offset: int, whence: int = 0) -> int:
        self.context.check_cancelled()
        return self.stream.seek(offset, whence)

    def read(self, size: int = -1) -> bytes:
        self.context.check_cancelled()
        remaining = self.budget - self.read_bytes
        amount = remaining + 1 if size < 0 else min(size, remaining + 1)
        try:
            data = self.stream.read(amount)
        except OSError:
            raise BlockError("file_unavailable", "Input is unreadable.") from None
        self.read_bytes += len(data)
        if self.read_bytes > self.budget:
            raise BlockError("preview_read_limit", "Parquet read budget exceeded.")
        return data

    def readinto(self, buffer: Any) -> int:
        data = self.read(len(buffer))
        buffer[: len(data)] = data
        return len(data)


def check_parquet_envelope(source: BudgetFile) -> None:
    """Magic bytes and footer length, read before Arrow parses any metadata."""
    size = source.seek(0, 2)
    if size < 12:
        raise ValueError("Incomplete Parquet")
    source.seek(0)
    if source.read(4) != b"PAR1":
        raise ValueError("Invalid magic")
    source.seek(-8, 2)
    trailer = source.read(8)
    footer_size = int.from_bytes(trailer[:4], "little")
    if trailer[4:] != b"PAR1" or footer_size > size - 12:
        raise ValueError("Invalid footer")
    if footer_size > MAX_FOOTER_BYTES:
        raise BlockError("preview_decode_limit", "Parquet footer is too large.")
    source.seek(0)


def check_parquet_metadata(metadata: pq.FileMetaData) -> None:
    if metadata.num_row_groups > MAX_ROW_GROUPS or metadata.num_columns > MAX_COLUMNS:
        raise BlockError("preview_decode_limit", "Parquet metadata is too large.")


def declared_rows(metadata: pq.FileMetaData) -> int:
    if metadata.num_rows < 0:
        raise ValueError("Invalid count")
    return int(metadata.num_rows)


def preview_row_groups(
    metadata: pq.FileMetaData, wanted: int, context: BlockContext
) -> list[int]:
    """Leading row groups covering ``wanted`` rows within the declared budget."""
    groups = []
    available = decode_bytes = 0
    for index in range(metadata.num_row_groups):
        context.check_cancelled()
        if available >= wanted:
            break
        group = metadata.row_group(index)
        if group.num_rows < 0:
            raise ValueError("Invalid group")
        decode_bytes += group_uncompressed_bytes(group)
        if decode_bytes > MAX_DECODE_BYTES:
            raise BlockError(
                "preview_decode_limit", "Parquet row groups are too large."
            )
        available += group.num_rows
        groups.append(index)
    return groups


def parquet_sample(
    source: BudgetFile,
    metadata: pq.FileMetaData,
    schema: DataSchema,
    groups: list[int],
    count: int,
    wanted: int,
    context: BlockContext,
) -> tuple[list[dict[str, Scalar]], int]:
    """Rows from ``groups`` until ``wanted`` are held, and rows decoded.

    Each batch is sliced to the preview ``count``, not ``wanted``, so a footer
    that under-declares its rows still fails the caller's row-count check.
    """
    rows: list[dict[str, Scalar]] = []
    inspected = 0
    # Keep strings dictionary-encoded until their expanded size is known to
    # fit the decode budget (#32).
    dictionary_file = pq.ParquetFile(
        source,
        metadata=metadata,
        memory_map=False,
        buffer_size=0,
        pre_buffer=False,
        read_dictionary=string_columns(schema),
    )
    for batch in dictionary_file.iter_batches(
        batch_size=wanted, row_groups=groups, use_threads=False
    ):
        context.check_cancelled()
        if decoded_bytes(batch) > MAX_DECODE_BYTES:
            raise BlockError("preview_decode_limit", "Decoded batch is too large.")
        inspected += batch.num_rows
        rows.extend(batch.slice(0, count - len(rows)).to_pylist())
        if len(rows) >= wanted:
            break
    return rows, inspected


def _sample_file(
    file: pq.ParquetFile,
    source: BudgetFile,
    config: SourceConfig,
    context: BlockContext,
    limits: PreviewLimits,
) -> PortValues:
    """Decode the bounded leading sample of an already opened Parquet file."""
    metadata = file.metadata
    check_parquet_metadata(metadata)
    schema = parquet_schema(file.schema_arrow)
    count = names_and_limit([c.name for c in schema.columns], config, limits)
    total = declared_rows(metadata)
    wanted = min(count, total)
    groups = preview_row_groups(metadata, wanted, context)
    rows, inspected = (
        parquet_sample(source, metadata, schema, groups, count, wanted, context)
        if total
        else ([], 0)
    )
    if len(rows) != wanted:
        raise ValueError("Metadata and sample disagree")
    for row in rows:
        check_values(row)
    table = configured_table(
        Table(data_schema=schema, rows=tuple(rows)), config, context
    )
    context.check_cancelled()
    if context.observe_preview:
        context.observe_preview(
            PreviewObservation(
                inspected_rows=inspected,
                full_row_count=total,
                truncated=len(rows) < total,
                schema_scope="declared" if config.columns else "file_metadata",
                full_count_scope="file_metadata",
                read_bytes=source.read_bytes,
            )
        )
    return {"table": (table,)}


def preview_parquet(
    config: SourceConfig, context: BlockContext, limits: PreviewLimits
) -> PortValues:
    context.check_cancelled()
    path = resource_path(context, config.resource_ref, ".parquet")
    try:
        stream = path.open("rb", buffering=0)
    except OSError:
        raise BlockError(
            "file_unavailable", "Input is missing or unreadable.", field="resource_ref"
        ) from None
    try:
        with stream:
            source = BudgetFile(stream, min(config.max_bytes, MAX_READ_BYTES), context)
            check_parquet_envelope(source)
            with pq.ParquetFile(
                source,
                memory_map=False,
                buffer_size=0,
                pre_buffer=False,
                thrift_string_size_limit=MAX_RECORD_BYTES,
                thrift_container_size_limit=10000,
            ) as file:
                return _sample_file(file, source, config, context, limits)
    except BlockError:
        raise
    except Exception:
        raise BlockError(
            "invalid_parquet", "Parquet metadata or sample is invalid."
        ) from None
