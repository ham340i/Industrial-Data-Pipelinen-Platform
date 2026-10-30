"""Public metadata discovery for the #15 block library."""

from fastapi.testclient import TestClient

from app.blocks.catalog import registry
from app.blocks.contracts import BlockMetadata


def test_catalog_matches_registered_public_contract(client: TestClient):
    response = client.get("/api/v1/blocks")
    assert response.status_code == 200
    assert response.json() == registry.public_metadata()
    for item in response.json():
        metadata = BlockMetadata.from_public(item)
        assert metadata.sdk_version == 1
        assert metadata.config_schema
    assert response.headers["x-correlation-id"]
