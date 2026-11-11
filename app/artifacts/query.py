"""Bounded DuckDB reads over registered Parquet artifacts only."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.blocks.context import BlockContext
from app.blocks.contracts import DataSchema, Scalar
from app.blocks.errors import BlockError
from app.blocks.files import resource_path
from app.metadata.database import Database
from app.metadata.models import OutputEndpoint

MAX_COLUMNS = 100
MAX_LIMIT = 500
MAX_OFFSET = 1_000_000
MAX_CELLS = 50_100  # 100 columns * (500 requested rows + one look-ahead row)


class ArtifactNotFound(LookupError):
    pass


class ArtifactNotQueryable(ValueError):
    pass


class ArtifactUnavailable(RuntimeError):
    pass


class ArtifactQuery(BaseModel):
    """The complete public query policy; arbitrary SQL is intentionally absent."""

    model_config = ConfigDict(extra="forbid")

    columns: list[str] = Field(default_factory=list, max_length=MAX_COLUMNS)
    offset: int = Field(default=0, ge=0, le=MAX_OFFSET)
    limit: int = Field(default=100, ge=1, le=MAX_LIMIT)

    @field_validator("columns")
    @classmethod
    def valid_columns(cls, value: list[str]) -> list[str]:
        if any(not name.strip() or len(name) > 128 for name in value):
            raise ValueError("Column names must be nonblank and at most 128 characters")
        if len(set(value)) != len(value):
            raise ValueError("Columns must be unique")
        return value


@dataclass(frozen=True)
class ArtifactQueryResult:
    artifact_id: str
    run_id: str
    pipeline_revision_id: str
    columns: tuple[str, ...]
    rows: tuple[tuple[Scalar, ...], ...]
    offset: int
    limit: int
    has_more: bool


@dataclass(frozen=True)
class RegisteredArtifact:
    id: str
    run_id: str
    pipeline_revision_id: str
    pipeline_id: str
    project_id: str
    node_id: str
    name: str
    format: str
    artifact_ref: str
    row_count: int | None
    schema: DataSchema | None
    created_at: datetime


def get_artifact(db: Database, artifact_id: str) -> RegisteredArtifact:
    """Load a detached metadata snapshot; never resolve its local path here."""
    with db.transaction() as session:
        output = session.get(OutputEndpoint, artifact_id)
        if output is None:
            raise ArtifactNotFound()
        schema = None
        if output.schema_json:
            try:
                schema = DataSchema.model_validate_json(json.dumps(output.schema_json))
            except Exception:
                raise ArtifactNotQueryable(
                    "Registered artifact schema is invalid"
                ) from None
        revision = output.run.pipeline_revision
        return RegisteredArtifact(
            id=output.id,
            run_id=output.run_id,
            pipeline_revision_id=revision.id,
            pipeline_id=revision.pipeline_id,
            project_id=revision.pipeline.project_id,
            node_id=output.node_id,
            name=output.name,
            format=output.format,
            artifact_ref=output.artifact_ref,
            row_count=output.row_count,
            schema=schema,
            created_at=output.created_at,
        )


def _projection(schema: DataSchema, requested: list[str]) -> tuple[str, ...]:
    available = tuple(column.name for column in schema.columns)
    selected = tuple(requested) if requested else available
    if not selected:
        raise ArtifactNotQueryable("Artifact has no queryable columns")
    if len(selected) > MAX_COLUMNS:
        raise ArtifactNotQueryable("Select at most 100 columns")
    if any(name not in available for name in selected):
        raise ArtifactNotQueryable("A requested column is not registered")
    return selected


def _quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _scalar(value: object) -> Scalar:
    if value is None or type(value) in (str, int, bool):
        return value  # type: ignore[return-value]
    if type(value) is float and math.isfinite(value):
        return value
    raise ArtifactUnavailable("Artifact contains an unsupported result value")


def query_artifact(
    db: Database,
    artifact_id: str,
    workspace_root: Path,
    query: ArtifactQuery,
) -> ArtifactQueryResult:
    """Read a bounded projection without loading the full Parquet artifact."""
    # Keep the native query engine out of API startup and non-query processes.
    import duckdb

    artifact = get_artifact(db, artifact_id)
    if artifact.format != "parquet":
        raise ArtifactNotQueryable("Only registered Parquet artifacts are queryable")
    if artifact.schema is None:
        raise ArtifactNotQueryable("Artifact schema is not available")
    columns = _projection(artifact.schema, query.columns)
    if len(columns) * (query.limit + 1) > MAX_CELLS:
        raise ArtifactNotQueryable("Requested result exceeds the cell limit")
    try:
        path = resource_path(
            BlockContext(
                artifact.run_id, "artifact-query", workspace_root=workspace_root
            ),
            artifact.artifact_ref,
            ".parquet",
        )
        if not path.is_file():
            raise ArtifactUnavailable("Registered artifact is unavailable")
    except BlockError:
        raise ArtifactUnavailable("Registered artifact is unavailable") from None

    connection: Any = None
    try:
        connection = duckdb.connect(database=":memory:")
        connection.execute("SET threads = 1")
        connection.execute("SET memory_limit = '64MB'")
        connection.execute("SET preserve_insertion_order = false")
        projection = ", ".join(_quoted(name) for name in columns)
        cursor = connection.execute(
            f"SELECT {projection} FROM read_parquet(?) LIMIT ? OFFSET ?",
            [str(path), query.limit + 1, query.offset],
        )
        fetched = cursor.fetchall()
        rows = tuple(
            tuple(_scalar(value) for value in row) for row in fetched[: query.limit]
        )
        return ArtifactQueryResult(
            artifact_id=artifact.id,
            run_id=artifact.run_id,
            pipeline_revision_id=artifact.pipeline_revision_id,
            columns=columns,
            rows=rows,
            offset=query.offset,
            limit=query.limit,
            has_more=len(fetched) > query.limit,
        )
    except (ArtifactNotQueryable, ArtifactUnavailable):
        raise
    except Exception:
        raise ArtifactUnavailable("Registered artifact could not be queried") from None
    finally:
        if connection is not None:
            connection.close()
