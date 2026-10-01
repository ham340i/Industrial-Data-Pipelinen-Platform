from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "Local Pipeline Studio API"
    api_version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


settings = Settings()
