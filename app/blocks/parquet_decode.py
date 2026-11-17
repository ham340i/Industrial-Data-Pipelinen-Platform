# AI contribution: 50% or more AI-generated
"""Decoded-size checks shared by Parquet execution and preview (#32).

A Parquet file can be tiny on disk and still decode to gigabytes, either
through large plain pages (caught from writer-declared page sizes before
reading) or through dictionary repetition (caught from dictionary value
lengths and indices before expansion). Both readers use these helpers so the
two paths cannot drift apart.
"""

from __future__ import annotations

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from app.blocks.contracts import Column, DataSchema
from app.blocks.errors import BlockError
from app.blocks.tabular import DType

# Decoded Parquet may exceed its on-disk size by this factor before execution
# refuses it; MAX_PARQUET_DECODE_BYTES caps it for the largest allowed file.
PARQUET_DECODE_FACTOR = 16
MAX_PARQUET_DECODE_BYTES = 1024 * 1024 * 1024


def parquet_decode_budget(max_bytes: int) -> int:
    return min(max_bytes * PARQUET_DECODE_FACTOR, MAX_PARQUET_DECODE_BYTES)


def parquet_schema(arrow: pa.Schema) -> DataSchema:
    """Map an Arrow schema onto SDK scalar types, refusing anything else."""
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


def string_columns(schema: DataSchema) -> list[str]:
    """Columns to read with ``read_dictionary`` so expansion can be measured."""
    return [column.name for column in schema.columns if column.dtype == "string"]


def group_uncompressed_bytes(group: pq.RowGroupMetaData) -> int:
    """Writer-declared page bytes across one row group's column chunks."""
    total = 0
    for column in range(group.num_columns):
        size = group.column(column).total_uncompressed_size
        if size < 0:
            raise ValueError("Invalid column chunk size")
        total += size
    return total


def uncompressed_bytes(metadata: pq.FileMetaData) -> int:
    """Writer-declared page bytes across every column chunk."""
    return sum(
        group_uncompressed_bytes(metadata.row_group(index))
        for index in range(metadata.num_row_groups)
    )


def decoded_bytes(data: pa.Table | pa.RecordBatch) -> int:
    """Bytes ``data`` occupies once dictionary columns are expanded.

    Computed from dictionary value lengths and indices, without expanding
    them: a dictionary page can repeat one long string for every row, so a
    file with a small declared page size can still decode to gigabytes
    (#32). Read string columns with ``read_dictionary`` before calling this.
    """
    total = 0
    for column in data.columns:
        chunks = column.chunks if isinstance(column, pa.ChunkedArray) else [column]
        for chunk in chunks:
            if pa.types.is_dictionary(chunk.type):
                lengths = pc.binary_length(chunk.dictionary).take(chunk.indices)
                total += (pc.sum(lengths).as_py() or 0) + chunk.indices.nbytes
            else:
                total += chunk.nbytes
    return total


def expand_dictionaries(table: pa.Table) -> pa.Table:
    return table.cast(
        pa.schema(
            pa.field(
                field.name,
                field.type.value_type
                if pa.types.is_dictionary(field.type)
                else field.type,
                nullable=field.nullable,
            )
            for field in table.schema
        )
    )
