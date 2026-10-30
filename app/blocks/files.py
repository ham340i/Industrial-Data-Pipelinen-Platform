"""Workspace-bound file readers and atomic file writers (#16, #20)."""

from __future__ import annotations

import csv
import io
import json
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Literal

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import Field, field_validator, model_validator

from app.blocks.base import Block
from app.blocks.context import BlockContext
from app.blocks.contracts import (
    BlockConfig,
    BlockDescriptor,
    Column,
    DataSchema,
    NonBlank,
    Port,
    PortValues,
    Table,
)
from app.blocks.errors import BlockError
from app.blocks.tabular import (
    DType,
    POLARS_TYPES,
    TABLE_PORT,
    cast_column,
    checked_names,
    descriptor_values,
    from_frame,
    to_frame,
)

ARROW_TYPES = {
    "string": pa.string(),
    "integer": pa.int64(),
    "number": pa.float64(),
    "boolean": pa.bool_(),
}


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


class FileSource[SourceT: SourceConfig](Block[SourceT]):
    suffix = ""

    def _read(
        self, path: Path, config: SourceT
    ) -> tuple[pl.DataFrame, DataSchema | None]:
        raise NotImplementedError

    def _execute(
        self, config: SourceT, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        path = resource_path(context, config.resource_ref, self.suffix)
        try:
            if not path.is_file():
                raise BlockError(
                    "file_unavailable",
                    "Input file is missing or unreadable.",
                    field="resource_ref",
                )
            if path.stat().st_size > config.max_bytes:
                raise BlockError(
                    "file_limit", "Input exceeds the configured byte limit."
                )
            frame, schema = self._read(path, config)
            if (
                len(frame) > config.max_rows
                or frame.width > config.max_columns
                or len(frame) * frame.width > config.max_cells
            ):
                raise BlockError(
                    "table_limit", "Input exceeds the configured table limits."
                )
            if config.columns:
                if frame.columns != config.columns:
                    raise BlockError(
                        "schema_mismatch",
                        "Declared columns must match source order and names.",
                        field="columns",
                    )
                for name, kind in zip(config.columns, config.types, strict=True):
                    frame = cast_column(frame, name, kind)
                schema = config.declared_schema()
            return {"table": (from_frame(frame, schema),)}
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
                "invalid_file", "Input format, encoding or scalar values are invalid."
            ) from None


class CsvSource(FileSource[CsvConfig]):
    config_model = CsvConfig
    suffix = ".csv"
    descriptor = BlockDescriptor(
        **descriptor_values("source.csv", "CSV Source", "source"), outputs=(TABLE_PORT,)
    )

    def _read(
        self, path: Path, config: CsvConfig
    ) -> tuple[pl.DataFrame, DataSchema | None]:
        # Harden the proof's strict csv.reader rather than trusting inferred rows.
        data = path.read_bytes()
        if len(data) > config.max_bytes:
            raise BlockError("file_limit", "Input exceeds the configured byte limit.")
        reader = csv.reader(
            io.StringIO(data.decode(config.encoding), newline=""), strict=True
        )
        header = next(reader, [])
        if len(header) > config.max_columns:
            raise BlockError("table_limit", "CSV exceeds the column limit.")
        try:
            checked_names(header)
            if not header:
                raise ValueError("Missing header")
        except ValueError:
            raise BlockError(
                "invalid_csv", "CSV requires unique nonblank headers."
            ) from None
        rows = []
        for values in reader:
            if len(values) != len(header):
                raise BlockError(
                    "invalid_csv", "CSV row width differs from its header."
                )
            rows.append(
                {
                    name: None if value == config.null_value else value
                    for name, value in zip(header, values, strict=True)
                }
            )
            if (
                len(rows) > config.max_rows
                or len(rows) * len(header) > config.max_cells
            ):
                raise BlockError(
                    "table_limit", "Input exceeds the configured table limits."
                )
        return pl.DataFrame(rows, schema={name: pl.String for name in header}), None


class JsonSource(FileSource[JsonConfig]):
    config_model = JsonConfig
    suffix = ".json"
    descriptor = BlockDescriptor(
        **descriptor_values("source.json", "JSON Source", "source"),
        outputs=(TABLE_PORT,),
    )

    def _read(
        self, path: Path, config: JsonConfig
    ) -> tuple[pl.DataFrame, DataSchema | None]:
        data = path.read_bytes()
        if len(data) > config.max_bytes:
            raise BlockError("file_limit", "Input exceeds the configured byte limit.")
        rows = json.loads(data.decode(config.encoding), object_pairs_hook=unique_object)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("JSON requires an array of record objects")
        if len(rows) > config.max_rows:
            raise BlockError("table_limit", "Input exceeds the configured row limit.")
        if not rows:
            if not config.columns:
                raise BlockError(
                    "schema_required",
                    "An empty JSON array requires an explicit schema.",
                )
            return pl.DataFrame(
                schema={
                    n: POLARS_TYPES[t]
                    for n, t in zip(config.columns, config.types, strict=True)
                }
            ), config.declared_schema()
        names = list(rows[0])
        checked_names(names)
        if (
            not names
            or len(names) > config.max_columns
            or len(names) * len(rows) > config.max_cells
        ):
            raise BlockError(
                "table_limit", "Input exceeds the configured table limits."
            )
        columns = []
        for name in names:
            kind: DType
            values = [row[name] for row in rows if name in row]
            kinds = {type(value) for value in values if value is not None}
            if kinds <= {int, float} and kinds:
                kind = "number" if float in kinds else "integer"
            elif kinds <= {str}:
                kind = "string"
            elif kinds == {bool}:
                kind = "boolean"
            else:
                raise BlockError(
                    "unsupported_type", "JSON columns require consistent scalar types."
                )
            columns.append(Column(name=name, dtype=kind, nullable=None in values))
        table = Table(data_schema=DataSchema(columns=tuple(columns)), rows=tuple(rows))
        return to_frame(table), table.data_schema


class ParquetSource(FileSource[SourceConfig]):
    config_model = SourceConfig
    suffix = ".parquet"
    descriptor = BlockDescriptor(
        **descriptor_values("source.parquet", "Parquet Source", "source"),
        outputs=(TABLE_PORT,),
    )

    def _read(
        self, path: Path, config: SourceConfig
    ) -> tuple[pl.DataFrame, DataSchema | None]:
        arrow = pq.read_schema(path)
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
                raise BlockError(
                    "unsupported_type",
                    "Parquet contains an unsupported SDK column type.",
                )
            columns.append(Column(name=item.name, dtype=kind, nullable=item.nullable))
        if len(columns) > config.max_columns:
            raise BlockError(
                "table_limit", "Input exceeds the configured column limit."
            )
        return pl.read_parquet(
            path,
            n_rows=min(config.max_rows, config.max_cells // max(1, len(columns))) + 1,
        ), DataSchema(columns=tuple(columns))


class SinkConfig(ResourceConfig):
    overwrite: Literal["error", "replace"] = "error"
    null_value: str = Field(default="NULL", min_length=1, max_length=64)


ARTIFACT_SCHEMA = DataSchema(
    columns=(
        Column(name="location", dtype="string"),
        Column(name="format", dtype="string"),
        Column(name="row_count", dtype="integer"),
        Column(name="schema_json", dtype="string"),
    )
)
ARTIFACT_PORT = Port(name="artifact", data_schema=ARTIFACT_SCHEMA)


class FileSink(Block[SinkConfig]):
    config_model = SinkConfig
    suffix = ""

    def _write(self, path: Path, table: Table, config: SinkConfig) -> None:
        raise NotImplementedError

    def _execute(
        self, config: SinkConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        target = resource_path(context, config.resource_ref, self.suffix)
        table = inputs["table"][0]
        assert isinstance(table, Table)
        # Validate serializability and construct metadata before publication.
        to_frame(table)
        artifact = Table(
            data_schema=ARTIFACT_SCHEMA,
            rows=(
                {
                    "location": config.resource_ref,
                    "format": self.suffix[1:],
                    "row_count": len(table.rows),
                    "schema_json": table.data_schema.model_dump_json(),
                },
            ),
        )
        temporary: Path | None = None
        try:
            if target.exists() and config.overwrite == "error":
                raise BlockError(
                    "output_exists", "Output already exists; choose replace explicitly."
                )
            with NamedTemporaryFile(
                dir=target.parent, prefix=".lps-", suffix=".tmp", delete=False
            ) as stream:
                temporary = Path(stream.name)
            self._write(temporary, table, config)
            with temporary.open("r+b") as stream:
                os.fsync(stream.fileno())
            if config.overwrite == "replace":
                os.replace(temporary, target)
                temporary = None
            else:
                # Atomic no-clobber publication, including a destination race.
                os.link(temporary, target)
            return {"artifact": (artifact,)}
        except FileExistsError:
            raise BlockError(
                "output_exists", "Output already exists; choose replace explicitly."
            ) from None
        except BlockError:
            raise
        except Exception:
            raise BlockError(
                "write_failed", "Output could not be published atomically."
            ) from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


class CsvSink(FileSink):
    suffix = ".csv"
    descriptor = BlockDescriptor(
        **descriptor_values("sink.csv", "CSV Sink", "sink"),
        inputs=(TABLE_PORT,),
        outputs=(ARTIFACT_PORT,),
    )

    def _write(self, path: Path, table: Table, config: SinkConfig) -> None:
        if not table.data_schema.columns:
            raise BlockError(
                "schema_required", "CSV requires at least one declared column."
            )
        if any(
            value == config.null_value
            for row in table.rows
            for value in row.values()
            if isinstance(value, str)
        ):
            raise BlockError(
                "ambiguous_null",
                "A string equals the CSV null marker; choose a different marker.",
                field="null_value",
            )
        to_frame(table).write_csv(path, null_value=config.null_value)


class ParquetSink(FileSink):
    suffix = ".parquet"
    descriptor = BlockDescriptor(
        **descriptor_values("sink.parquet", "Parquet Sink", "sink"),
        inputs=(TABLE_PORT,),
        outputs=(ARTIFACT_PORT,),
    )

    def _write(self, path: Path, table: Table, config: SinkConfig) -> None:
        schema = pa.schema(
            [
                pa.field(c.name, ARROW_TYPES[c.dtype], nullable=c.nullable)
                for c in table.data_schema.columns
            ]
        )
        pq.write_table(pa.Table.from_pylist(list(table.rows), schema=schema), path)
