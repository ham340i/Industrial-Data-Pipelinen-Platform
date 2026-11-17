# AI contribution: 50% or more AI-generated
"""Bounded JSON record preview, independent of the execution reader.

Also holds the column, value and schema checks shared with the Parquet preview.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterator
from typing import Any, BinaryIO

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
from app.blocks.inference import scalar_dtype
from app.blocks.preview_policy import (
    MAX_COLUMN_CHARS,
    MAX_COLUMNS,
    MAX_FIELD_CHARS,
    MAX_READ_BYTES,
    MAX_RECORD_BYTES,
)
from app.blocks.resources import JsonConfig, SourceConfig, resource_path, unique_object
from app.blocks.tabular import cast_column, checked_names, from_frame, to_frame


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

    def _open_array(self) -> None:
        """Consume an optional BOM, leading whitespace and the opening bracket."""
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

    def _record_bytes(self) -> bytearray:
        """Frame one flat object after its opening brace, within the record cap."""
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
                return record

    def __next__(self) -> dict[str, Any]:
        self.context.check_cancelled()
        if self.finished:
            raise StopIteration
        if not self.started:
            self._open_array()
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
        record = self._record_bytes()
        self.after_record = True
        # Decode BOM only at the start of the file, not at each record.
        encoding = "utf-8" if self.encoding == "utf-8-sig" else self.encoding
        row: dict[str, Any] = json.loads(
            record.decode(encoding), object_pairs_hook=unique_object
        )
        check_values(row)
        return row


def _sample(
    records: JsonRecords, config: JsonConfig, limits: PreviewLimits
) -> tuple[list[dict[str, Scalar]], list[str], int, bool]:
    """Read the bounded sample; return rows, column names, inspected, truncated."""
    rows: list[dict[str, Scalar]] = []
    names: list[str] = config.columns
    count = inspected = 0
    for row in records:
        if not inspected:
            names = list(row)
            count = names_and_limit(names, config, limits)
        elif set(row) != set(names):
            raise BlockError("schema_mismatch", "JSON record keys differ.")
        inspected += 1
        if len(rows) == count:
            return rows, names, inspected, True
        rows.append(row)
    return rows, names, inspected, False


def _sample_schema(
    names: list[str], rows: list[dict[str, Scalar]], config: JsonConfig
) -> DataSchema:
    columns = []
    for index, name in enumerate(names):
        kinds = {type(row[name]) for row in rows if row[name] is not None}
        if not kinds:
            if not config.columns:
                raise BlockError(
                    "schema_required",
                    "All-null columns need a schema.",
                    field=name,
                )
            kind = config.types[index]
        else:
            inferred = scalar_dtype(kinds)
            if inferred is None:
                raise BlockError(
                    "unsupported_type", "JSON column types differ.", field=name
                )
            kind = inferred
        columns.append(Column(name=name, dtype=kind, nullable=True))
    return DataSchema(columns=tuple(columns))


def _read_preview(
    config: JsonConfig, context: BlockContext, limits: PreviewLimits
) -> PortValues:
    path = resource_path(context, config.resource_ref, ".json")
    with path.open("rb", buffering=0) as stream:
        records = JsonRecords(
            stream, config.encoding, min(config.max_bytes, MAX_READ_BYTES), context
        )
        rows, names, inspected, truncated = _sample(records, config, limits)
        if not names:
            raise BlockError("schema_required", "Empty JSON requires a schema.")
        names_and_limit(names, config, limits)
        table = configured_table(
            Table(data_schema=_sample_schema(names, rows, config), rows=tuple(rows)),
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


def preview_json(
    config: JsonConfig, context: BlockContext, limits: PreviewLimits
) -> PortValues:
    context.check_cancelled()
    try:
        return _read_preview(config, context, limits)
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
