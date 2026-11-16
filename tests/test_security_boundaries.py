# AI contribution: 50% or more AI-generated
"""Adversarial file, SQL and definition fixtures through the real API (#32).

Each case drives validate → save → execute (or preview) over a real project
workspace and asserts three things: the request is refused with a structured
code, nothing is read or written outside the project folder, and no response
or run record echoes a machine path. Unit-level traversal/symlink checks live
in tests/test_file_blocks.py; project-folder aliasing in
tests/test_integration_failures.py.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from tests.integration_support import (
    READINGS_SCHEMA,
    Workbench,
    block_states,
    csv_text,
    READINGS,
    linear,
    node,
)

CSV_SINK = node("sink", "sink.csv", {"resource_ref": "result.csv"})


def symlink(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except OSError:
        pytest.skip("Symlinks are unavailable on this filesystem")


def outside(tmp_path: Path) -> Path:
    folder = tmp_path / "outside"
    folder.mkdir(exist_ok=True)
    return folder


def csv_source(resource_ref: str, **overrides: Any) -> dict[str, Any]:
    return node(
        "source",
        "source.csv",
        {"resource_ref": resource_ref, **READINGS_SCHEMA, **overrides},
    )


def failed_run(bench: Workbench, definition: dict[str, Any]) -> dict[str, Any]:
    assert bench.validate(definition).json()["valid"]
    response = bench.execute(bench.save(definition))
    assert response.status_code == 201, response.text
    assert response.json()["state"] == "failed"
    return bench.run(response.json()["run_id"])


def assert_no_machine_paths(bench: Workbench, text: str, *paths: Path) -> None:
    for path in (bench.root, *paths):
        assert str(path) not in text
        assert str(path.resolve()) not in text


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# -- path confinement -----------------------------------------------------


@pytest.mark.parametrize(
    "resource_ref",
    [
        "../escape.csv",
        "inputs/../../escape.csv",
        "/etc/passwd.csv",
        "C:/Windows/escape.csv",
        "\\\\server\\share\\escape.csv",
        "~/escape.csv",
        "inputs/NUL.csv",
    ],
)
def test_traversal_and_machine_paths_are_refused_before_persistence(
    bench: Workbench, resource_ref: str
):
    definition = linear(csv_source(resource_ref), CSV_SINK)
    report = bench.validate(definition)
    # Machine paths fail the portable boundary (422); relative-looking
    # traversal reaches block validation and is reported invalid.
    if report.status_code == 422:
        assert report.json()["error"]["code"] == "validation_error"
    else:
        assert report.json()["valid"] is False
    assert_no_machine_paths(bench, report.text)
    response = bench.try_save(definition)
    if response.status_code == 201:
        # Relative-looking refs are stored, but can never execute.
        executed = bench.execute(response.json()["id"])
        assert executed.status_code == 422, executed.text
    else:
        assert response.status_code == 422, response.text
    assert_no_machine_paths(bench, response.text)


def test_symlinked_inputs_folder_cannot_read_outside_the_project(
    bench: Workbench, tmp_path: Path
):
    target = outside(tmp_path)
    (target / "readings.csv").write_text(csv_text(READINGS), encoding="utf-8")
    (bench.root / "inputs").rmdir()
    symlink(bench.root / "inputs", target)

    detail = failed_run(bench, linear(csv_source("inputs/readings.csv"), CSV_SINK))
    assert detail["error"]["code"] == "unsafe_resource"
    assert block_states(detail) == {"source": "failed", "sink": "skipped"}
    text = bench.client.get(f"/api/v1/runs/{detail['id']}").text
    assert_no_machine_paths(bench, text, target)
    assert not (bench.root / "result.csv").exists()


def test_symlinked_input_file_is_refused_by_preview_and_execute(
    bench: Workbench, tmp_path: Path
):
    secret = outside(tmp_path) / "plant-secret.csv"
    secret.write_text(csv_text(READINGS), encoding="utf-8")
    symlink(bench.root / "inputs" / "linked.csv", secret)
    definition = linear(csv_source("inputs/linked.csv"), CSV_SINK)

    preview = bench.preview(definition, "source")
    assert preview.json()["error"]["code"] == "unsafe_resource", preview.text
    assert "alpha" not in preview.text
    assert_no_machine_paths(bench, preview.text, secret)

    detail = failed_run(bench, definition)
    assert detail["error"]["code"] == "unsafe_resource"


def test_sink_cannot_write_through_a_symlinked_output_folder(
    bench: Workbench, tmp_path: Path
):
    target = outside(tmp_path)
    symlink(bench.root / "outputs", target)
    sink = node("sink", "sink.csv", {"resource_ref": "outputs/result.csv"})

    detail = failed_run(bench, linear(csv_source(bench.write_csv()), sink))
    assert detail["error"]["code"] == "unsafe_resource"
    assert list(target.iterdir()) == []


def test_sink_replace_cannot_overwrite_a_symlinked_target_file(
    bench: Workbench, tmp_path: Path
):
    victim = outside(tmp_path) / "victim.csv"
    victim.write_text("ORIGINAL\n", encoding="utf-8")
    symlink(bench.root / "result.csv", victim)
    sink = node(
        "sink", "sink.csv", {"resource_ref": "result.csv", "overwrite": "replace"}
    )

    detail = failed_run(bench, linear(csv_source(bench.write_csv()), sink))
    assert detail["error"]["code"] == "unsafe_resource"
    assert victim.read_text(encoding="utf-8") == "ORIGINAL\n"


# -- bounded inputs -------------------------------------------------------


def test_oversized_input_fails_with_a_limit_code(bench: Workbench):
    source = csv_source(bench.write_csv(), max_bytes=32)
    detail = failed_run(bench, linear(source, CSV_SINK))
    assert detail["error"]["code"] == "file_limit"


def test_malformed_input_fails_without_echoing_its_contents(bench: Workbench):
    (bench.root / "inputs" / "bad.csv").write_text(
        'name,value,active\n"PRIVATE_CELL,1,true\n', encoding="utf-8"
    )
    detail = failed_run(bench, linear(csv_source("inputs/bad.csv"), CSV_SINK))
    assert detail["error"]["code"] in {"invalid_csv", "invalid_file"}
    text = bench.client.get(f"/api/v1/runs/{detail['id']}").text
    assert "PRIVATE_CELL" not in text


# -- SQL misuse -----------------------------------------------------------


def sql_source(bench: Workbench, query: str, column: str = "n") -> dict[str, Any]:
    return node(
        "source",
        "source.sql",
        {
            "resource_ref": "inputs/readings.sqlite3",
            "columns": [column],
            "types": ["string"],
            "nullable": [True],
            "query": query,
        },
    )


@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM readings",
        "SELECT name AS n FROM readings; DROP TABLE readings",
        "ATTACH DATABASE 'copy.sqlite3' AS c",
        "WITH x AS (SELECT 1) UPDATE readings SET name = 'x'",
        "PRAGMA writable_schema = ON",
    ],
)
def test_sql_write_queries_are_refused_at_validation(bench: Workbench, query: str):
    database = bench.root / bench.write_sqlite()
    before = digest(database)
    report = bench.validate(linear(sql_source(bench, query), CSV_SINK))
    assert report.status_code == 200, report.text
    assert report.json()["valid"] is False
    assert digest(database) == before
    assert not (bench.root / "copy.sqlite3").exists()


@pytest.mark.parametrize(
    ("query", "column"),
    [
        # Passes the lexical policy; the SQLite authorizer must refuse it.
        # It would otherwise return the absolute database file path.
        ("SELECT file FROM pragma_database_list", "file"),
        ("SELECT name FROM pragma_table_info('readings')", "name"),
        ("SELECT load_extension('synthetic_missing') AS n", "n"),
    ],
)
def test_sql_introspection_and_extensions_are_refused_at_runtime(
    bench: Workbench, query: str, column: str
):
    database = bench.root / bench.write_sqlite()
    before = digest(database)
    detail = failed_run(bench, linear(sql_source(bench, query, column), CSV_SINK))
    assert detail["error"]["code"] == "sql_query_failed"
    text = bench.client.get(f"/api/v1/runs/{detail['id']}").text
    assert_no_machine_paths(bench, text, database)
    assert digest(database) == before
