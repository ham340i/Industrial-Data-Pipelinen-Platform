"""Shared backend test fixtures. Feature owners keep their own tests."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """API client that returns error responses instead of re-raising server errors."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
