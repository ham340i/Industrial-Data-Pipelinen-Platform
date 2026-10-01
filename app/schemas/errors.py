from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    node_context: str | None = None


class ErrorEnvelope(BaseModel):
    error: ApiError
