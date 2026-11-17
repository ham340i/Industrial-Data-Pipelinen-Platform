# AI contribution: below 50% AI-generated
"""Bounded JSON preview: flat-record framing, a sample and inferred types.

Moved out of app/blocks/file_preview.py (#32 review) so each preview module
stays under the size limit; the checks shared with Parquet previews stay
there and are imported here.
"""

from __future__ import annotations

import json
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
from app.blocks.file_preview import check_values, configured_table, names_and_limit
from app.blocks.files import JsonConfig, resource_path, unique_object
from app.blocks.preview_policy import MAX_READ_BYTES, MAX_RECORD_BYTES
from app.blocks.tabular import DType


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

    def open_array(self) -> None:
        """Consume an optional UTF-8 BOM, leading whitespace and ``[``."""
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

    def record_byte(self, record: bytearray) -> int:
        char = self.byte()
        if char == -1:
            raise ValueError("Incomplete record")
        record.append(char)
        if len(record) > MAX_RECORD_BYTES:
            raise BlockError("preview_read_limit", "JSON record budget exceeded.")
        return char

    def record_bytes(self) -> bytearray:
        """One flat ``{...}`` record, rejecting nesting outside strings."""
        record = bytearray(b"{")
        quoted = escaped = False
        while True:
            char = self.record_byte(record)
            if quoted:
                quoted, escaped = string_state(char, escaped)
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
            self.open_array()
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
        record = self.record_bytes()
        self.after_record = True
        # Decode BOM only at the start of the file, not at each record.
        encoding = "utf-8" if self.encoding == "utf-8-sig" else self.encoding
        row: dict[str, Any] = json.loads(
            record.decode(encoding), object_pairs_hook=unique_object
        )
        check_values(row)
        return row


def string_state(char: int, escaped: bool) -> tuple[bool, bool]:
    """(still quoted, next byte escaped) after ``char`` inside a JSON string."""
    if escaped:
        return True, False
    if char == 92:
        return True, True
    return char != 34, False


def json_sample(
    records: JsonRecords, config: JsonConfig, limits: PreviewLimits
) -> tuple[list[str], list[dict[str, Scalar]], int, bool]:
    """Column names, up to the preview row budget, inspected count, truncation."""
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
            return names, rows, inspected, True
        rows.append(row)
    return names, rows, inspected, False


def json_column_kind(
    name: str, index: int, rows: list[dict[str, Scalar]], config: JsonConfig
) -> DType:
    kinds = {type(row[name]) for row in rows if row[name] is not None}
    if not kinds:
        if not config.columns:
            raise BlockError(
                "schema_required", "All-null columns need a schema.", field=name
            )
        return config.types[index]
    if kinds <= {int, float}:
        return "number" if float in kinds else "integer"
    if kinds == {str}:
        return "string"
    if kinds == {bool}:
        return "boolean"
    raise BlockError("unsupported_type", "JSON column types differ.", field=name)


def json_schema(
    names: list[str], rows: list[dict[str, Scalar]], config: JsonConfig
) -> DataSchema:
    return DataSchema(
        columns=tuple(
            Column(
                name=name,
                dtype=json_column_kind(name, index, rows, config),
                nullable=True,
            )
            for index, name in enumerate(names)
        )
    )


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
            names, rows, inspected, truncated = json_sample(records, config, limits)
            if not names:
                raise BlockError("schema_required", "Empty JSON requires a schema.")
            names_and_limit(names, config, limits)
            table = configured_table(
                Table(data_schema=json_schema(names, rows, config), rows=tuple(rows)),
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
