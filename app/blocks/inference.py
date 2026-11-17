# AI contribution: 50% or more AI-generated
"""SDK scalar type inference shared by execution readers and previews.

Both functions return ``None`` for an unsupported type so each caller keeps
its own public error code and message.
"""

from __future__ import annotations

import pyarrow as pa

from app.blocks.tabular import DType


def arrow_dtype(kind: pa.DataType) -> DType | None:
    """Map an Arrow column type to its SDK scalar type."""
    if pa.types.is_string(kind) or pa.types.is_large_string(kind):
        return "string"
    if pa.types.is_integer(kind):
        return "integer"
    if pa.types.is_floating(kind):
        return "number"
    if pa.types.is_boolean(kind):
        return "boolean"
    return None


def scalar_dtype(kinds: set[type]) -> DType | None:
    """Map the Python types seen in one JSON column to its SDK scalar type.

    ``kinds`` holds the types of the column's non-null values and must not be
    empty; an all-null column has no inferable type.
    """
    if kinds <= {int, float}:
        return "number" if float in kinds else "integer"
    if kinds == {str}:
        return "string"
    if kinds == {bool}:
        return "boolean"
    return None
