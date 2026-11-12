"""Fixed source-work ceilings in addition to SDK returned-row/cell limits."""

from collections.abc import Iterator
from typing import BinaryIO

from app.blocks.context import BlockContext
from app.blocks.errors import BlockError

MAX_READ_BYTES = 2 * 1024 * 1024
MAX_RECORD_BYTES = 64 * 1024
MAX_FIELD_CHARS = 4096
MAX_COLUMNS = 128
MAX_COLUMN_CHARS = 128


class CsvLines(Iterator[str]):
    """Bound physical reads and multiline records before csv.reader allocates.

    The stream is unbuffered, so a prefix preview never reads the whole file or
    performs hidden read-ahead beyond its byte budget. One sentinel byte detects
    an exhausted budget. No process-global csv.field_size_limit is changed.
    """

    def __init__(
        self, stream: BinaryIO, encoding: str, budget: int, context: BlockContext
    ) -> None:
        self.stream, self.encoding = stream, encoding
        self.budget, self.context = budget, context
        self.read_bytes = 0
        self.record_bytes = 0
        self.first = True

    def __next__(self) -> str:
        self.context.check_cancelled()
        remaining = min(
            self.budget - self.read_bytes, MAX_RECORD_BYTES - self.record_bytes
        )
        data = self.stream.readline(remaining + 1)
        self.read_bytes += len(data)
        self.record_bytes += len(data)
        if self.read_bytes > self.budget or self.record_bytes > MAX_RECORD_BYTES:
            raise BlockError(
                "preview_read_limit",
                "CSV preview reached its byte or record-size budget. "
                "Use a smaller input or sample.",
            )
        if not data:
            raise StopIteration
        encoding = self.encoding
        if encoding == "utf-8-sig" and not self.first:
            encoding = "utf-8"
        self.first = False
        return data.decode(encoding)

    def next_record(self) -> None:
        self.record_bytes = 0
