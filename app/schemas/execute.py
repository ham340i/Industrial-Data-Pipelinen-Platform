# AI contribution: below 50% AI-generated
"""Execute and timer response contracts (#29)."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.runs import RunState


class ExecuteRequest(BaseModel):
    """Optionally guard execution against a newer saved revision (#33)."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int | None = Field(default=None, strict=True, ge=1)


class ExecuteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    state: RunState


class TimerStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    running: bool
    revision_id: str | None = None
    interval_seconds: int | None = None
