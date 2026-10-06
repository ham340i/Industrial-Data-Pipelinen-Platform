import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "Local Pipeline Studio API"
    api_version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    metadata_path: Path = Field(
        default_factory=lambda: Path(
            os.environ.get("LPS_METADATA_PATH", "local-data/metadata.sqlite3")
        )
    )
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


settings = Settings()
