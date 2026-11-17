# AI contribution: below 50% AI-generated
"""Shared backend test fixtures. Feature owners keep their own tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from tests.integration_support import Workbench, build_workbench


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """API client that returns error responses instead of re-raising server errors."""
    monkeypatch.setattr(settings, "metadata_path", tmp_path / "api.sqlite3")
    monkeypatch.setattr(settings, "workspace_root", tmp_path / "workspace")
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def bench(client: TestClient, tmp_path: Path) -> Workbench:
    """A project whose workspace folder exists, for API-level integration (#37)."""
    return build_workbench(client, tmp_path / "workspace")
