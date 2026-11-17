# Representative local workload benchmark (#35)

This isolated experiment exercises the production executor, SQLite telemetry,
registered Parquet artifacts, bounded DuckDB queries and selected-source preview.
It changes no production defaults and adds no dependencies. Inputs are synthetic;
structural resemblance to the release workflow is not stakeholder validation.

## Reproduce

From the repository root, with Docker running:

```sh
docker build -f docker/api.Dockerfile -t lps-workload-benchmark .
python -m experiments.workloads.measure --repeats 3
```

The host runner needs Python 3.11+ and Git. It creates its own container, inspects
its actual limits, runs without network, mounts this checkout read-only and
removes only that container afterward. Temporary inputs, SQLite metadata and
outputs live inside each worker's temporary directory and are deleted. It emits
JSON on stdout; it accepts no arbitrary output-path argument. To save UTF-8 JSON
without PowerShell encoding changes:

```sh
python -c "import pathlib,subprocess,sys; pathlib.Path('local-benchmark.json').write_bytes(subprocess.check_output([sys.executable,'-m','experiments.workloads.measure']))"
```

The image uses the repository's digest-pinned Python and hash-locked libraries.
Run on an otherwise idle machine. The configured limits are two CPU equivalents,
1 GiB RAM, Docker's default swap allowance and two Polars threads; actual
`NanoCpus`, `Memory`, `MemorySwap` and network mode are included in the report.
Logical host CPU count is not the container quota. Missing cgroup-v2 files are
recorded as null, rather than guessed. Workers have a 180-second timeout and
the overall host run has a 600-second timeout; timeouts abort reporting rather
than inventing measurements. Three repeats normally take about a minute here.

## Workload and measurements

Facts have duplicate dimension keys and every eleventh value is null. A unique
32-row dimension assigns eight segments. Cases use 100/1,000/3,000 fact rows
with 6/10/26 columns respectively. The versioned graphs run:

```text
CSV facts ──────────────┐
                       Join → Aggregate(sum,count) → Sort → Parquet
CSV dimension ─────────┘
```

The projected variant inserts Select(key,value) before Join. Both variants have
the same exact expected output; the fixture generator and graph configurations
are versioned Python, and input/graph/output SHA-256 values are recorded.

- Execution wall time includes graph loading/validation, real block execution,
  SQLite telemetry and artifact registration. Fixture generation, migration,
  revision creation and correctness assertions are outside that timer.
- Throughput is fact input rows divided by that execution time. It is not join
  output throughput or a per-block capacity claim.
- Each worker runs once in a fresh process. Peak process RSS includes imports,
  fixtures, migration, execution, Arrow verification, preview and queries; it is
  not incremental engine memory, container memory or separate preview peak RSS.
- SQLite block durations identify stages, but are not additive: executor
  validation/copies and recorder overhead can lie outside block timing windows.
- First DuckDB query includes lazy library startup. Two more queries in the same
  worker report repeated-query latency separately. All results match the oracle.
- Preview measures the service's bounded source → Select path: 25 leading rows,
  max 1,000 cells, and at most 26 inspected rows. Join/Aggregate/Sort preview is
  unsupported by the current policy and is not claimed. This is service latency,
  not HTTP, browser rendering, concurrent-user or request-to-visible latency.
- An independent pure-Python oracle checks sums, non-null counts, deterministic
  ordering and values. Arrow checks the actual output file and schema, the
  artifact API checks its rows/metadata, and preview has its own leading-row
  oracle. Output fingerprints must agree across variants and repeats.
- Trial order alternates variants. OS filesystem caches, CPU scheduling and
  library caches are not reset or claimed cold. Min/median/max and every raw
  observation are retained; three samples cannot establish p95 or an SLO.

## Failure envelope

For 100 source rows, source `max_rows=99` must fail with `table_limit`; an
executor retained-row budget of one must fail with `data_limit`. Both probes
check that no output file or artifact metadata was published. These are
configured-boundary failures, not experimentally discovered maximum capacity.
Row/cell limits are post-read/retention checks in parts of the runtime; they do
not guarantee pre-allocation memory bounds or bound many-to-many join expansion.
No OOM, timeout threshold, cancellation latency or production envelope is claimed.

## Tests and results

```sh
python -m pytest tests/test_workload_benchmark.py -q
python -m ruff check --isolated --select E,F,W,B,UP --target-version py312 experiments/workloads
python -m mypy experiments/workloads
```

Linux worker integration tests are skipped on Windows because `ru_maxrss` units
and availability differ; fixture/oracle/graph tests still run on Windows. Hosted
Linux CI runs all eight tests. Repeated timing trials are deliberately manual;
CI checks correctness without brittle timing thresholds.

See [observed results and tradeoffs](../../docs/performance/issue-35-workloads.md).

AI Assistance: Codex implemented and measured this experiment at Karim's
direction. Independent reviewer and stakeholder acceptance remain separate.
