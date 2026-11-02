# AI contribution: 50% or more AI-generated
"""Execute and timer response contracts (#29)."""

from pydantic import BaseModel, ConfigDict

from app.schemas.runs import RunState


class ExecuteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    state: RunState


class TimerStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    running: bool
    revision_id: str | None = None
    interval_seconds: int | None = None
