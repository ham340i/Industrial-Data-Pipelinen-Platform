# AI contribution: 50% or more AI-generated (Claude Code, used by ham340i)
"""Spike #109: eager per-block execution versus one fused Polars lazy plan.

One pipeline, three ways:

* ``product``: the real Release 1 executor and blocks (CSV source, Filter,
  Join, Aggregate, Sort, Parquet sink), exactly as the API runs them.
* ``eager``: the same steps as eager Polars calls, keeping every intermediate
  frame alive until the end, which is how the executor retains block outputs.
* ``lazy``: the same steps fused into one ``LazyFrame`` and written with
  ``sink_parquet`` so Polars can stream instead of materializing.

Usage (host, with Docker running and the locked packages installed)::

    python -m experiments.lazy_execution.spike measure --repeats 3

Each run is a fresh ``docker run`` of the repository's pinned Python base
image with a 1 GiB memory limit (no swap), two CPUs and no network. The
locked site-packages and this checkout are mounted read-only. Inputs are
synthetic and generated deterministically; nothing is committed but results.
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

    from app.pipelines.models import PipelineDefinition

    Schema = dict[str, type[pl.DataType]]

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "python@sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3"
THRESHOLD = 2000
# Largest size the product executor completes within its default budget.
PRODUCT_ROWS = 150_000
DIMENSION_KEYS = 1000
FACT_COLUMNS = ["id", "key", "value", "qty", "flag", "c1", "c2", "c3", "c4", "c5"]
FACT_TYPES = [
    "integer",
    "integer",
    "integer",
    "number",
    "boolean",
    "string",
    "string",
    "string",
    "string",
    "string",
]


# --------------------------------------------------------------------- inputs
def generate(data: Path, rows: int) -> None:
    """Write fact.csv (rows x 10, every 11th value null) and dimension.csv."""
    import polars as pl

    ids = pl.int_range(0, rows, eager=True, dtype=pl.Int64)
    fact = pl.DataFrame({"id": ids}).with_columns(
        key=(pl.col("id") * 7919) % DIMENSION_KEYS,
        value=pl.when(pl.col("id") % 11 == 0)
        .then(None)
        .otherwise((pl.col("id") * 31) % 10_000),
        qty=(pl.col("id") % 1000).cast(pl.Float64) / 8,
        flag=pl.col("id") % 2 == 0,
        **{
            f"c{i}": pl.format("sensor-{}-{}", pl.lit(i), pl.col("id") % 997)
            for i in range(1, 6)
        },
    )
    dimension = pl.DataFrame(
        {"key": pl.int_range(0, DIMENSION_KEYS, eager=True, dtype=pl.Int64)}
    ).with_columns(segment=pl.format("S{}", pl.col("key") % 8))
    fact.write_csv(data / "fact.csv", null_value="NULL")
    dimension.write_csv(data / "dimension.csv", null_value="NULL")


def _schemas() -> tuple[Schema, Schema]:
    import polars as pl

    kinds: Schema = {
        "integer": pl.Int64,
        "number": pl.Float64,
        "boolean": pl.Boolean,
        "string": pl.String,
    }
    fact = {n: kinds[t] for n, t in zip(FACT_COLUMNS, FACT_TYPES, strict=True)}
    dimension: Schema = {"key": pl.Int64, "segment": pl.String}
    return fact, dimension


# ---------------------------------------------------------------------- modes
def run_eager(data: Path, out: Path) -> None:
    """Eager Polars per step; every intermediate stays referenced, like the
    executor's retained block outputs."""
    import polars as pl

    fact_schema, dim_schema = _schemas()
    kept: dict[str, pl.DataFrame] = {}
    kept["fact"] = pl.read_csv(
        data / "fact.csv", schema=fact_schema, null_values="NULL"
    )
    kept["dimension"] = pl.read_csv(
        data / "dimension.csv", schema=dim_schema, null_values="NULL"
    )
    kept["filter"] = kept["fact"].filter(pl.col("value") > THRESHOLD)
    kept["join"] = kept["filter"].join(kept["dimension"], on="key", how="inner")
    kept["aggregate"] = (
        kept["join"]
        .group_by("segment")
        .agg(
            pl.col("value").sum().alias("total"), pl.col("value").count().alias("rows")
        )
        .sort("segment")
    )
    kept["aggregate"].write_parquet(out)


def lazy_plan(data: Path) -> pl.LazyFrame:
    import polars as pl

    fact_schema, dim_schema = _schemas()
    fact = pl.scan_csv(data / "fact.csv", schema=fact_schema, null_values="NULL")
    dimension = pl.scan_csv(
        data / "dimension.csv", schema=dim_schema, null_values="NULL"
    )
    return (
        fact.filter(pl.col("value") > THRESHOLD)
        .join(dimension, on="key", how="inner")
        .group_by("segment")
        .agg(
            pl.col("value").sum().alias("total"), pl.col("value").count().alias("rows")
        )
        .sort("segment")
    )


def run_lazy(data: Path, out: Path) -> None:
    lazy_plan(data).sink_parquet(out)


def _product_definition() -> PipelineDefinition:
    from app.pipelines.models import PipelineDefinition

    def node(node_id: str, block: str, config: dict[str, object]) -> dict[str, object]:
        return {
            "id": node_id,
            "block_id": block,
            "block_version": "1.0.0",
            "config": config,
        }

    def edge(source: str, target: str, port: str = "table") -> dict[str, object]:
        return {
            "id": f"{source}-{target}",
            "source": {"node_id": source, "port": "table"},
            "target": {"node_id": target, "port": port},
        }

    source = {"max_rows": 1_000_000, "max_cells": 2_000_000, "max_bytes": 134_217_728}
    # Definitions are strict models; parse them from JSON as the API does.
    return PipelineDefinition.from_json(
        json.dumps(
            {
                "schema_version": 1,
                "nodes": [
                    node(
                        "fact",
                        "source.csv",
                        {
                            "resource_ref": "fact.csv",
                            "columns": FACT_COLUMNS,
                            "types": FACT_TYPES,
                            "nullable": [True] * len(FACT_COLUMNS),
                            **source,
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
                        "filter",
                        "transform.filter",
                        {
                            "column": "value",
                            "operator": "gt",
                            "value_text": str(THRESHOLD),
                        },
                    ),
                    node(
                        "join",
                        "transform.join",
                        {"left_on": ["key"], "right_on": ["key"]},
                    ),
                    node(
                        "aggregate",
                        "transform.aggregate",
                        {
                            "group_by": ["segment"],
                            "operations": [
                                {
                                    "column": "value",
                                    "function": "sum",
                                    "output_name": "total",
                                },
                                {
                                    "column": "value",
                                    "function": "count",
                                    "output_name": "rows",
                                },
                            ],
                        },
                    ),
                    node(
                        "sort", "transform.sort", {"columns": [{"column": "segment"}]}
                    ),
                    node(
                        "sink", "sink.parquet", {"resource_ref": "out-product.parquet"}
                    ),
                ],
                "edges": [
                    edge("fact", "filter"),
                    edge("filter", "join", "left"),
                    edge("dimension", "join", "right"),
                    edge("join", "aggregate"),
                    edge("aggregate", "sort"),
                    edge("sort", "sink"),
                ],
            }
        )
    )


def run_product(data: Path, out: Path) -> None:
    """The real executor; raises if any node does not complete."""
    from app.blocks.catalog import registry
    from app.execution import Executor

    context = Executor(registry).execute(_product_definition(), workspace_root=data)
    if context.failures:
        codes = {node: f.code for node, f in context.failures.items()}
        raise RuntimeError(f"product run failed: {codes}")
    (data / "out-product.parquet").replace(out)


MODES = {"eager": run_eager, "lazy": run_lazy, "product": run_product}


def worker(mode: str, data: Path, out: Path) -> None:
    """Run one mode once and print a JSON line with time and peak memory."""
    started = time.perf_counter()
    MODES[mode](data, out)
    elapsed = time.perf_counter() - started
    peak_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(
        json.dumps(
            {"seconds": round(elapsed, 3), "peak_mib": round(peak_kib / 1024, 1)}
        )
    )


# ----------------------------------------------------------------- host side
def _site_packages() -> str:
    import site

    return site.getsitepackages()[0]


def _docker(data: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    command = [
        "docker", "run", "--rm", "--memory=1g", "--memory-swap=1g", "--cpus=2",
        "--network=none", "-e", "POLARS_MAX_THREADS=2",
        "-e", "PYTHONPATH=/deps:/repo",
        "-v", f"{_site_packages()}:/deps:ro", "-v", f"{ROOT}:/repo:ro",
        "-v", f"{data}:/data", "-w", "/repo", IMAGE,
        "python", "-m", "experiments.lazy_execution.spike", *arguments,
    ]  # fmt: skip
    return subprocess.run(command, capture_output=True, text=True, timeout=900)


def _measure_case(data: Path, mode: str, rows: int, repeats: int) -> dict[str, object]:
    runs: list[dict[str, object]] = []
    for repeat in range(repeats):
        out = f"/data/out-{mode}-{repeat}.parquet"
        done = _docker(data, "worker", mode, "/data", out)
        if done.returncode == 0:
            runs.append(json.loads(done.stdout.strip().splitlines()[-1]))
        else:
            # 137 is the kernel's OOM kill at the 1 GiB container limit.
            reason = "killed at 1 GiB limit" if done.returncode == 137 else "failed"
            runs.append({"error": reason, "detail": done.stderr.strip()[-300:]})
    ok = [r for r in runs if "seconds" in r]
    summary: dict[str, object] = {"mode": mode, "rows": rows, "runs": runs}
    if ok:
        summary["median_seconds"] = statistics.median(
            float(str(r["seconds"])) for r in ok
        )
        summary["median_peak_mib"] = statistics.median(
            float(str(r["peak_mib"])) for r in ok
        )
    return summary


def _same_output(data: Path, first: str, second: str) -> dict[str, object]:
    import polars as pl
    import pyarrow.parquet as pq

    a, b = data / first, data / second
    if not (a.exists() and b.exists()):
        return {"compared": [first, second], "available": False}
    schema_a, schema_b = pq.read_schema(a), pq.read_schema(b)
    return {
        "compared": [first, second],
        "values_equal": pl.read_parquet(a).equals(pl.read_parquet(b)),
        "arrow_schema_equal": schema_a.equals(schema_b),
        "types_equal": [f.type for f in schema_a] == [f.type for f in schema_b],
    }


def _product_probe(rows: int) -> dict[str, object]:
    """One product run just above PRODUCT_ROWS, to record how it stops."""
    with tempfile.TemporaryDirectory(prefix="lll-109-") as temp:
        data = Path(temp)
        os.chmod(data, 0o777)
        _docker(data, "generate", "/data", str(rows)).check_returncode()
        done = _docker(data, "worker", "product", "/data", "/data/out.parquet")
        tail = (done.stdout + done.stderr).strip().splitlines()[-1:]
        return {"rows": rows, "returncode": done.returncode, "outcome": tail}


def measure(sizes: list[int], repeats: int) -> dict[str, object]:
    report: dict[str, object] = {
        "image": IMAGE,
        "limits": "1 GiB, no swap, 2 CPUs, no network",
    }
    cases: list[dict[str, object]] = []
    checks: list[dict[str, object]] = []
    for rows in sizes:
        with tempfile.TemporaryDirectory(prefix="lll-109-") as temp:
            data = Path(temp)
            os.chmod(data, 0o777)
            _docker(data, "generate", "/data", str(rows)).check_returncode()
            modes = (
                ["product", "eager", "lazy"]
                if rows <= PRODUCT_ROWS
                else ["eager", "lazy"]
            )
            for mode in modes:
                cases.append(_measure_case(data, mode, rows, repeats))
            pairs = [("eager", "lazy")] + (
                [("product", "lazy")] if "product" in modes else []
            )
            for x, y in pairs:
                check = _same_output(data, f"out-{x}-0.parquet", f"out-{y}-0.parquet")
                checks.append({"rows": rows, **check})
    plan = _docker(Path(tempfile.mkdtemp()), "plan").stdout
    report.update(
        cases=cases,
        output_checks=checks,
        product_budget_probe=_product_probe(200_000),
        optimized_plan=plan,
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("data", type=Path)
    gen.add_argument("rows", type=int)
    run = sub.add_parser("worker")
    run.add_argument("mode", choices=sorted(MODES))
    run.add_argument("data", type=Path)
    run.add_argument("out", type=Path)
    sub.add_parser("plan")
    host = sub.add_parser("measure")
    host.add_argument("--repeats", type=int, default=3)
    host.add_argument("--sizes", type=int, nargs="+", default=[PRODUCT_ROWS, 2_000_000])
    args = parser.parse_args()
    if args.command == "generate":
        generate(args.data, args.rows)
    elif args.command == "worker":
        worker(args.mode, args.data, args.out)
    elif args.command == "plan":
        print(lazy_plan(Path("/data")).explain())
    else:
        json.dump(measure(args.sizes, args.repeats), sys.stdout, indent=2)
        print()


if __name__ == "__main__":
    main()
