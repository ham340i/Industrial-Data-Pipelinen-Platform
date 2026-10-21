"""Issue #13: reproducible interchange checks and isolated Linux RSS measurements."""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
from time import perf_counter

import polars as pl
from polars.testing import assert_frame_equal
import pyarrow as pa
import pyarrow.parquet as pq

CASES = {"small": (1000, 10), "wide": (5000, 128), "nulls": (100000, 10)}


def fixture(rows: int, width: int = 10) -> pl.DataFrame:
    if rows < 0 or width < 10:
        raise ValueError("Rows must be nonnegative and width at least ten")
    frame = pl.DataFrame({"id": pl.Series(range(rows), dtype=pl.Int64)})
    frame = frame.with_columns(
        (pl.col("id") + 2**53 + 1).alias("large_integer"),
        (pl.col("id").cast(pl.UInt64) + 2**63).alias("unsigned"),
        pl.when(pl.col("id") % 7 == 0)
        .then(None)
        .otherwise(pl.col("id") / 10)
        .cast(pl.Float64)
        .alias("value"),
        (pl.col("id") % 2 == 0).alias("flag"),
        pl.concat_str([pl.lit("asset-"), pl.col("id") % 17]).alias("label"),
        pl.lit(date(2026, 1, 1), dtype=pl.Date).alias("date"),
        pl.lit(datetime(2026, 1, 1, tzinfo=UTC), dtype=pl.Datetime("us", "UTC")).alias(
            "observed_at"
        ),
        pl.lit(None, dtype=pl.Int64).alias("all_null"),
        pl.when(pl.col("id") % 11 == 0)
        .then(None)
        .otherwise(pl.col("id").cast(pl.Int32))
        .alias("nullable_integer"),
    )
    return frame.with_columns(
        (pl.col("id") % (index + 2)).alias(f"extra_{index:03}")
        for index in range(width - 10)
    )


def preview(
    frame: pl.DataFrame, max_rows: int = 20, max_cells: int = 2000
) -> pl.DataFrame:
    if max_rows < 1 or max_cells < 1:
        raise ValueError("Preview budgets must be positive")
    return frame.head(min(max_rows, max_cells // max(frame.width, 1)))


def verify_roundtrip(frame: pl.DataFrame, directory: Path) -> dict[str, float]:
    timings = {}
    start = perf_counter()
    arrow = frame.to_arrow()
    timings["to_arrow_ms"] = (perf_counter() - start) * 1000
    start = perf_counter()
    restored = pl.from_arrow(arrow)
    timings["from_arrow_ms"] = (perf_counter() - start) * 1000
    assert_frame_equal(frame, restored, check_exact=True)
    start = perf_counter()
    pq.write_table(arrow, directory / "fixture.parquet", compression="zstd")
    timings["parquet_write_ms"] = (perf_counter() - start) * 1000
    start = perf_counter()
    persisted = pq.read_table(directory / "fixture.parquet")
    timings["parquet_read_ms"] = (perf_counter() - start) * 1000
    if not arrow.equals(persisted):
        raise AssertionError("Arrow schema/values changed through Parquet")
    assert_frame_equal(frame, pl.from_arrow(persisted), check_exact=True)
    return timings


def current_rss_bytes() -> int:
    # Linux /proc reports KiB; this experiment intentionally measures Linux.
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("Linux VmRSS is unavailable")


def worker(case: str) -> dict[str, object]:
    pa.set_cpu_count(2)
    pa.set_io_thread_count(2)
    rows, width = CASES[case]
    baseline = current_rss_bytes()
    start = perf_counter()
    frame = fixture(rows, width)
    build_ms = (perf_counter() - start) * 1000
    with tempfile.TemporaryDirectory(prefix="arrow-spike-") as temporary:
        timings = verify_roundtrip(frame, Path(temporary))
    start = perf_counter()
    sample = preview(frame)
    preview_ms = (perf_counter() - start) * 1000
    assert sample.height <= 20 and sample.height * sample.width <= 2000
    # A deliberate precision-loss experiment must fail exact equality.
    loss_detected = False
    if rows:
        lossy = frame.with_columns(
            pl.col("large_integer").cast(pl.Float64).cast(pl.Int64)
        )
        try:
            assert_frame_equal(frame, lossy, check_exact=True)
        except AssertionError:
            loss_detected = True
        if not loss_detected:
            raise AssertionError("Precision-loss control failed to detect corruption")
    return {
        "case": case,
        "rows": rows,
        "columns": width,
        "build_ms": build_ms,
        **timings,
        "preview_ms": preview_ms,
        "baseline_rss_bytes": baseline,
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "frame_estimated_bytes": frame.estimated_size(),
        "preview_estimated_bytes": sample.estimated_size(),
        "preview_rows": sample.height,
        "correctness": "passed",
        "float_precision_loss_detected": loss_detected,
        "schema": {name: str(dtype) for name, dtype in frame.schema.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=CASES)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if platform.system() != "Linux":
        parser.error("Run in Linux for comparable /proc and ru_maxrss units")
    if args.worker:
        print(json.dumps(worker(args.worker)))
        return
    if not 1 <= args.repeats <= 10:
        parser.error("Use between one and ten repeats")
    runs = []
    for case in CASES:
        for _ in range(args.repeats):
            completed = subprocess.run(
                [sys.executable, __file__, "--worker", case],
                check=True,
                text=True,
                capture_output=True,
                timeout=120,
                env=dict(os.environ, POLARS_MAX_THREADS="2"),
            )
            runs.append(json.loads(completed.stdout))
    metrics = [
        "build_ms",
        "to_arrow_ms",
        "from_arrow_ms",
        "parquet_write_ms",
        "parquet_read_ms",
        "preview_ms",
        "peak_rss_bytes",
    ]
    summary = {
        case: {
            metric: {
                "min": min(run[metric] for run in runs if run["case"] == case),
                "median": statistics.median(
                    run[metric] for run in runs if run["case"] == case
                ),
                "max": max(run[metric] for run in runs if run["case"] == case),
            }
            for metric in metrics
        }
        for case in CASES
    }
    report = {
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "lock_sha256": hashlib.sha256(
            Path(__file__).with_name("requirements.lock").read_bytes()
        ).hexdigest(),
        "environment": {
            "python": platform.python_version(),
            "os": platform.system(),
            "architecture": platform.machine(),
            "cpu_count": os.cpu_count(),
            "polars": pl.__version__,
            "pyarrow": pa.__version__,
            "threads_per_library": 2,
        },
        "method": (
            "Fresh subprocess per repeat; exact correctness checks; process peak RSS "
            "includes imports, fixtures, conversions and negative control"
        ),
        "repeats": args.repeats,
        "runs": runs,
        "summary": summary,
    }
    serialized = json.dumps(report, indent=2) + "\n"
    # File destinations belong to the invoking shell, not untrusted CLI paths.
    sys.stdout.write(serialized)


if __name__ == "__main__":
    main()
