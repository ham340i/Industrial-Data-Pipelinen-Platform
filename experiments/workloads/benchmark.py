# AI contribution: 50% or more AI-generated
"""Repeatable service-level ETL benchmark. Reports JSON on stdout only (#35)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
from threading import Event
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CASES = {"small": (100, 4), "medium": (1000, 8), "wide": (3000, 24)}
VARIANTS = ("baseline", "projected")


def fact(index: int, width: int) -> dict[str, Any]:
    return {
        "key": index % 32,
        "value": None if index % 11 == 0 else index % 17,
        **{f"unused_{n}": index + n for n in range(width)},
    }


def fixtures(root: Path, rows: int, width: int) -> dict[str, str]:
    """Stream deterministic, duplicate-key/null-bearing inputs to local CSVs."""
    with (root / "facts.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fact(0, width)))
        writer.writeheader()
        for index in range(rows):
            row = fact(index, width)
            writer.writerow({k: "NULL" if v is None else v for k, v in row.items()})
    with (root / "dimension.csv").open("w", newline="", encoding="utf-8") as stream:
        dimension_writer = csv.writer(stream)
        dimension_writer.writerow(["key", "segment"])
        dimension_writer.writerows((key, f"segment-{key % 8}") for key in range(32))
    return {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ("facts.csv", "dimension.csv")
    }


def expected(rows: int) -> list[dict[str, Any]]:
    """Independent Python oracle; no Polars/Arrow/query code is reused."""
    groups: dict[str, dict[str, Any]] = {}
    for index in range(rows):
        segment = f"segment-{(index % 32) % 8}"
        group = groups.setdefault(segment, {"segment": segment, "total": 0, "count": 0})
        if index % 11:
            group["total"] += index % 17
            group["count"] += 1
    return sorted(groups.values(), key=lambda row: (-row["total"], row["segment"]))


def node(identity: str, block: str, config: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": identity,
        "block_id": block,
        "block_version": "1.0.0",
        "config": config,
    }


def edge(source: str, target: str, port: str = "table") -> dict[str, Any]:
    return {
        "id": f"{source}-{target}",
        "source": {"node_id": source, "port": "table"},
        "target": {"node_id": target, "port": port},
    }


def graph(width: int, variant: str, source_limit: int = 100000) -> dict[str, Any]:
    if variant not in VARIANTS:
        raise ValueError("Unknown benchmark variant")
    names = list(fact(0, width))
    nodes = [
        node(
            "facts",
            "source.csv",
            {
                "resource_ref": "facts.csv",
                "columns": names,
                "types": ["integer"] * len(names),
                "nullable": [False, True] + [False] * width,
                "max_rows": source_limit,
            },
        ),
        node(
            "dimension",
            "source.csv",
            {
                "resource_ref": "dimension.csv",
                "columns": ["key", "segment"],
                "types": ["integer", "string"],
                "nullable": [False, False],
            },
        ),
        node(
            "join",
            "transform.join",
            {
                "left_on": ["key"],
                "right_on": ["key"],
                "how": "inner",
                "cardinality": "many_to_one",
            },
        ),
        node(
            "aggregate",
            "transform.aggregate",
            {
                "group_by": ["segment"],
                "operations": [
                    {"column": "value", "function": "sum", "output_name": "total"},
                    {"column": "value", "function": "count", "output_name": "count"},
                ],
            },
        ),
        node(
            "sort",
            "transform.sort",
            {
                "columns": [
                    {"column": "total", "descending": True},
                    {"column": "segment"},
                ]
            },
        ),
        node("sink", "sink.parquet", {"resource_ref": "result.parquet"}),
    ]
    edges = [
        edge("dimension", "join", "right"),
        edge("join", "aggregate"),
        edge("aggregate", "sort"),
        edge("sort", "sink"),
    ]
    if variant == "projected":
        nodes.append(node("project", "transform.select", {"columns": ["key", "value"]}))
        edges.extend([edge("facts", "project"), edge("project", "join", "left")])
    else:
        edges.append(edge("facts", "join", "left"))
    return {"schema_version": 1, "nodes": nodes, "edges": edges}


def timed(operation: Any) -> tuple[Any, float]:
    started = perf_counter()
    result = operation()
    return result, perf_counter() - started


def worker(case: str, variant: str, failure: str | None = None) -> dict[str, Any]:
    # Imports stay in each fresh worker, including DuckDB's first-query startup.
    import resource
    import pyarrow.parquet as pq
    from sqlalchemy import select
    from app.artifacts import ArtifactQuery, query_artifact
    from app.blocks.catalog import registry
    from app.execution import ExecutionLimits, Executor
    from app.metadata.database import Database
    from app.metadata.migrate import upgrade
    from app.metadata.models import (
        RunBlock,
        OutputEndpoint,
        Pipeline,
        PipelineRevision,
        Project,
    )
    from app.preview.models import PreviewRequest
    from app.preview.service import preview
    from app.runs import execute_revision

    rows, width = CASES[case]
    with tempfile.TemporaryDirectory(prefix="lps-benchmark-") as temporary:
        root = Path(temporary)
        db = Database(root / "metadata.sqlite3")
        try:
            upgrade(db)
            with db.transaction(write=True) as session:
                project = Project(name="Synthetic benchmark")
                session.add(project)
                session.flush()
                project_id = project.id
                pipeline = Pipeline(project_id=project_id, name="Synthetic workflow")
                session.add(pipeline)
                session.flush()
                definition = graph(
                    width, variant, rows - 1 if failure == "source" else 100000
                )
                revision = PipelineRevision(
                    pipeline_id=pipeline.id, revision=1, definition=definition
                )
                session.add(revision)
                session.flush()
                revision_id = revision.id
            workspace = root / "workspace"
            folder = workspace / project_id
            folder.mkdir(parents=True)
            hashes = fixtures(folder, rows, width)
            limits = (
                ExecutionLimits(max_rows=1)
                if failure == "executor"
                else ExecutionLimits()
            )
            outcome, elapsed = timed(
                lambda: execute_revision(
                    db,
                    Executor(registry, limits),
                    revision_id,
                    workspace_root=folder,
                )
            )
            if failure:
                codes = sorted(
                    {value.code for value in outcome.context.failures.values()}
                )
                required = "table_limit" if failure == "source" else "data_limit"
                if required not in codes:
                    raise AssertionError(f"Expected {required}, got {codes}")
                if outcome.state != "failed" or (folder / "result.parquet").exists():
                    raise AssertionError("Budget failure did not stop publication")
                with db.transaction() as session:
                    if session.scalar(select(OutputEndpoint)) is not None:
                        raise AssertionError("Failed run published an artifact")
                return {
                    "failure": failure,
                    "state": outcome.state,
                    "codes": codes,
                    "expected_code": required,
                    "execution_seconds": elapsed,
                }
            if outcome.state != "succeeded":
                raise AssertionError(f"Execution failed: {outcome.context.failures}")
            oracle = expected(rows)
            actual = pq.read_table(folder / "result.parquet").to_pylist()
            if actual != oracle:
                raise AssertionError("Parquet output differs from independent oracle")
            schema = pq.read_schema(folder / "result.parquet")
            if (
                schema.names != ["segment", "total", "count"]
                or str(schema.field("total").type) != "int64"
            ):
                raise AssertionError("Output schema changed")
            with db.transaction() as session:
                artifact = session.scalars(select(OutputEndpoint)).one()
                artifact_id = artifact.id
                if artifact.row_count != len(oracle):
                    raise AssertionError("Artifact row count differs")
                block_timings = {
                    block.node_id: block.duration_ms
                    for block in session.scalars(
                        select(RunBlock).where(RunBlock.run_id == outcome.run_id)
                    )
                }
            query_times = []
            for _ in range(3):
                result, seconds = timed(
                    lambda: query_artifact(
                        db,
                        artifact_id,
                        folder,
                        ArtifactQuery(columns=["segment", "total", "count"], limit=100),
                    )
                )
                if (
                    result.rows
                    != tuple(tuple(row[k] for k in result.columns) for row in oracle)
                    or result.has_more
                ):
                    raise AssertionError("Query result differs from oracle")
                query_times.append(seconds)
            preview_graph = {
                "nodes": [
                    definition["nodes"][0],
                    node(
                        "sample",
                        "transform.select",
                        {"columns": ["key", "value"]},
                    ),
                ],
                "edges": [edge("facts", "sample")],
            }
            request = PreviewRequest.model_validate(
                {
                    "definition": preview_graph,
                    "node_id": "sample",
                    "limits": {"max_rows": 25, "max_cells": 1000},
                }
            )
            sample, preview_seconds = timed(
                lambda: preview(
                    request,
                    project_id,
                    db,
                    registry,
                    workspace,
                    Event(),
                )
            )
            expected_sample = tuple(
                {k: fact(i, width)[k] for k in ("key", "value")} for i in range(25)
            )
            if sample.rows != expected_sample or not sample.truncated:
                raise AssertionError("Preview differs from leading-row oracle")
            if sample.sample_cell_count > 1000 or sample.inspected_row_count > 26:
                raise AssertionError("Preview exceeded its observation budget")
            return {
                "case": case,
                "variant": variant,
                "input_rows": rows,
                "input_columns": width + 2,
                "input_sha256": hashes,
                "graph_sha256": hashlib.sha256(
                    json.dumps(definition, sort_keys=True).encode()
                ).hexdigest(),
                "execution_seconds": elapsed,
                "input_rows_per_second": rows / elapsed,
                "block_duration_ms": block_timings,
                "peak_process_rss_mib": resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss
                / 1024,
                "preview_seconds": preview_seconds,
                "preview_rows": sample.sample_row_count,
                "preview_read_bytes": sample.source_read_bytes,
                "query_first_seconds": query_times[0],
                "query_repeat_seconds": query_times[1:],
                "query_repeat_median_seconds": statistics.median(query_times[1:]),
                "output_sha256": hashlib.sha256(
                    json.dumps(actual, sort_keys=True).encode()
                ).hexdigest(),
                "correctness": "passed",
            }
        finally:
            db.close()


def summarize(runs: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = (
        "execution_seconds",
        "input_rows_per_second",
        "peak_process_rss_mib",
        "preview_seconds",
        "query_first_seconds",
        "query_repeat_median_seconds",
    )
    return {
        f"{case}/{variant}": {
            metric: {
                "min": min(values),
                "median": statistics.median(values),
                "max": max(values),
            }
            for metric in metrics
            if (
                values := [
                    run[metric]
                    for run in runs
                    if run["case"] == case and run["variant"] == variant
                ]
            )
        }
        for case in CASES
        for variant in VARIANTS
    }


def optional_text(path: str) -> str | None:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=CASES)
    parser.add_argument("--variant", choices=VARIANTS, default="baseline")
    parser.add_argument("--failure", choices=("source", "executor"))
    parser.add_argument("--repeats", type=int, default=3, choices=range(1, 6))
    args = parser.parse_args()
    if platform.system() != "Linux":
        parser.error("Use the documented Linux container for comparable peak RSS units")
    if args.worker:
        print(json.dumps(worker(args.worker, args.variant, args.failure)))
        return
    if args.failure:
        parser.error("--failure requires --worker")

    def invoke(case: str, variant: str, failure: str | None = None) -> dict[str, Any]:
        command = [
            sys.executable,
            "-m",
            "experiments.workloads.benchmark",
            "--worker",
            case,
            "--variant",
            variant,
        ]
        if failure:
            command.extend(["--failure", failure])
        completed = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=180
        )
        if completed.returncode:
            raise RuntimeError(
                f"Worker failed ({case}/{variant}): {completed.stderr[-2000:]}"
            )
        decoded: dict[str, Any] = json.loads(completed.stdout)
        return decoded

    runs = []
    # Alternate order to reduce systematic baseline/optimization cache bias.
    for repeat in range(args.repeats):
        for case in CASES:
            for variant in VARIANTS if repeat % 2 == 0 else reversed(VARIANTS):
                runs.append(invoke(case, variant))
    for case in CASES:
        outputs = {run["output_sha256"] for run in runs if run["case"] == case}
        if len(outputs) != 1:
            raise AssertionError("Variant/repeat output fingerprints differ")
    from importlib.metadata import version

    report = {
        "environment": {
            "python": platform.python_version(),
            "platform": platform.system(),
            "machine": platform.machine(),
            "kernel": platform.release(),
            "cpu_model": next(
                (
                    line.split(":", 1)[1].strip()
                    for line in (optional_text("/proc/cpuinfo") or "").splitlines()
                    if line.startswith("model name")
                ),
                "unavailable",
            ),
            "logical_cpus": os.cpu_count(),
            "polars_threads": os.environ.get("POLARS_MAX_THREADS"),
            "versions": {
                name: version(name)
                for name in ("polars", "pyarrow", "duckdb", "sqlalchemy")
            },
            "source_revision": os.environ.get("BENCHMARK_REVISION", "unrecorded"),
            "cgroup_cpu_max": optional_text("/sys/fs/cgroup/cpu.max"),
            "cgroup_memory_max": optional_text("/sys/fs/cgroup/memory.max"),
        },
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "lock_sha256": hashlib.sha256(
            (ROOT / "requirements.lock").read_bytes()
        ).hexdigest(),
        "repeats": args.repeats,
        "runs": runs,
        "summary": summarize(runs),
        "failure_probes": [
            invoke("small", "baseline", failure) for failure in ("source", "executor")
        ],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
