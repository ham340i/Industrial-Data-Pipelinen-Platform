from pydantic import BaseModel, Field


class ExampleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    count: int = Field(ge=1, le=1000)


class ExampleResponse(BaseModel):
    name: str
    count: int
