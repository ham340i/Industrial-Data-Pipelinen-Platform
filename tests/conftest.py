"""Shared backend test fixtures. Feature owners keep their own tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """API client that returns error responses instead of re-raising server errors."""
    monkeypatch.setattr(settings, "metadata_path", tmp_path / "api.sqlite3")
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
