"""Stable artifact metadata and bounded-query response contracts (#28)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.blocks.contracts import DataSchema, Scalar


class _Response(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ArtifactMetadataResponse(_Response):
    schema_version: Literal[1] = 1
    id: str
    run_id: str
    pipeline_revision_id: str
    pipeline_id: str
    project_id: str
    node_id: str
    name: str
    format: Literal["csv", "parquet"]
    resource_ref: str
    row_count: int | None
    data_schema: DataSchema | None
    created_at: datetime


class ArtifactQueryResponse(_Response):
    schema_version: Literal[1] = 1
    artifact_id: str
    run_id: str
    pipeline_revision_id: str
    columns: list[str]
    rows: list[list[Scalar]]
    offset: int
    limit: int
    has_more: bool
