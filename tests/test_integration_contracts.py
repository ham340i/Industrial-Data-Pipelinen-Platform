# AI contribution: 50% or more AI-generated
"""Shared API response fixtures: produced by the real backend, parsed by the
frontend guards (#37).

The JSON files under ``tests/fixtures/contracts`` are captured from the real
validate, execute, run-status and artifact endpoints. For every live
response this module asserts two things: the recorded *shape* (keys and
JSON types) is unchanged, and the parser-critical *values and relationships*
the Builder's ``parseRun`` / ``parseReport`` guards enforce still hold
(enumerations, identifier formats, ordering, cross-field rules). The same
files are parsed by ``frontend/src/api/contracts.test.ts``. A drift on either
side fails CI, including a same-type change such as ``level: "warn"``.

Regenerate after an intentional contract change with
``LPS_UPDATE_CONTRACT_FIXTURES=1 python -m pytest tests/test_integration_contracts.py``.
"""

from __future__ import annotations

import copy
import json
import os
import re
from collections.abc import Callable
from datetime import datetime
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

# Mirrors frontend/src/api/runs.ts, validation.ts and projects.ts. Keep the
# two in step: the frontend test parses the fixtures these rules accept.
RUN_STATES = {"queued", "running", "succeeded", "failed", "cancelled"}
BLOCK_STATES = {"queued", "running", "completed", "failed", "skipped"}
LEVELS = {"info", "warning", "error"}
IDENTIFIER = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
Rules = Callable[[Any], None]


def shape(value: Any) -> Any:
    """Keys and JSON types only; lists reduce to their distinct element shapes."""
    if isinstance(value, dict):
        return {key: shape(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return sorted({json.dumps(shape(item), sort_keys=True) for item in value})
    return type(value).__name__


def is_count(value: Any) -> bool:
    return type(value) is int and value >= 0


def is_measurement(value: Any) -> bool:
    return value is None or is_count(value)


def is_date(value: Any) -> bool:
    try:
        datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True


def is_failure(value: Any) -> bool:
    return value is None or (
        isinstance(value, dict)
        and isinstance(value.get("code"), str)
        and isinstance(value.get("reason"), str)
    )


def parsable_summary(run: Any) -> None:
    assert run["schema_version"] == 1
    for key in ("id", "project_id", "pipeline_id", "pipeline_revision_id"):
        assert IDENTIFIER.match(run[key]), key
    assert is_count(run["revision"]) and run["revision"] >= 1
    assert run["state"] in RUN_STATES, run["state"]
    assert is_date(run["created_at"])
    for key in ("started_at", "ended_at"):
        assert run[key] is None or is_date(run[key]), key
    assert is_measurement(run["duration_ms"]) and is_measurement(run["row_count"])
    assert is_failure(run["error"])


def parsable_run(run: Any) -> None:
    """Every rule parseRun applies to GET /runs/{id}."""
    parsable_summary(run)
    seen: set[str] = set()
    for block in run["blocks"]:
        assert isinstance(block["node_id"], str) and block["node_id"] not in seen
        seen.add(block["node_id"])
        assert isinstance(block["block_id"], str)
        assert isinstance(block["block_version"], str)
        assert is_count(block["position"])
        assert block["state"] in BLOCK_STATES, block["state"]
        for key in ("started_at", "ended_at"):
            assert block[key] is None or is_date(block[key]), key
        for key in ("duration_ms", "rows_in", "rows_out"):
            assert is_measurement(block[key]), key
        assert is_failure(block["error"])
    previous = -1
    for event in run["events"]:
        assert is_count(event["sequence"]) and event["sequence"] > previous
        previous = event["sequence"]
        assert is_date(event["created_at"])
        assert event["level"] in LEVELS, event["level"]
        assert event["node_id"] is None or isinstance(event["node_id"], str)
        assert isinstance(event["kind"], str)
        assert event["code"] is None or isinstance(event["code"], str)
        assert isinstance(event["message"], str)
    for output in run["outputs"]:
        for key in ("id", "name", "artifact_ref"):
            assert isinstance(output[key], str), key
        assert is_measurement(output["row_count"])


def parsable_run_list(page: Any) -> None:
    assert is_count(page["total"]) and is_count(page["offset"])
    assert is_count(page["limit"]) and len(page["items"]) <= page["limit"]
    for item in page["items"]:
        parsable_summary(item)
    assert len({item["id"] for item in page["items"]}) == len(page["items"])


def parsable_report(report: Any) -> None:
    """Every rule parseReport applies to POST /pipelines/validate."""
    assert isinstance(report["valid"], bool)
    assert report["valid"] == (len(report["diagnostics"]) == 0)
    for diagnostic in report["diagnostics"]:
        assert isinstance(diagnostic["code"], str)
        assert isinstance(diagnostic["message"], str) and diagnostic["message"].strip()
        for key in ("node_id", "edge_id", "port", "field"):
            assert diagnostic[key] is None or isinstance(diagnostic[key], str), key


def parsable_execute(response: Any) -> None:
    assert IDENTIFIER.match(response["run_id"]) and response["state"] in RUN_STATES


def parsable_error(envelope: Any) -> None:
    error = envelope["error"]
    assert isinstance(error["code"], str) and isinstance(error["message"], str)
    assert isinstance(error["correlation_id"], str)


def check(name: str, actual: Any, rules: Rules | None = None) -> None:
    """Live response keeps the recorded shape and satisfies the parser rules."""
    if rules is not None:
        rules(actual)
    path = FIXTURES / f"{name}.json"
    if UPDATE:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n", "utf-8")
    recorded = json.loads(path.read_text(encoding="utf-8"))
    assert shape(actual) == shape(recorded), (
        f"{name} drifted from tests/fixtures/contracts/{name}.json; "
        "update the frontend parsers and regenerate the fixture together"
    )
    if rules is not None:
        rules(recorded)


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
    check("execute-response", executed.json(), parsable_execute)

    detail = bench.run(executed.json()["run_id"])
    assert detail["state"] == "succeeded", detail["error"]
    check("run-detail-succeeded", detail, parsable_run)
    page = bench.runs(project_id=bench.project_id, pipeline_id=pipeline_id)
    check("run-list", page, parsable_run_list)

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
    check("run-detail-failed", detail, parsable_run)


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
    check("validation-report", report.json(), parsable_report)

    refused = bench.execute(bench.save(draft))
    assert refused.status_code == 422, refused.text
    check("error-envelope", refused.json(), parsable_error)


def mutate(name: str, apply: Callable[[Any], None]) -> Any:
    value = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    apply(value)
    return value


def set_level(value: Any) -> None:
    value["events"][0]["level"] = "warn"


def set_state(value: Any) -> None:
    value["blocks"][0]["state"] = "done"


def set_sequence(value: Any) -> None:
    value["events"][1]["sequence"] = value["events"][0]["sequence"]


def set_valid(value: Any) -> None:
    value["valid"] = True


@pytest.mark.parametrize(
    "name,apply,rules",
    [
        ("run-detail-succeeded", set_level, parsable_run),
        ("run-detail-failed", set_state, parsable_run),
        ("run-detail-succeeded", set_sequence, parsable_run),
        ("validation-report", set_valid, parsable_report),
    ],
    ids=["event-level", "block-state", "event-order", "valid-flag"],
)
def test_same_type_incompatible_changes_fail_the_bridge(
    name: str, apply: Callable[[Any], None], rules: Rules
):
    """A value the Builder's parser rejects must fail here even when its JSON
    type is unchanged, so a shape-only comparison cannot wave it through."""
    broken = mutate(name, apply)
    recorded = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    assert shape(broken) == shape(recorded), "the mutation must be same-type"
    rules(recorded)
    with pytest.raises(AssertionError):
        rules(copy.deepcopy(broken))


@pytest.mark.skipif(UPDATE, reason="fixtures are being regenerated")
def test_every_recorded_fixture_is_still_referenced():
    recorded = {path.stem for path in FIXTURES.glob("*.json")}
    source = Path(__file__).read_text(encoding="utf-8")
    assert recorded == {name for name in recorded if f'"{name}"' in source}
