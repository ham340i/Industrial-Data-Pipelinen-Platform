# AI contribution: 50% or more AI-generated
"""Central logging configuration and request/error log content."""

import logging

from fastapi.testclient import TestClient

from app.logging_config import configure_logging
from app.main import app


def test_level_is_applied_to_the_application_logger():
    configure_logging("warning")
    try:
        assert logging.getLogger("app").level == logging.WARNING
    finally:
        configure_logging("INFO")


def test_unknown_level_falls_back_to_info():
    configure_logging("verbose")
    assert logging.getLogger("app").level == logging.INFO


def test_requests_are_logged_with_route_status_and_correlation_id(caplog):
    with caplog.at_level(logging.INFO, logger="app.main"), TestClient(app) as client:
        response = client.get(
            "/api/v1/health?token=do-not-log", headers={"X-Correlation-ID": "abc-123"}
        )
    assert response.status_code == 200
    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "GET /api/v1/health -> 200" in message and "[abc-123]" in message
        for message in messages
    )
    # Query strings can carry secrets; only the path is recorded.
    assert not any("do-not-log" in message for message in messages)


def test_refused_requests_log_the_error_code_not_the_payload(caplog):
    with caplog.at_level(logging.INFO, logger="app.main"), TestClient(app) as client:
        response = client.post("/api/v1/example", json={"name": "secret-value"})
    assert response.status_code == 422
    messages = [record.getMessage() for record in caplog.records]
    assert any("validation_error (422)" in message for message in messages)
    assert not any("secret-value" in message for message in messages)
