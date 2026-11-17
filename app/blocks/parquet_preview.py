"""Bounded Parquet batch preview, independent of the execution reader.

Parquet limits bound reads and declared decoding work, not native allocator RSS.
Corrupt metadata/codec behavior is not a hard process-isolation boundary.
"""

from __future__ import annotations

import io
from typing import Any, BinaryIO

import pyarrow as pa
import pyarrow.parquet as pq

from app.blocks.context import BlockContext
from app.blocks.contracts import (
    Column,
    DataSchema,
    PortValues,
    PreviewLimits,
    PreviewObservation,
    Scalar,
    Table,
)
from app.blocks.errors import BlockError
from app.blocks.file_preview import check_values, configured_table, names_and_limit
from app.blocks.inference import arrow_dtype
from app.blocks.preview_policy import MAX_COLUMNS, MAX_READ_BYTES, MAX_RECORD_BYTES
from app.blocks.resources import SourceConfig, resource_path

MAX_FOOTER_BYTES = 256 * 1024
MAX_DECODE_BYTES = 8 * 1024 * 1024
MAX_ROW_GROUPS = 1024


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


def parquet_schema(arrow: pa.Schema) -> DataSchema:
    columns = []
    for item in arrow:
        kind = arrow_dtype(item.type)
        if kind is None:
            raise BlockError("unsupported_type", "Unsupported Parquet scalar type.")
        columns.append(Column(name=item.name, dtype=kind, nullable=item.nullable))
    return DataSchema(columns=tuple(columns))


def _check_footer(source: BudgetFile) -> None:
    """Validate the magic bytes and footer size before Arrow parses metadata."""
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


def _row_groups(metadata: Any, wanted: int, context: BlockContext) -> list[int]:
    """Pick the leading row groups holding wanted rows, within decode budget."""
    groups: list[int] = []
    available = decode_bytes = 0
    for index in range(metadata.num_row_groups):
        context.check_cancelled()
        if available >= wanted:
            break
        group = metadata.row_group(index)
        if group.num_rows < 0:
            raise ValueError("Invalid group")
        for col in range(group.num_columns):
            chunk = group.column(col)
            if chunk.total_uncompressed_size < 0:
                raise ValueError("Invalid chunk")
            decode_bytes += chunk.total_uncompressed_size
        if decode_bytes > MAX_DECODE_BYTES:
            raise BlockError(
                "preview_decode_limit", "Parquet row groups are too large."
            )
        available += group.num_rows
        groups.append(index)
    return groups


def _read_rows(
    file: pq.ParquetFile, groups: list[int], wanted: int, context: BlockContext
) -> tuple[list[dict[str, Scalar]], int]:
    """Decode up to wanted rows; return them and the rows inspected."""
    rows: list[dict[str, Scalar]] = []
    inspected = 0
    if not wanted:
        return rows, inspected
    for batch in file.iter_batches(
        batch_size=wanted, row_groups=groups, use_threads=False
    ):
        context.check_cancelled()
        if batch.nbytes > MAX_DECODE_BYTES:
            raise BlockError("preview_decode_limit", "Decoded batch is too large.")
        inspected += batch.num_rows
        rows.extend(batch.slice(0, wanted - len(rows)).to_pylist())
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
    metadata = file.metadata
    if metadata.num_row_groups > MAX_ROW_GROUPS or metadata.num_columns > MAX_COLUMNS:
        raise BlockError("preview_decode_limit", "Parquet metadata is too large.")
    schema = parquet_schema(file.schema_arrow)
    count = names_and_limit([c.name for c in schema.columns], config, limits)
    total = metadata.num_rows
    if total < 0:
        raise ValueError("Invalid count")
    wanted = min(count, total)
    groups = _row_groups(metadata, wanted, context)
    rows, inspected = _read_rows(file, groups, wanted, context)
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
            _check_footer(source)
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
