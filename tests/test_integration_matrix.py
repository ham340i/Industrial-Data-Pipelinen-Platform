# AI contribution: 50% or more AI-generated
"""Source → transform → quality → sink compatibility through the real API (#37).

Each case saves a pipeline, validates it, executes it with the production
block catalog over a real workspace folder and SQLite metadata, then reads
the persisted run, its registered outputs and (for Parquet) the artifact
query path. Negative and failure-path cases live in
``test_integration_failures.py``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from tests.integration_support import (
    READINGS,
    READINGS_SCHEMA,
    Row,
    Workbench,
    block_states,
    edge,
    graph,
    linear,
    node,
)

SourceCase = Callable[[Workbench], tuple[dict[str, Any], list[list[Any]]]]


def csv_source(bench: Workbench) -> tuple[dict[str, Any], list[list[Any]]]:
    ref = bench.write_csv()
    config = {"resource_ref": ref, **READINGS_SCHEMA}
    return node("source", "source.csv", config), [list(r) for r in READINGS]


def json_source(bench: Workbench) -> tuple[dict[str, Any], list[list[Any]]]:
    ref = bench.write_json()
    return node("source", "source.json", {"resource_ref": ref}), [
        list(r) for r in READINGS
    ]


def parquet_source(bench: Workbench) -> tuple[dict[str, Any], list[list[Any]]]:
    ref = bench.write_parquet()
    return node("source", "source.parquet", {"resource_ref": ref}), [
        list(r) for r in READINGS
    ]


def sql_source(bench: Workbench) -> tuple[dict[str, Any], list[list[Any]]]:
    """SQLite has no boolean storage class: ``active`` is declared integer."""
    ref = bench.write_sqlite()
    config = {
        "resource_ref": ref,
        "columns": ["name", "value", "active"],
        "types": ["string", "integer", "integer"],
        "nullable": [False, True, False],
        "query": "SELECT name, value, active FROM readings ORDER BY rowid",
    }
    rows = [[n, v, int(a)] for n, v, a in READINGS]
    return node("source", "source.sql", config), rows


SOURCES: dict[str, SourceCase] = {
    "csv": csv_source,
    "json": json_source,
    "parquet": parquet_source,
    "sql": sql_source,
}
SINKS = {
    "csv": node("sink", "sink.csv", {"resource_ref": "result.csv"}),
    "parquet": node("sink", "sink.parquet", {"resource_ref": "result.parquet"}),
}


def published_rows(bench: Workbench, detail: dict[str, Any]) -> list[list[Any]]:
    """Read the sink's rows back the way an operator would: by artifact id."""
    (output,) = detail["outputs"]
    metadata = bench.artifact(output["id"])
    assert metadata.status_code == 200, metadata.text
    body = metadata.json()
    assert body["project_id"] == bench.project_id
    assert body["run_id"] == detail["id"]
    assert body["resource_ref"] == output["artifact_ref"]
    if body["format"] == "csv":
        unsupported = bench.query(output["id"], limit=10)
        assert unsupported.status_code == 422
        assert unsupported.json()["error"]["code"] == "artifact_not_queryable"
        text = (bench.root / output["artifact_ref"]).read_text(encoding="utf-8")
        lines = text.strip().splitlines()[1:]
        return [
            [
                None
                if cell == "NULL"
                else {"true": True, "false": False}.get(cell, cell)
                for cell in line.split(",")
            ]
            for line in lines
        ]
    result = bench.query(output["id"], limit=10)
    assert result.status_code == 200, result.text
    assert result.json()["has_more"] is False
    return [list(row) for row in result.json()["rows"]]


def numeric_strings(rows: list[list[Any]]) -> list[list[Any]]:
    """CSV round-trips lose integer typing; normalise digits for comparison."""
    return [
        [int(c) if isinstance(c, str) and c.lstrip("-").isdigit() else c for c in r]
        for r in rows
    ]


@pytest.mark.parametrize("sink_kind", sorted(SINKS))
@pytest.mark.parametrize("source_kind", sorted(SOURCES))
def test_every_source_publishes_through_every_sink(
    bench: Workbench, source_kind: str, sink_kind: str
):
    source, expected = SOURCES[source_kind](bench)
    detail = bench.run_pipeline(linear(source, SINKS[sink_kind]))

    assert detail["state"] == "succeeded", detail["error"]
    assert block_states(detail) == {"source": "completed", "sink": "completed"}
    source_block, sink_block = detail["blocks"]
    assert (source_block["rows_in"], source_block["rows_out"]) == (0, len(expected))
    assert sink_block["rows_in"] == len(expected)
    assert detail["row_count"] == len(expected)
    assert [o["node_id"] for o in detail["outputs"]] == ["sink"]
    assert detail["outputs"][0]["row_count"] == len(expected)
    assert numeric_strings(published_rows(bench, detail)) == expected


def test_select_rename_filter_cast_sort_chain_publishes_typed_rows(
    bench: Workbench,
):
    source, _ = csv_source(bench)
    chain = linear(
        source,
        node("select", "transform.select", {"columns": ["name", "value"]}),
        node(
            "rename",
            "transform.rename",
            {"columns": ["value"], "names": ["reading"]},
        ),
        node(
            "filter",
            "transform.filter",
            {"column": "reading", "operator": "is_not_null"},
        ),
        node("cast", "transform.cast", {"column": "reading", "dtype": "number"}),
        node(
            "sort",
            "transform.sort",
            {"columns": [{"column": "reading", "descending": True}]},
        ),
        SINKS["parquet"],
    )
    detail = bench.run_pipeline(chain)

    assert detail["state"] == "succeeded", detail["error"]
    assert set(block_states(detail).values()) == {"completed"}
    rows_out = {b["node_id"]: b["rows_out"] for b in detail["blocks"]}
    assert rows_out["select"] == 4 and rows_out["filter"] == 3
    assert detail["row_count"] == 3
    assert published_rows(bench, detail) == [
        ["delta", 4.0],
        ["gamma", 3.0],
        ["alpha", 1.0],
    ]
    metadata = bench.artifact(detail["outputs"][0]["id"]).json()
    assert metadata["data_schema"]["columns"] == [
        {"name": "name", "dtype": "string", "nullable": False},
        {"name": "reading", "dtype": "number", "nullable": True},
    ]


def test_two_sources_fan_in_through_join_and_aggregate(bench: Workbench):
    readings, _ = csv_source(bench)
    limits: tuple[Row, ...] = (("alpha", 2, True), ("gamma", 2, True))
    thresholds = node(
        "thresholds",
        "source.json",
        {"resource_ref": bench.write_json(limits, "inputs/limits.json")},
    )
    thresholds_select = node(
        "limit", "transform.select", {"columns": ["name", "value"]}
    )
    rename = node(
        "as_limit", "transform.rename", {"columns": ["value"], "names": ["limit"]}
    )
    join = node(
        "join",
        "transform.join",
        {"left_on": ["name"], "right_on": ["name"], "how": "inner"},
    )
    aggregate = node(
        "aggregate",
        "transform.aggregate",
        {
            "group_by": ["active"],
            "operations": [
                {"column": "name", "function": "count", "output_name": "n"},
                {"column": "value", "function": "sum", "output_name": "total"},
            ],
        },
    )
    definition = graph(
        [
            readings,
            thresholds,
            thresholds_select,
            rename,
            join,
            aggregate,
            SINKS["parquet"],
        ],
        [
            edge("source", "join", target_port="left"),
            edge("thresholds", "limit"),
            edge("limit", "as_limit"),
            edge("as_limit", "join", target_port="right"),
            edge("join", "aggregate"),
            edge("aggregate", "sink"),
        ],
    )
    detail = bench.run_pipeline(definition)

    assert detail["state"] == "succeeded", detail["error"]
    assert set(block_states(detail).values()) == {"completed"}
    join_block = next(b for b in detail["blocks"] if b["node_id"] == "join")
    assert (join_block["rows_in"], join_block["rows_out"]) == (6, 2)
    assert published_rows(bench, detail) == [[True, 2, 4]]


@pytest.mark.parametrize(
    "gate,config",
    [
        (
            "quality.schema_validation",
            {
                "columns": [
                    {"name": "name", "dtype": "string"},
                    {"name": "value", "dtype": "integer", "nullable": True},
                    {"name": "active", "dtype": "boolean"},
                ]
            },
        ),
        ("quality.null_check", {"columns": ["name", "active"]}),
        ("quality.row_count", {"min_rows": 4, "max_rows": 4}),
        ("transform.null_handling", {"policy": "drop"}),
    ],
)
def test_passing_quality_gates_keep_the_run_publishing(
    bench: Workbench, gate: str, config: dict[str, Any]
):
    source, expected = parquet_source(bench)
    detail = bench.run_pipeline(
        linear(source, node("gate", gate, config), SINKS["csv"])
    )

    assert detail["state"] == "succeeded", detail["error"]
    assert block_states(detail) == {
        "source": "completed",
        "gate": "completed",
        "sink": "completed",
    }
    kept = [
        r for r in expected if gate != "transform.null_handling" or r[1] is not None
    ]
    assert numeric_strings(published_rows(bench, detail)) == kept
    quality_events = [e for e in detail["events"] if e["kind"] == "block"]
    assert any(
        e["node_id"] == "gate" and "quality" in e["message"] for e in quality_events
    )


def test_required_gate_failure_blocks_publication_and_registers_nothing(
    bench: Workbench,
):
    source, _ = csv_source(bench)
    gate = node("gate", "quality.null_check", {"columns": ["value"]})
    detail = bench.run_pipeline(linear(source, gate, SINKS["parquet"]))

    assert detail["state"] == "failed"
    assert detail["error"]["code"] == "quality_failed"
    assert block_states(detail) == {
        "source": "completed",
        "gate": "failed",
        "sink": "skipped",
    }
    sink = detail["blocks"][2]
    assert sink["error"]["code"] == "dependency_failed"
    assert detail["outputs"] == [] and detail["row_count"] is None
    assert not (bench.root / "result.parquet").exists()


def test_optional_gate_warns_and_still_publishes(bench: Workbench):
    source, expected = csv_source(bench)
    gate = node("gate", "quality.null_check", {"columns": ["value"], "required": False})
    detail = bench.run_pipeline(linear(source, gate, SINKS["parquet"]))

    assert detail["state"] == "succeeded", detail["error"]
    assert detail["row_count"] == len(expected)
    assert published_rows(bench, detail) == expected


def test_run_status_paths_list_filter_and_scope_the_matrix_runs(bench: Workbench):
    source, _ = csv_source(bench)
    # The default no-clobber sink would fail a second run with output_exists.
    sink = node(
        "sink", "sink.csv", {"resource_ref": "result.csv", "overwrite": "replace"}
    )
    good = bench.save(linear(source, sink), "good")
    bad = bench.save(
        linear(source, node("gate", "quality.row_count", {"min_rows": 99}), sink),
        "bad",
    )
    ids = [bench.execute(p).json()["run_id"] for p in (good, good, bad)]

    everything = bench.runs(project_id=bench.project_id)
    assert everything["total"] == 3
    assert [item["id"] for item in everything["items"]] == ids[::-1]
    failed = bench.runs(pipeline_id=bad, state="failed")
    assert [item["id"] for item in failed["items"]] == [ids[2]]
    assert failed["items"][0]["error"]["code"] == "quality_failed"
    scoped = bench.runs(pipeline_id=good, state="succeeded")
    assert {item["id"] for item in scoped["items"]} == set(ids[:2])
    assert bench.runs(project_id=bench.project_id, state="cancelled")["total"] == 0
    detail = bench.run(ids[2])
    sequences = [event["sequence"] for event in detail["events"]]
    assert sequences == sorted(sequences) and len(set(sequences)) == len(sequences)


def test_sink_creates_a_missing_output_folder_inside_the_project(bench: Workbench):
    """Only inputs/ is prepared; outputs/<file> must still publish (#37)."""
    source, expected = csv_source(bench)
    sink = node(
        "sink", "sink.parquet", {"resource_ref": "outputs/nested/result.parquet"}
    )
    detail = bench.run_pipeline(linear(source, sink))

    assert detail["state"] == "succeeded", detail["error"]
    assert (bench.root / "outputs" / "nested" / "result.parquet").is_file()
    assert detail["outputs"][0]["artifact_ref"] == "outputs/nested/result.parquet"
    assert published_rows(bench, detail) == expected
