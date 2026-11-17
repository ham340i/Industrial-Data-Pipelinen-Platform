# AI contribution: 50% or more AI-generated
"""Workspace resource references, source configuration and path containment.

Shared by the execution readers, the bounded previews and the sinks so that
every file block resolves and limits resources through one rule set.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from app.blocks.context import BlockContext
from app.blocks.contracts import BlockConfig, Column, DataSchema, NonBlank
from app.blocks.errors import BlockError
from app.blocks.tabular import DType, POLARS_TYPES, checked_names


class ResourceConfig(BlockConfig):
    resource_ref: NonBlank = Field(
        max_length=256,
        description="Relative workspace resource, such as inputs/readings.csv.",
    )

    @field_validator("resource_ref")
    @classmethod
    def relative_resource(cls, value: str) -> str:
        if (
            not re.fullmatch(r"[A-Za-z0-9_./ -]+", value)
            or any(part in ("", ".", "..") for part in value.split("/"))
            or any(part.endswith((" ", ".")) for part in value.split("/"))
            or any(
                part.split(".")[0].upper()
                in {
                    "CON",
                    "PRN",
                    "AUX",
                    "NUL",
                    *(f"COM{i}" for i in range(1, 10)),
                    *(f"LPT{i}" for i in range(1, 10)),
                }
                for part in value.split("/")
            )
        ):
            raise ValueError("Use a relative resource without traversal")
        return value


def resource_path(context: BlockContext, resource: str, suffix: str) -> Path:
    if context.workspace_root is None:
        raise BlockError("workspace_required", "A runtime workspace root is required.")
    try:
        root = context.workspace_root.resolve(strict=True)
        candidate = (
            context.resolve_resource(resource)
            if context.resolve_resource
            else root / resource
        )
        if not isinstance(candidate, Path):
            raise ValueError("Resolver must return a path")
        target = candidate.resolve()
        target.relative_to(root)
        if not root.is_dir() or target == root or target.suffix.lower() != suffix:
            raise ValueError("Unsupported resource")
        return target
    except Exception:
        raise BlockError(
            "unsafe_resource",
            "Resource must be a supported file inside the workspace.",
            field="resource_ref",
        ) from None


class SourceConfig(ResourceConfig):
    columns: list[str] = Field(default_factory=list, max_length=1000)
    types: list[DType] = Field(
        default_factory=list,
        max_length=1000,
        description="Parallel SDK types: string, integer, number, boolean.",
    )
    nullable: list[bool] = Field(default_factory=list, max_length=1000)
    max_bytes: int = Field(default=16777216, ge=1, le=134217728)
    max_rows: int = Field(default=100000, ge=1, le=1000000)
    max_columns: int = Field(default=256, ge=1, le=1000)
    max_cells: int = Field(default=1000000, ge=1, le=2000000)

    @model_validator(mode="after")
    def schema_lists(self) -> SourceConfig:
        checked_names(self.columns)
        if len(self.columns) != len(self.types) or len(self.columns) != len(
            self.nullable
        ):
            raise ValueError("Schema lists must have the same length")
        if any(kind not in POLARS_TYPES for kind in self.types):
            raise ValueError("Unsupported SDK type")
        return self

    def declared_schema(self) -> DataSchema:
        return DataSchema(
            columns=tuple(
                Column(name=n, dtype=t, nullable=v)
                for n, t, v in zip(self.columns, self.types, self.nullable, strict=True)
            )
        )


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


class CsvConfig(SourceConfig):
    encoding: Literal["utf-8", "utf-8-sig", "latin-1"] = "utf-8"
    null_value: str = Field(default="NULL", min_length=1, max_length=64)


class JsonConfig(SourceConfig):
    encoding: Literal["utf-8", "utf-8-sig", "latin-1"] = "utf-8"


def check_source_file(path: Path, max_bytes: int) -> None:
    """Apply the shared availability and on-disk byte budget for sources."""
    try:
        if not path.is_file():
            raise BlockError(
                "file_unavailable",
                "Input file is missing or unreadable.",
                field="resource_ref",
            )
        if path.stat().st_size > max_bytes:
            raise BlockError("file_limit", "Input exceeds the configured byte limit.")
    except OSError:
        raise BlockError(
            "file_unavailable",
            "Input file is missing or unreadable.",
            field="resource_ref",
        ) from None
