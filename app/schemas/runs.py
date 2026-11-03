# AI contribution: 50% or more AI-generated
"""Stable, versioned run status/detail response contracts (#27)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

RunState = Literal["queued", "running", "succeeded", "failed", "cancelled"]
BlockState = Literal["queued", "running", "completed", "failed", "skipped"]


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class RunFailure(_Response):
    code: str
    reason: str


class RunBlockDetail(_Response):
    position: int
    node_id: str
    block_id: str
    block_version: str
    state: BlockState
    started_at: datetime | None
    ended_at: datetime | None
    duration_ms: int | None
    # None means unknown or not tabular; 0 is a real, measured count.
    rows_in: int | None
    rows_out: int | None
    error: RunFailure | None


class RunEventDetail(_Response):
    sequence: int
    created_at: datetime
    level: Literal["info", "warning", "error"]
    node_id: str | None
    kind: str
    code: str | None
    message: str


class RunOutputLink(_Response):
    id: str
    node_id: str
    name: str
    format: str
    artifact_ref: str
    row_count: int | None
    created_at: datetime


class RunSummary(_Response):
    schema_version: Literal[1] = 1
    id: str
    project_id: str
    pipeline_id: str
    pipeline_revision_id: str
    revision: int
    state: RunState
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None
    duration_ms: int | None
    row_count: int | None
    error: RunFailure | None


class RunDetail(RunSummary):
    blocks: list[RunBlockDetail]
    events: list[RunEventDetail]
    outputs: list[RunOutputLink]


class RunPage(_Response):
    items: list[RunSummary]
    total: int
    offset: int
    limit: int
