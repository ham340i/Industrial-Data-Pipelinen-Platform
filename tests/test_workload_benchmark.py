# AI contribution: 50% or more AI-generated
"""Independent fixture/oracle and real service benchmark checks (#35)."""

import csv
import json
from pathlib import Path
import platform

import pytest

from app.pipelines.models import PipelineDefinition
from experiments.workloads.benchmark import expected, fact, fixtures, graph, worker


def test_fixtures_are_repeatable_and_have_nulls_and_duplicate_keys(tmp_path: Path):
    first = fixtures(tmp_path, 100, 4)
    assert fixtures(tmp_path, 100, 4) == first
    with (tmp_path / "facts.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 100
    assert rows[0]["value"] == "NULL"
    assert rows[1]["value"] == "1"
    assert rows[0]["key"] == rows[32]["key"]
    assert len(rows[0]) == 6


def test_oracle_counts_nonnull_values_and_preserves_zero():
    assert expected(0) == []
    assert expected(2) == [
        {"segment": "segment-1", "total": 1, "count": 1},
        {"segment": "segment-0", "total": 0, "count": 0},
    ]
    assert fact(17, 0)["value"] == 0
    assert sum(row["count"] for row in expected(100)) == 90


@pytest.mark.parametrize("variant", ["baseline", "projected"])
def test_benchmark_graph_is_valid_and_resolves_real_blocks(variant: str):
    from app.blocks.catalog import registry

    definition = PipelineDefinition.from_json(json.dumps(graph(8, variant)))
    assert definition.validate_registry(registry)


@pytest.mark.skipif(platform.system() != "Linux", reason="Linux peak RSS units")
@pytest.mark.parametrize("variant", ["baseline", "projected"])
def test_real_pipeline_artifact_query_and_preview_match_oracles(variant: str):
    result = worker("small", variant)
    assert result["correctness"] == "passed"
    assert result["preview_rows"] == 25
    assert result["execution_seconds"] > 0
    assert result["peak_process_rss_mib"] > 0
    assert len(result["query_repeat_seconds"]) == 2


@pytest.mark.skipif(platform.system() != "Linux", reason="Linux benchmark worker")
@pytest.mark.parametrize(
    "failure,code", [("source", "table_limit"), ("executor", "data_limit")]
)
def test_budget_failures_do_not_publish_artifacts(failure: str, code: str):
    result = worker("small", "baseline", failure)
    assert result["state"] == "failed"
    assert code in result["codes"]
