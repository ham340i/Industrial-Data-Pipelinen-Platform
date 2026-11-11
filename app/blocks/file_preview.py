"""Bounded JSON records and Parquet batches, independent of execution readers.

Parquet limits bound reads and declared decoding work, not native allocator RSS.
Corrupt metadata/codec behavior is not a hard process-isolation boundary.
"""

from __future__ import annotations

from collections.abc import Iterator
import io
import json
import math
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
from app.blocks.files import JsonConfig, SourceConfig, resource_path, unique_object
from app.blocks.preview_policy import (
    MAX_COLUMN_CHARS,
    MAX_COLUMNS,
    MAX_FIELD_CHARS,
    MAX_READ_BYTES,
    MAX_RECORD_BYTES,
)
from app.blocks.tabular import DType, cast_column, checked_names, from_frame, to_frame

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


class JsonRecords(Iterator[dict[str, Any]]):
    """Frame flat objects; the standard JSON decoder validates each whole record.

    A 1 KiB read-ahead buffer and 64 KiB record cap bound allocations before
    json.loads. Nested arrays/objects are rejected before decoding, including
    the lookahead record. Whitespace is subject to the same total byte budget.
    """

    def __init__(
        self, stream: BinaryIO, encoding: str, budget: int, context: BlockContext
    ) -> None:
        self.stream, self.encoding, self.budget, self.context = (
            stream,
            encoding,
            budget,
            context,
        )
        self.buffer = b""
        self.position = 0
        self.read_bytes = 0
        self.started = False
        self.after_record = False
        self.finished = False

    def byte(self) -> int:
        if self.position == len(self.buffer):
            self.context.check_cancelled()
            self.buffer = self.stream.read(min(1024, self.budget - self.read_bytes + 1))
            self.read_bytes += len(self.buffer)
            if self.read_bytes > self.budget:
                raise BlockError("preview_read_limit", "JSON read budget exceeded.")
            self.position = 0
            if not self.buffer:
                return -1
        result = self.buffer[self.position]
        self.position += 1
        return result

    def nonspace(self) -> int:
        char = self.byte()
        while char in (9, 10, 13, 32):
            char = self.byte()
        return char

    def __iter__(self) -> JsonRecords:
        return self

    def __next__(self) -> dict[str, Any]:
        self.context.check_cancelled()
        if self.finished:
            raise StopIteration
        if not self.started:
            char = self.byte()
            if char == 239 and self.encoding == "utf-8-sig":
                if (self.byte(), self.byte()) != (187, 191):
                    raise ValueError("Invalid BOM")
                char = self.byte()
            while char in (9, 10, 13, 32):
                char = self.byte()
            if char != 91:
                raise ValueError("Expected array")
            self.started = True
        char = self.nonspace()
        if char == 93:
            if self.nonspace() != -1:
                raise ValueError("Trailing content")
            self.finished = True
            raise StopIteration
        if self.after_record:
            if char != 44:
                raise ValueError("Expected separator")
            char = self.nonspace()
        if char != 123:
            raise ValueError("Expected record")
        record = bytearray(b"{")
        quoted = escaped = False
        while True:
            char = self.byte()
            if char == -1:
                raise ValueError("Incomplete record")
            record.append(char)
            if len(record) > MAX_RECORD_BYTES:
                raise BlockError("preview_read_limit", "JSON record budget exceeded.")
            if quoted:
                if escaped:
                    escaped = False
                elif char == 92:
                    escaped = True
                elif char == 34:
                    quoted = False
            elif char == 34:
                quoted = True
            elif char in (91, 123):
                raise BlockError("unsupported_type", "Nested JSON is unsupported.")
            elif char == 125:
                break
        self.after_record = True
        # Decode BOM only at the start of the file, not at each record.
        encoding = "utf-8" if self.encoding == "utf-8-sig" else self.encoding
        row: dict[str, Any] = json.loads(
            record.decode(encoding), object_pairs_hook=unique_object
        )
        check_values(row)
        return row


def preview_json(
    config: JsonConfig, context: BlockContext, limits: PreviewLimits
) -> PortValues:
    context.check_cancelled()
    path = resource_path(context, config.resource_ref, ".json")
    try:
        with path.open("rb", buffering=0) as stream:
            records = JsonRecords(
                stream, config.encoding, min(config.max_bytes, MAX_READ_BYTES), context
            )
            rows: list[dict[str, Scalar]] = []
            names: list[str] = config.columns
            count = inspected = 0
            truncated = False
            for row in records:
                if not inspected:
                    names = list(row)
                    count = names_and_limit(names, config, limits)
                elif set(row) != set(names):
                    raise BlockError("schema_mismatch", "JSON record keys differ.")
                inspected += 1
                if len(rows) == count:
                    truncated = True
                    break
                rows.append(row)
            if not names:
                raise BlockError("schema_required", "Empty JSON requires a schema.")
            names_and_limit(names, config, limits)
            columns = []
            for index, name in enumerate(names):
                kinds = {type(row[name]) for row in rows if row[name] is not None}
                kind: DType
                if not kinds:
                    if not config.columns:
                        raise BlockError(
                            "schema_required",
                            "All-null columns need a schema.",
                            field=name,
                        )
                    kind = config.types[index]
                elif kinds <= {int, float}:
                    kind = "number" if float in kinds else "integer"
                elif kinds == {str}:
                    kind = "string"
                elif kinds == {bool}:
                    kind = "boolean"
                else:
                    raise BlockError(
                        "unsupported_type", "JSON column types differ.", field=name
                    )
                columns.append(Column(name=name, dtype=kind, nullable=True))
            table = configured_table(
                Table(data_schema=DataSchema(columns=tuple(columns)), rows=tuple(rows)),
                config,
                context,
            )
            context.check_cancelled()
            if context.observe_preview:
                context.observe_preview(
                    PreviewObservation(
                        inspected_rows=inspected,
                        full_row_count=None if truncated else len(rows),
                        truncated=truncated,
                        schema_scope="declared" if config.columns else "sample",
                        full_count_scope="unknown" if truncated else "observed",
                        read_bytes=records.read_bytes,
                    )
                )
            return {"table": (table,)}
    except BlockError:
        raise
    except OSError:
        raise BlockError(
            "file_unavailable", "Input is missing or unreadable.", field="resource_ref"
        ) from None
    except Exception:
        raise BlockError(
            "invalid_json", "JSON records or encoding are invalid."
        ) from None


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
        kind: DType
        if pa.types.is_string(item.type) or pa.types.is_large_string(item.type):
            kind = "string"
        elif pa.types.is_integer(item.type):
            kind = "integer"
        elif pa.types.is_floating(item.type):
            kind = "number"
        elif pa.types.is_boolean(item.type):
            kind = "boolean"
        else:
            raise BlockError("unsupported_type", "Unsupported Parquet scalar type.")
        columns.append(Column(name=item.name, dtype=kind, nullable=item.nullable))
    return DataSchema(columns=tuple(columns))


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
            with pq.ParquetFile(
                source,
                memory_map=False,
                buffer_size=0,
                pre_buffer=False,
                thrift_string_size_limit=MAX_RECORD_BYTES,
                thrift_container_size_limit=10000,
            ) as file:
                metadata = file.metadata
                if (
                    metadata.num_row_groups > MAX_ROW_GROUPS
                    or metadata.num_columns > MAX_COLUMNS
                ):
                    raise BlockError(
                        "preview_decode_limit", "Parquet metadata is too large."
                    )
                schema = parquet_schema(file.schema_arrow)
                count = names_and_limit(
                    [c.name for c in schema.columns], config, limits
                )
                total = metadata.num_rows
                if total < 0:
                    raise ValueError("Invalid count")
                groups = []
                available = decode_bytes = 0
                for index in range(metadata.num_row_groups):
                    context.check_cancelled()
                    if available >= min(count, total):
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
                rows: list[dict[str, Scalar]] = []
                inspected = 0
                if total:
                    for batch in file.iter_batches(
                        batch_size=min(count, total),
                        row_groups=groups,
                        use_threads=False,
                    ):
                        context.check_cancelled()
                        if batch.nbytes > MAX_DECODE_BYTES:
                            raise BlockError(
                                "preview_decode_limit", "Decoded batch is too large."
                            )
                        inspected += batch.num_rows
                        rows.extend(batch.slice(0, count - len(rows)).to_pylist())
                        if len(rows) >= min(count, total):
                            break
                if len(rows) != min(count, total):
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
                            schema_scope="declared"
                            if config.columns
                            else "file_metadata",
                            full_count_scope="file_metadata",
                            read_bytes=source.read_bytes,
                        )
                    )
                return {"table": (table,)}
    except BlockError:
        raise
    except Exception:
        raise BlockError(
            "invalid_parquet", "Parquet metadata or sample is invalid."
        ) from None
