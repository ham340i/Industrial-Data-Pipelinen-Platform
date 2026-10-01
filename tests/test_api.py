from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "local-pipeline-studio",
        "version": "0.1.0",
    }
    assert response.headers["x-correlation-id"]


def test_valid_example_request():
    response = client.post(
        "/api/v1/example",
        json={"name": "sample", "count": 2},
    )

    assert response.status_code == 200
    assert response.json() == {
        "name": "sample",
        "count": 2,
    }


def test_invalid_example_request_returns_structured_error():
    response = client.post(
        "/api/v1/example",
        json={"name": "", "count": 0},
    )

    assert response.status_code == 422

    body = response.json()

    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"]
    assert body["error"]["correlation_id"]
    assert body["error"]["node_context"] is None


def test_supplied_safe_correlation_id_is_preserved():
    response = client.get(
        "/api/v1/health",
        headers={"X-Correlation-ID": "local-test-001"},
    )

    assert response.status_code == 200
    assert response.headers["x-correlation-id"] == "local-test-001"


def test_unsafe_correlation_id_is_replaced():
    response = client.get(
        "/api/v1/health",
        headers={"X-Correlation-ID": "bad value with spaces"},
    )

    assert response.status_code == 200
    assert response.headers["x-correlation-id"] != "bad value with spaces"
    assert response.headers["x-correlation-id"]