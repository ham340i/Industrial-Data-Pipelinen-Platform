"""Public discovery and library visibility preserve saved-pipeline contracts."""

from fastapi.testclient import TestClient

from app.blocks import BlockContext, BlockDescriptor, PortValues, PreviewLimits, Table
from app.blocks.catalog import registry
from app.blocks.contracts import BlockMetadata
from app.blocks.sample import VALUE_SCHEMA


def test_catalog_matches_registered_public_contract(client: TestClient):
    response = client.get("/api/v1/blocks")
    assert response.status_code == 200
    blocks = response.json()
    assert blocks == registry.public_metadata()
    for item in blocks:
        metadata = BlockMetadata.from_public(item)
        assert metadata.sdk_version == 1
        assert metadata.config_schema
    assert response.headers["x-correlation-id"]
    hidden = [block for block in blocks if not block["library_visible"]]
    assert [block["block_id"] for block in hidden] == ["synthetic.add_constant"]
    example = hidden[0]
    assert example["version"] == "1.0.0"
    assert example["inputs"][0]["name"] == "table"
    assert "amount" in example["config_schema"]["properties"]
    assert any(block["block_id"] == "quality.row_count" for block in blocks)
    sources = [
        block
        for block in blocks
        if block["block_id"] in {"source.csv", "source.json", "source.parquet"}
    ]
    assert len(sources) == 3
    assert all(
        block["supports_preview"] and block["preview_reason"] is None
        for block in sources
    )


def test_hidden_example_still_validates_executes_and_previews():
    block = registry.resolve("synthetic.add_constant", "1.0.0")
    inputs: PortValues = {
        "table": (Table(data_schema=VALUE_SCHEMA, rows=({"value": 2},)),)
    }
    config, checked = block.validate({"amount": 3}, inputs)
    context = BlockContext("existing-pipeline", "saved-node")
    result = block.run(config.model_dump(), checked, context)
    output = result["table"][0]
    assert isinstance(output, Table)
    assert output.rows == ({"value": 5},)
    preview = block.preview({}, inputs, context, PreviewLimits(max_rows=1))["table"][0]
    assert isinstance(preview, Table)
    assert preview.rows == ({"value": 3},)


def test_older_descriptors_default_to_visible():
    descriptor = registry.resolve("quality.row_count", "1.0.0").descriptor
    older = descriptor.model_dump(exclude={"library_visible"})
    assert BlockDescriptor.model_validate(older).library_visible is True
