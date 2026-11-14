# AI contribution: 50% or more AI-generated
"""Malformed definitions, schema mismatches and failure responses over the
real API, engine and SQLite metadata (#37).

These cases complement ``test_integration_matrix.py``: every response must
be a structured error envelope or a persisted, redacted failed run. Nothing
here may leak a workspace path, a credential or a traceback.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

import pytest

from app.preview import service as preview_service
from tests.integration_support import (
    READINGS_SCHEMA,
    Workbench,
    block_states,
    edge,
    graph,
    linear,
    node,
)

CSV_SINK = node("sink", "sink.csv", {"resource_ref": "result.csv"})


def csv(bench: Workbench, **overrides: Any) -> dict[str, Any]:
    config = {"resource_ref": bench.write_csv(), **READINGS_SCHEMA, **overrides}
    return node("source", "source.csv", config)


def failed_run(bench: Workbench, definition: dict[str, Any]) -> dict[str, Any]:
    """Execute a definition that validates but fails at runtime."""
    assert bench.validate(definition).json()["valid"]
    response = bench.execute(bench.save(definition))
    assert response.status_code == 201, response.text
    assert response.json()["state"] == "failed"
    return bench.run(response.json()["run_id"])


# -- malformed definitions ------------------------------------------------


@pytest.mark.parametrize(
    "definition",
    [
        {"schema_version": 2, "nodes": [], "edges": []},
        graph(
            [node("a", "transform.select"), node("b", "transform.select")],
            [edge("a", "b"), edge("b", "a")],
        ),
        graph([node("a", "source.csv")], [edge("a", "ghost")]),
        graph(
            [node("a", "source.sql", {"resource_ref": "x.sqlite3", "password": "p"})],
            [],
        ),
        graph([node("a", "source.csv"), node("a", "source.csv")], []),
    ],
    ids=[
        "schema-version",
        "cycle",
        "dangling-edge",
        "credential-key",
        "duplicate-node",
    ],
)
def test_malformed_definitions_are_refused_at_save_without_persistence(
    bench: Workbench, definition: dict[str, Any]
):
    response = bench.try_save(definition)
    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert "Traceback" not in response.text
    assert str(bench.root) not in response.text
    assert bench.client.get(bench.pipelines).json()["total"] == 0


def test_validate_reports_block_config_and_port_problems_without_running(
    bench: Workbench,
):
    draft = graph(
        [
            node("missing", "no.such.block"),
            node("old", "source.csv") | {"block_version": "0.0.1"},
            node("csv", "source.csv", {}),
            node("trigger", "trigger.manual"),
            node("gate", "quality.row_count"),
            CSV_SINK,
        ],
        [edge("trigger", "sink", source_port="signal")],
    )
    response = bench.validate(draft)
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["valid"] is False
    by_code = {d["code"]: d for d in report["diagnostics"]}
    assert by_code["block_unavailable"]["node_id"] == "missing"
    assert by_code["version_unavailable"]["node_id"] == "old"
    assert (
        by_code["missing_config"]["node_id"],
        by_code["missing_config"]["field"],
    ) == (
        "csv",
        "resource_ref",
    )
    assert by_code["incompatible_ports"]["edge_id"] == "trigger-sink-table"
    assert by_code["missing_input"]["node_id"] == "gate"
    for diagnostic in report["diagnostics"]:
        assert set(diagnostic) == {
            "code",
            "message",
            "node_id",
            "edge_id",
            "port",
            "field",
        }
    assert bench.runs()["total"] == 0


def test_saved_invalid_pipeline_cannot_execute_and_creates_no_run(bench: Workbench):
    # Saving accepts drafts that do not validate yet (#21); execute must not.
    pipeline_id = bench.save(linear(csv(bench, columns=["only"]), CSV_SINK))
    response = bench.execute(pipeline_id)
    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert (error["code"], error["node_context"]) == ("invalid_config", "source")
    assert bench.runs()["total"] == 0


# -- schema mismatches at runtime ----------------------------------------


def test_declared_csv_schema_that_disagrees_with_the_file_fails_the_source(
    bench: Workbench,
):
    source = csv(bench, columns=["name", "value", "flag"])
    detail = failed_run(bench, linear(source, CSV_SINK))
    assert detail["error"]["code"] == "schema_mismatch"
    assert block_states(detail) == {"source": "failed", "sink": "skipped"}
    assert detail["outputs"] == []
    assert not (bench.root / "result.csv").exists()


def test_sql_result_columns_must_match_the_declared_order(bench: Workbench):
    source = node(
        "source",
        "source.sql",
        {
            "resource_ref": bench.write_sqlite(),
            "columns": ["value", "name"],
            "types": ["integer", "string"],
            "nullable": [True, False],
            "query": "SELECT name, value FROM readings",
        },
    )
    detail = failed_run(bench, linear(source, CSV_SINK))
    assert detail["error"]["code"] == "schema_mismatch"
    assert detail["blocks"][0]["error"]["code"] == "schema_mismatch"


def test_downstream_type_contract_violations_fail_the_offending_block(
    bench: Workbench,
):
    cast = node("cast", "transform.cast", {"column": "name", "dtype": "integer"})
    detail = failed_run(bench, linear(csv(bench), cast, CSV_SINK))
    assert detail["error"]["code"] == "cast_failed"
    assert block_states(detail) == {
        "source": "completed",
        "cast": "failed",
        "sink": "skipped",
    }

    left = csv(bench)
    right = node(
        "right",
        "source.json",
        {"resource_ref": bench.write_json(name="inputs/right.json")},
    )
    to_text = node("text", "transform.cast", {"column": "value", "dtype": "string"})
    join = node("join", "transform.join", {"left_on": ["value"], "right_on": ["value"]})
    definition = graph(
        [left, right, to_text, join, CSV_SINK],
        [
            edge("source", "join", target_port="left"),
            edge("right", "text"),
            edge("text", "join", target_port="right"),
            edge("join", "sink"),
        ],
    )
    detail = failed_run(bench, definition)
    assert detail["error"]["code"] == "join_key_type_mismatch"
    assert block_states(detail)["sink"] == "skipped"


def test_strict_schema_gate_rejects_an_untyped_header_only_csv(bench: Workbench):
    untyped = node("source", "source.csv", {"resource_ref": bench.write_csv()})
    gate = node(
        "gate",
        "quality.schema_validation",
        {"columns": [{"name": "value", "dtype": "integer", "nullable": True}]},
    )
    detail = failed_run(bench, linear(untyped, gate, CSV_SINK))
    assert detail["error"]["code"] == "quality_failed"
    assert detail["blocks"][1]["error"]["code"] == "quality_failed"


# -- failure and timeout responses ---------------------------------------


def test_missing_input_file_fails_without_leaking_the_workspace_path(
    bench: Workbench,
):
    source = node("source", "source.csv", {"resource_ref": "inputs/absent.csv"})
    detail = failed_run(bench, linear(source, CSV_SINK))
    assert detail["error"]["code"] == "file_unavailable"
    text = bench.client.get(f"/api/v1/runs/{detail['id']}").text
    assert str(bench.root) not in text
    assert "absent.csv" not in text


def test_sql_work_budget_exhaustion_is_a_structured_query_failure(bench: Workbench):
    source = node(
        "source",
        "source.sql",
        {
            "resource_ref": bench.write_sqlite(),
            "columns": ["n"],
            "types": ["integer"],
            "nullable": [False],
            "max_steps": 1000,
            "query": (
                "WITH RECURSIVE seq(x) AS (SELECT 1 UNION ALL SELECT x + 1 "
                "FROM seq WHERE x < 500000) SELECT count(*) AS n FROM seq"
            ),
        },
    )
    detail = failed_run(bench, linear(source, CSV_SINK))
    assert detail["error"]["code"] == "sql_query_failed"
    assert block_states(detail) == {"source": "failed", "sink": "skipped"}


def test_execute_without_a_workspace_records_a_failed_run_not_a_crash(
    bench: Workbench, monkeypatch: pytest.MonkeyPatch
):
    from app.config import settings

    definition = linear(csv(bench), CSV_SINK)
    pipeline_id = bench.save(definition)
    monkeypatch.setattr(settings, "workspace_root", None)
    response = bench.execute(pipeline_id)
    assert response.status_code == 201, response.text
    detail = bench.run(response.json()["run_id"])
    assert detail["state"] == "failed"
    assert detail["error"]["code"] == "workspace_required"


def test_preview_time_budget_exhaustion_is_a_structured_timeout(
    bench: Workbench, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(preview_service, "MAX_SECONDS", 0.0)
    response = bench.preview(linear(csv(bench)), "source", max_rows=2, max_cells=6)
    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert (error["code"], error["node_context"]) == ("preview_timeout", "source")
    assert response.headers["cache-control"] == "no-store"


def test_preview_refuses_gates_sinks_and_unknown_projects_explicitly(
    bench: Workbench,
):
    gate = node("gate", "quality.row_count", {"min_rows": 1})
    definition = linear(csv(bench), gate, CSV_SINK)
    # Capability is checked along the whole input path, so selecting the sink
    # names the first unsupported ancestor (the gate), never the sink itself.
    for target, blamed in (("gate", "gate"), ("sink", "gate")):
        response = bench.preview(definition, target)
        assert response.status_code == 422, response.text
        assert response.json()["error"]["code"] == "preview_unsupported"
        assert response.json()["error"]["node_context"] == blamed
    missing = bench.client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/pipelines/preview",
        json={"definition": definition, "node_id": "source"},
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "project_not_found"


def test_preview_and_execute_agree_on_the_same_project_folder(bench: Workbench):
    """Preview and execute both resolve inputs under <workspace>/<project>."""
    definition = linear(csv(bench), CSV_SINK)
    preview = bench.preview(definition, "source", max_rows=10, max_cells=100)
    assert preview.status_code == 200, preview.text
    sample = preview.json()
    assert sample["full_row_count"] == 4
    assert sample["schema_scope"] == "declared"
    detail = bench.run_pipeline(definition)
    assert detail["state"] == "succeeded", detail["error"]
    assert detail["row_count"] == sample["full_row_count"]


# -- project-folder containment (PR #85 review) --------------------------


def alias_project_folder(bench: Workbench, target: Path) -> None:
    """Replace the project's data folder with a link to ``target``."""
    shutil.rmtree(bench.root)
    try:
        bench.root.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are unavailable on this runner")


def test_artifact_query_refuses_a_project_folder_that_aliases_another(
    bench: Workbench, tmp_path: Path
):
    """A link at <workspace>/<project> must not redirect reads elsewhere."""
    sink = node("sink", "sink.parquet", {"resource_ref": "result.parquet"})
    detail = bench.run_pipeline(linear(csv(bench), sink))
    artifact_id = detail["outputs"][0]["id"]
    assert bench.query(artifact_id, limit=5).status_code == 200
    published = (bench.root / "result.parquet").read_bytes()

    other = bench.client.post("/api/v1/projects", json={"name": "Other"}).json()
    other_root = bench.root.parent / other["id"]
    (other_root / "result.parquet").write_bytes(published)
    alias_project_folder(bench, other_root)
    aliased = bench.query(artifact_id, limit=5)
    assert aliased.status_code == 409, aliased.text
    assert aliased.json()["error"]["code"] == "artifact_unavailable"

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "result.parquet").write_bytes(published)
    bench.root.unlink()
    bench.root.symlink_to(outside, target_is_directory=True)
    escaped = bench.query(artifact_id, limit=5)
    assert escaped.status_code == 409, escaped.text
    assert escaped.json()["error"]["code"] == "artifact_unavailable"


@pytest.mark.parametrize("problem", ["aliased", "missing"])
def test_execute_refuses_an_unusable_project_folder_before_creating_a_run(
    bench: Workbench, tmp_path: Path, problem: str
):
    pipeline_id = bench.save(linear(csv(bench), CSV_SINK))
    elsewhere = tmp_path / "elsewhere"
    (elsewhere / "inputs").mkdir(parents=True)
    shutil.copy(bench.root / "inputs" / "readings.csv", elsewhere / "inputs")
    if problem == "aliased":
        alias_project_folder(bench, elsewhere)
    else:
        shutil.rmtree(bench.root)

    response = bench.execute(pipeline_id)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "workspace_project_folder"
    assert bench.runs()["total"] == 0
    assert not (elsewhere / "result.csv").exists()


def test_case_only_rename_of_the_project_folder_follows_the_filesystem_rule(
    bench: Workbench,
):
    """NTFS and default APFS ignore case: a case-only rename of the project
    folder still addresses the same directory, so preview, execute and the
    artifact query must keep working there. On a case-sensitive filesystem
    the original path no longer exists and the same calls must refuse."""
    sink = node(
        "sink",
        "sink.parquet",
        {"resource_ref": "result.parquet", "overwrite": "replace"},
    )
    definition = linear(csv(bench), sink)
    pipeline_id = bench.save(definition)
    first = bench.execute(pipeline_id)
    assert first.status_code == 201, first.text
    artifact_id = bench.run(first.json()["run_id"])["outputs"][0]["id"]

    renamed = bench.root.with_name(bench.root.name.swapcase())
    # Compare names, not paths: WindowsPath equality already ignores case.
    assert renamed.name != bench.root.name, "a UUID name always contains hex letters"
    os.rename(bench.root, renamed)
    insensitive = bench.root.exists() and os.path.samefile(bench.root, renamed)

    preview = bench.preview(definition, "source", max_rows=2, max_cells=6)
    again = bench.execute(pipeline_id)
    query = bench.query(artifact_id, limit=5)
    if insensitive:
        assert preview.status_code == 200, preview.text
        assert again.status_code == 201, again.text
        assert again.json()["state"] == "succeeded"
        assert query.status_code == 200, query.text
    else:
        assert preview.json()["error"]["code"] == "workspace_required"
        assert again.status_code == 422, again.text
        assert again.json()["error"]["code"] == "workspace_project_folder"
        assert query.status_code == 409, query.text
