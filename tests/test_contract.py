"""Contract tests for the API shell: versioned routes, error envelope and CORS."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.schemas.errors import ErrorEnvelope

SECRET_DETAIL = "synthetic-internal-detail"


@pytest.fixture
def failing_route() -> Iterator[str]:
    """Temporarily register a route that raises, then restore the route table."""
    path = "/api/v1/_test/unhandled"
    original_routes = list(app.router.routes)

    async def raise_unhandled() -> None:
        raise RuntimeError(SECRET_DETAIL)

    app.add_api_route(path, raise_unhandled, methods=["GET"])
    try:
        yield path
    finally:
        app.router.routes[:] = original_routes


def test_openapi_schema_publishes_versioned_contract(client: TestClient):
    schema = client.get("/openapi.json").json()

    assert schema["info"]["version"] == settings.api_version
    assert "get" in schema["paths"]["/api/v1/health"]
    assert "post" in schema["paths"]["/api/v1/example"]
    assert all(path.startswith("/api/v1/") for path in schema["paths"])


def test_health_version_matches_published_api_version(client: TestClient):
    schema = client.get("/openapi.json").json()
    health = client.get("/api/v1/health").json()

    assert health["version"] == schema["info"]["version"]


@pytest.mark.parametrize(
    ("name", "count"),
    [("a", 1), ("a" * 100, 1000)],
)
def test_example_accepts_boundary_values(client: TestClient, name: str, count: int):
    response = client.post("/api/v1/example", json={"name": name, "count": count})

    assert response.status_code == 200
    assert response.json() == {"name": name, "count": count}


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "a" * 101, "count": 1},
        {"name": "sample", "count": 1001},
        {"name": "sample", "count": "many"},
        {"name": "sample"},
        {},
    ],
)
def test_example_rejects_out_of_contract_payloads(
    client: TestClient, payload: dict[str, object]
):
    response = client.post("/api/v1/example", json=payload)

    assert response.status_code == 422
    envelope = ErrorEnvelope.model_validate(response.json())
    assert envelope.error.code == "validation_error"


def test_malformed_json_returns_error_envelope(client: TestClient):
    response = client.post(
        "/api/v1/example",
        content=b'{"name": ',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    envelope = ErrorEnvelope.model_validate(response.json())
    assert envelope.error.code == "validation_error"


def test_error_envelope_and_header_share_supplied_correlation_id(client: TestClient):
    response = client.post(
        "/api/v1/example",
        json={"name": "", "count": 0},
        headers={"X-Correlation-ID": "contract-test-001"},
    )

    envelope = ErrorEnvelope.model_validate(response.json())
    assert envelope.error.correlation_id == "contract-test-001"
    # The header is currently emitted by both the middleware and the error
    # response, so compare the set of values rather than a single value.
    header_values = response.headers.get_list("x-correlation-id")
    assert set(header_values) == {"contract-test-001"}


def test_unhandled_error_returns_envelope_without_internal_detail(
    client: TestClient, failing_route: str
):
    response = client.get(failing_route)

    assert response.status_code == 500
    envelope = ErrorEnvelope.model_validate(response.json())
    assert envelope.error.code == "internal_error"
    assert SECRET_DETAIL not in response.text


def test_failing_route_fixture_restores_route_table(client: TestClient):
    assert client.get("/api/v1/_test/unhandled").status_code == 404


def test_cors_preflight_allows_configured_origin_only(client: TestClient):
    preflight = {"Access-Control-Request-Method": "POST"}
    allowed_origin = settings.allowed_origins[0]

    allowed = client.options(
        "/api/v1/example", headers={"Origin": allowed_origin, **preflight}
    )
    rejected = client.options(
        "/api/v1/example",
        headers={"Origin": "http://untrusted.example", **preflight},
    )

    assert allowed.headers["access-control-allow-origin"] == allowed_origin
    assert "access-control-allow-origin" not in rejected.headers
