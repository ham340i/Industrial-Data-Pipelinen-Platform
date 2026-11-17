# AI contribution: 50% or more AI-generated
"""Workspace-bound file readers (#16). Sinks live in ``app.blocks.sinks``."""

from __future__ import annotations

import csv
import io
import json
from abc import abstractmethod
from pathlib import Path
from typing import Any

import polars as pl
import pyarrow.parquet as pq

from app.blocks.base import Block
from app.blocks.context import BlockContext
from app.blocks.contracts import (
    BlockDescriptor,
    Column,
    DataSchema,
    PortValues,
    PreviewLimits,
    Table,
)
from app.blocks.csv_preview import preview_csv
from app.blocks.errors import BlockError
from app.blocks.file_preview import preview_json
from app.blocks.inference import arrow_dtype, scalar_dtype
from app.blocks.parquet_preview import preview_parquet
from app.blocks.resources import (
    CsvConfig,
    JsonConfig,
    SourceConfig,
    check_source_file,
    resource_path,
    unique_object,
)
from app.blocks.tabular import (
    POLARS_TYPES,
    TABLE_PORT,
    cast_column,
    checked_names,
    descriptor_values,
    from_frame,
    to_frame,
)


class FileSource[SourceT: SourceConfig](Block[SourceT]):
    suffix = ""

    @abstractmethod
    def _read(
        self, path: Path, config: SourceT
    ) -> tuple[pl.DataFrame, DataSchema | None]:
        """Read ``path`` into a frame, with its schema when the format has one."""

    def _execute(
        self, config: SourceT, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        path = resource_path(context, config.resource_ref, self.suffix)
        try:
            check_source_file(path, config.max_bytes)
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
        **descriptor_values("source.csv", "CSV Source", "source"),
        outputs=(TABLE_PORT,),
        supports_preview=True,
        preview_reason=None,
    )

    def _preview(
        self,
        config: CsvConfig,
        inputs: PortValues,
        context: BlockContext,
        limits: PreviewLimits,
    ) -> PortValues:
        return preview_csv(config, context, limits)

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
        supports_preview=True,
        preview_reason=None,
    )

    def _preview(
        self,
        config: JsonConfig,
        inputs: PortValues,
        context: BlockContext,
        limits: PreviewLimits,
    ) -> PortValues:
        return preview_json(config, context, limits)

    @staticmethod
    def _records(path: Path, config: JsonConfig) -> list[dict[str, Any]]:
        data = path.read_bytes()
        if len(data) > config.max_bytes:
            raise BlockError("file_limit", "Input exceeds the configured byte limit.")
        rows = json.loads(data.decode(config.encoding), object_pairs_hook=unique_object)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("JSON requires an array of record objects")
        if len(rows) > config.max_rows:
            raise BlockError("table_limit", "Input exceeds the configured row limit.")
        return rows

    @staticmethod
    def _inferred_schema(rows: list[dict[str, Any]], names: list[str]) -> DataSchema:
        columns = []
        for name in names:
            values = [row[name] for row in rows if name in row]
            kinds = {type(value) for value in values if value is not None}
            # An all-null column is carried as a nullable string.
            kind = scalar_dtype(kinds) if kinds else "string"
            if kind is None:
                raise BlockError(
                    "unsupported_type", "JSON columns require consistent scalar types."
                )
            columns.append(Column(name=name, dtype=kind, nullable=None in values))
        return DataSchema(columns=tuple(columns))

    def _read(
        self, path: Path, config: JsonConfig
    ) -> tuple[pl.DataFrame, DataSchema | None]:
        rows = self._records(path, config)
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
        table = Table(data_schema=self._inferred_schema(rows, names), rows=tuple(rows))
        return to_frame(table), table.data_schema


class ParquetSource(FileSource[SourceConfig]):
    config_model = SourceConfig
    suffix = ".parquet"
    descriptor = BlockDescriptor(
        **descriptor_values("source.parquet", "Parquet Source", "source"),
        outputs=(TABLE_PORT,),
        supports_preview=True,
        preview_reason=None,
    )

    def _preview(
        self,
        config: SourceConfig,
        inputs: PortValues,
        context: BlockContext,
        limits: PreviewLimits,
    ) -> PortValues:
        return preview_parquet(config, context, limits)

    def _read(
        self, path: Path, config: SourceConfig
    ) -> tuple[pl.DataFrame, DataSchema | None]:
        columns = []
        for item in pq.read_schema(path):
            kind = arrow_dtype(item.type)
            if kind is None:
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
