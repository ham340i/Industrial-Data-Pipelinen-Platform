"""Actual catalog → executor → filesystem tests for required quality gates."""

from pathlib import Path
from typing import Any

import pytest

from app.blocks.catalog import registry
from app.execution import Executor, Frame
from app.pipelines.models import Edge, Node, PipelineDefinition, PortReference


def pipeline(block: str, config: dict[str, Any]) -> PipelineDefinition:
    return PipelineDefinition(
        nodes=(
            Node(
                id="source",
                block_id="source.csv",
                block_version="1.0.0",
                config={
                    "resource_ref": "input.csv",
                    "columns": ["name", "value"],
                    "types": ["string", "integer"],
                    "nullable": [False, True],
                },
            ),
            Node(id="quality", block_id=block, block_version="1.0.0", config=config),
            Node(
                id="sink",
                block_id="sink.csv",
                block_version="1.0.0",
                config={
                    "resource_ref": "output.csv",
                    "overwrite": "replace",
                },
            ),
        ),
        edges=tuple(
            Edge(
                id=str(i),
                source=PortReference(node_id=source, port="table"),
                target=PortReference(node_id=target, port="table"),
            )
            for i, (source, target) in enumerate(
                [("source", "quality"), ("quality", "sink")]
            )
        ),
    )


@pytest.mark.parametrize(
    "block,config,content",
    [
        ("quality.null_check", {}, "name,value\na,NULL\n"),
        ("quality.row_count", {"min_rows": 2}, "name,value\na,1\n"),
        (
            "quality.schema_validation",
            {
                "columns": [
                    {"name": "name", "dtype": "integer"},
                    {"name": "value", "dtype": "integer", "nullable": True},
                ]
            },
            "name,value\na,1\n",
        ),
    ],
)
def test_required_failure_blocks_publication(
    tmp_path: Path, block: str, config: dict[str, Any], content: str
):
    (tmp_path / "input.csv").write_text(content)
    # No artifact may appear on initial failure. An existing file must survive too.
    for existing in (False, True):
        if existing:
            (tmp_path / "output.csv").write_text("previous successful artifact\n")
        result = Executor(registry).execute(
            pipeline(block, config), workspace_root=tmp_path
        )
        assert result.state == "failed"
        assert result.node_states == {
            "source": "completed",
            "quality": "failed",
            "sink": "skipped",
        }
        assert result.failures["quality"].code == "quality_failed"
        assert result.failures["quality"].diagnostics
        assert result.failures["sink"].code == "dependency_failed"
        assert "quality" not in result.outputs
        assert "sink" not in result.outputs
        assert not any(
            e.event == "succeeded" and e.node_id == "quality"
            for e in result.block_events
        )
        if existing:
            assert (
                tmp_path / "output.csv"
            ).read_text() == "previous successful artifact\n"
        else:
            assert not (tmp_path / "output.csv").exists()


@pytest.mark.parametrize(
    "block,config,expected",
    [
        ("quality.null_check", {"max_nulls": 1}, "name,value\na,NULL\nb,2\n"),
        ("quality.null_check", {"required": False}, "name,value\na,NULL\nb,2\n"),
        (
            "quality.row_count",
            {"min_rows": 2, "max_rows": 2},
            "name,value\na,NULL\nb,2\n",
        ),
        (
            "quality.schema_validation",
            {
                "columns": [
                    {"name": "name", "dtype": "string"},
                    {"name": "value", "dtype": "integer", "nullable": True},
                ]
            },
            "name,value\na,NULL\nb,2\n",
        ),
        ("transform.null_handling", {"policy": "drop"}, "name,value\nb,2\n"),
        (
            "transform.null_handling",
            {"policy": "fill", "columns": ["value"], "fill_values": {"value": 9}},
            "name,value\na,9\nb,2\n",
        ),
    ],
)
def test_valid_warning_and_null_policy_publish(
    tmp_path: Path, block: str, config: dict[str, Any], expected: str
):
    (tmp_path / "input.csv").write_text("name,value\na,NULL\nb,2\n")
    result = Executor(registry).execute(
        pipeline(block, config), workspace_root=tmp_path
    )
    assert result.state == "completed", result.failures
    assert (tmp_path / "output.csv").read_text() == expected
    artifact = result.outputs["sink"]["artifact"][0]
    assert isinstance(artifact, Frame)
    assert artifact.to_table().rows[0]["location"] == "output.csv"
    if config.get("required") is False:
        assert any(
            d.status == "warning" for e in result.block_events for d in e.diagnostics
        )
