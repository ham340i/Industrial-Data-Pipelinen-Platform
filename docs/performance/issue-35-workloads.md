# Issue #35 — representative bounded workflow measurements

Measured November 16, 2026, at revision `db5df18f1db583b508ff066e45f9008b82cf12d8`,
based on main `c4cc9671f3d555bcd47e29a85662d945e0cf613b`. Documentation and this
report are a subsequent evidence-only change. Prerequisites #24, #26 and #28
were closed before measurement. Independent review remains pending; planned
reviewer: `menaboulus`. No stakeholder hardware approval or signoff is claimed.

## Evidence and reproduction

- [Raw observations, fingerprints and environment](issue-35-results.json).
- [Runnable experiment, methodology and commands](../../experiments/workloads/README.md).
- [Fixture/oracle and real-service tests](../../tests/test_workload_benchmark.py).
- [Contribution record](../individual-contributions/karimikhaeil-iteration-4.md).

The committed runner was invoked as `python -m experiments.workloads.measure`
with three repeats. All 18 measurements passed independent Python output and
preview oracles, Arrow file/schema checks and registered-artifact query checks.
Each size's output fingerprint agrees across both variants and all repeats.
Both deliberate budget-failure probes passed without file/metadata publication.
No generated input datasets are committed; only sanitized measurements are kept.

Environment: Python 3.12.15, Polars 1.44.2, PyArrow 25.0.1, DuckDB 1.5.6,
SQLAlchemy 2.0.54, Linux x86_64 / WSL2 kernel 5.15.167.4, Intel i7-10750H
2.60 GHz. Docker inspection confirms two CPU equivalents, 1 GiB RAM and
2 GiB combined memory-plus-swap allowance, no network, two Polars threads.
The visible 12 logical CPUs are the host topology, not the granted quota.
Cgroup-v2 files were unavailable; the report records nulls and actual Docker
settings. Image ID, source/runner/lock hashes are included. Filesystem caches
were not flushed, and other host activity is not controlled or an approved
stakeholder-hardware baseline.

## Scenario and decision

Synthetic fact CSVs contain duplicate dimension keys and a null every eleventh
value. A 32-row dimension maps records to eight segments. The graph joins,
computes per-segment integer sum/non-null count, deterministically sorts and
publishes a registered Parquet output. It structurally exercises manufacturing
ETL building blocks without claiming representative partner data distributions.
The bounded alternative inserts Select(key,value) before the wide join; output
values, schemas and order must remain identical. This is a graph optimization,
not a production engine rewrite or default change.

## Execution and memory

Three fresh-process trials per row below. Execution includes graph validation,
SQLite telemetry and artifact registration, excluding fixture/migration/setup
and correctness checks. Throughput uses fact input rows divided by that time.
Peak RSS is the whole worker's high-water mark through execution, verification,
queries and preview; it does not isolate engine or preview allocations.

| Case / variant | Fact rows × columns | Execution median [min–max], seconds | Input rows/sec median | Peak RSS median [min–max], MiB |
|---|---|---|---|---|
| Small baseline | 100 × 6 | 0.1891 [0.1714–0.2906] | 528.8 | 248.57 [247.93–252.88] |
| Small projected | 100 × 6 | 0.1933 [0.1831–0.2348] | 517.4 | 247.92 [244.39–251.32] |
| Medium baseline | 1,000 × 10 | 0.4296 [0.3698–0.4753] | 2,327.9 | 245.36 [244.17–248.66] |
| Medium projected | 1,000 × 10 | 0.3974 [0.3092–0.4146] | 2,516.3 | 245.57 [244.97–249.70] |
| Wide baseline | 3,000 × 26 | 1.5382 [1.5252–2.2631] | 1,950.3 | 261.90 [260.11–262.66] |
| Wide projected | 3,000 × 26 | 1.0539 [1.0280–1.2235] | 2,846.6 | 255.45 [254.52–257.81] |

The wide baseline's median recorded block durations are 324 ms source, 691 ms
join and 381 ms aggregate. Projecting early reduces join/aggregate medians to
88/65 ms, but adds a Select stage and its validation/copies. Whole-run median
time falls about 31.5%, with approximately 2.5% lower whole-worker peak RSS.
This is evidence of wide intermediate processing cost, not a proof of which
internal allocation dominates. Block times omit some executor overhead and are
not expected to sum to the external execution wall time.

Decision: recommend explicit early projection for this wide graph; retain it
as an opt-in graph choice. Small median time is slightly worse and medium
ranges overlap, so there is no evidence for a universal automatic optimizer or
a blanket speedup. No production code/default change is warranted by three
small synthetic observations. Further tuning needs larger approved workloads
and confirmed hardware rather than extending this time-boxed spike into a redesign.

## Preview and local query latency

These are service calls, excluding network/UI rendering. Preview samples the
supported source → Select path (25 rows, 1,000-cell budget, at most 26 inspected
rows). The current policy does not preview Join/Aggregate/Sort; this benchmark
does not bypass that policy. Each query reads the registered eight-row summary
through the real bounded DuckDB service, not arbitrary SQL or an unregistered file.

| Case / variant | Preview median [min–max], ms | First query median [min–max], ms | Repeated-query median, ms |
|---|---|---|---|
| Small baseline | 6.6 [6.1–8.3] | 67.0 [64.4–111.4] | 20.8 |
| Small projected | 6.3 [6.1–13.0] | 76.7 [60.8–83.3] | 19.8 |
| Medium baseline | 8.5 [7.0–9.0] | 62.2 [53.9–67.2] | 20.9 |
| Medium projected | 7.8 [7.7–8.6] | 63.9 [60.1–74.5] | 20.3 |
| Wide baseline | 12.4 [11.5–34.2] | 77.6 [60.5–148.4] | 19.5 |
| Wide projected | 12.3 [12.2–13.4] | 65.7 [62.7–82.2] | 20.3 |

First query includes DuckDB lazy import/initialization. Repeated-query numbers
are medians across workers of each worker's two follow-up calls; all individual
latencies and min/median/max summaries remain in the raw JSON. The preview path
is identical for both variants, so its timing differences are variation, not an
optimization effect. Three trials do not support p95, concurrency or release SLOs.

## Verified failure envelope and limits

- With 100 rows and source max_rows=99, the run fails with `table_limit` and
  downstream `dependency_failed`; no output file or registered artifact exists.
- With executor max_rows=1, the run fails with `data_limit` and downstream
  `dependency_failed`; no output file or registered artifact exists.
- The largest successful workload measured here is 3,000 × 26 fact values plus
  the dimension and retained intermediates. This is an observation, not maximum
  capacity. Source/retained-row checks can happen after allocation; row/cell
  budgets do not bound bytes or many-to-many expansion.
- Container limits and worker timeouts protect the experiment. No memory-kill,
  timeout/cancellation threshold, large-artifact query scalability, six-hour
  capacity or stakeholder workload guarantee was measured. Disk/cache effects,
  narrow returned summaries, lack of concurrency and small sample count limit
  extrapolation. Integrated browser ETL acceptance is separate from this spike.

## Verification and attribution

The eight feature tests pass on Linux: fixture repeatability, independent
null/count/sum oracle, both real registered graphs, both complete service paths
and both no-publication failure probes. Host-side runner metadata gracefully
handles unavailable cgroup files. Full backend checks and hosted CI are recorded
in the PR; no timing threshold is imposed on CI.

Fresh local checks on November 16: all 921 backend tests passed (70 deprecation
warnings); Ruff lint/format passed (105 application/test/migration files), strict
mypy passed for 105 source files and separately for all three experiment Python
files. Explicit experiment Ruff lint/format passed. All 16 repository-tool tests,
release-plan validation, documentation/link checks (183 Markdown files) and Git
whitespace checks passed. The native Windows repository checker still flags the
two existing GitHub-setup Bash wrappers; hosted Linux repository CI is the
remaining authoritative check for them. Frontend code is unchanged. No check
was disabled and no independent reviewer or stakeholder approval is asserted.

AI Assistance: Karim requested #35. Codex designed, implemented and executed the
recorded experiment and drafted this evidence. No separate manual implementation
or verification by Karim, completed teammate review or stakeholder acceptance is
asserted.
