# AI contribution: 50% or more AI-generated
"""Shared API response fixtures: produced by the real backend, parsed by the
frontend guards (#37).

The JSON files under ``tests/fixtures/contracts`` are captured from the real
validate, execute, run-status and artifact endpoints. This module asserts the
live responses still have the recorded *shape* (keys and JSON types, not
values); ``frontend/src/api/contracts.test.ts`` feeds the same files through
the Builder's response parsers. A drift on either side fails CI.

Regenerate after an intentional contract change with
``LPS_UPDATE_CONTRACT_FIXTURES=1 python -m pytest tests/test_integration_contracts.py``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from tests.integration_support import (
    READINGS_SCHEMA,
    Workbench,
    edge,
    graph,
    linear,
    node,
)

FIXTURES = Path(__file__).parent / "fixtures" / "contracts"
UPDATE = os.environ.get("LPS_UPDATE_CONTRACT_FIXTURES") == "1"
PARQUET_SINK = node("sink", "sink.parquet", {"resource_ref": "outputs/result.parquet"})


def shape(value: Any) -> Any:
    """Keys and JSON types only; lists reduce to their distinct element shapes."""
    if isinstance(value, dict):
        return {key: shape(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return sorted({json.dumps(shape(item), sort_keys=True) for item in value})
    return type(value).__name__


def check(name: str, actual: Any) -> None:
    path = FIXTURES / f"{name}.json"
    if UPDATE:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n", "utf-8")
    recorded = json.loads(path.read_text(encoding="utf-8"))
    assert shape(actual) == shape(recorded), (
        f"{name} drifted from tests/fixtures/contracts/{name}.json; "
        "update the frontend parsers and regenerate the fixture together"
    )


def csv(bench: Workbench) -> dict[str, Any]:
    return node(
        "source", "source.csv", {"resource_ref": bench.write_csv(), **READINGS_SCHEMA}
    )


def test_succeeded_run_artifact_and_query_contracts(bench: Workbench):
    gate = node("gate", "transform.null_handling", {"policy": "drop"})
    definition = linear(csv(bench), gate, PARQUET_SINK)
    pipeline_id = bench.save(definition)
    executed = bench.execute(pipeline_id)
    assert executed.status_code == 201, executed.text
    check("execute-response", executed.json())

    detail = bench.run(executed.json()["run_id"])
    assert detail["state"] == "succeeded", detail["error"]
    check("run-detail-succeeded", detail)
    check("run-list", bench.runs(project_id=bench.project_id, pipeline_id=pipeline_id))

    (output,) = detail["outputs"]
    metadata = bench.artifact(output["id"])
    assert metadata.status_code == 200, metadata.text
    check("artifact-metadata", metadata.json())
    result = bench.query(output["id"], columns=["name", "value"], limit=2)
    assert result.status_code == 200, result.text
    check("artifact-query", result.json())


def test_failed_run_contract_carries_block_and_run_errors(bench: Workbench):
    gate = node("gate", "quality.null_check", {"columns": ["value"]})
    executed = bench.execute(bench.save(linear(csv(bench), gate, PARQUET_SINK)))
    assert executed.status_code == 201, executed.text
    detail = bench.run(executed.json()["run_id"])
    assert detail["state"] == "failed"
    assert detail["error"] and detail["blocks"][1]["error"]
    check("run-detail-failed", detail)


def test_validation_report_and_error_envelope_contracts(bench: Workbench):
    draft = graph(
        [
            node("missing", "no.such.block"),
            node("csv", "source.csv", {}),
            node("trigger", "trigger.manual"),
            node("gate", "quality.row_count"),
            PARQUET_SINK,
        ],
        [edge("trigger", "sink", source_port="signal")],
    )
    report = bench.validate(draft)
    assert report.status_code == 200, report.text
    assert report.json()["valid"] is False
    check("validation-report", report.json())

    refused = bench.execute(bench.save(draft))
    assert refused.status_code == 422, refused.text
    check("error-envelope", refused.json())


@pytest.mark.skipif(UPDATE, reason="fixtures are being regenerated")
def test_every_recorded_fixture_is_still_referenced():
    recorded = {path.stem for path in FIXTURES.glob("*.json")}
    source = Path(__file__).read_text(encoding="utf-8")
    assert recorded == {name for name in recorded if f'"{name}"' in source}
