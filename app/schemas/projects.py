"""Public project contracts; names are display text, never workspace paths."""

from datetime import UTC, datetime
import unicodedata
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str = Field(min_length=1, max_length=128)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        if isinstance(value, str):
            if any(unicodedata.category(char) == "Cc" for char in value):
                raise ValueError("Project names cannot contain control characters")
            return value.strip()
        return value


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )


class ProjectPage(BaseModel):
    items: list[ProjectResponse]
    total: int
    offset: int
    limit: int
