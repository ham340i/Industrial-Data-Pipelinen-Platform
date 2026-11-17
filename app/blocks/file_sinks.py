# AI contribution: 50% or more AI-generated
"""Atomic, no-clobber-by-default file writers (#20).

Split from app/blocks/files.py so readers and writers stay separately
reviewable. Targets are confined to the workspace by the same
resource_path rule the readers use.
"""

from __future__ import annotations

import os
from abc import abstractmethod
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import Field

from app.blocks.base import Block
from app.blocks.context import BlockContext
from app.blocks.contracts import (
    BlockDescriptor,
    Column,
    DataSchema,
    Port,
    PortValues,
    Table,
)
from app.blocks.errors import BlockError
from app.blocks.files import ResourceConfig, resource_path
from app.blocks.tabular import TABLE_PORT, descriptor_values, to_frame

ARROW_TYPES = {
    "string": pa.string(),
    "integer": pa.int64(),
    "number": pa.float64(),
    "boolean": pa.bool_(),
}


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

    @abstractmethod
    def _write(self, path: Path, table: Table, config: SinkConfig) -> None:
        """Serialize ``table`` to the temporary ``path``; each format implements it."""

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
            # resource_path already proved target lies inside the project
            # workspace; only inputs/ is pre-created, so make output folders
            # such as outputs/ on demand instead of failing the publication.
            target.parent.mkdir(parents=True, exist_ok=True)
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
