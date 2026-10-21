# Issue #13: observed Polars / Arrow schema and memory spike

Measured October 13, 2026 during Iteration 2 as Iteration 1 carryover.
Status: experiment implemented and executed locally; independent review, hosted
CI, final integration acceptance and experiment merge remain pending. SDK #8
has since merged through PR #59 at `80f8dc7`. No partner data used.

## Reproducer and environment

The [experiment](../../experiments/polars_arrow/README.md) has its own exact,
hash-verified dependency lock and Python base-image digest. It does not change
the API dependencies. Final measured source and lock fingerprints are in
[raw results](issue-13-results.json). These identify the measured source before
commit; the issue-specific PR identifies its published implementation revision.

Observed environment: Python 3.12.15, Linux x86_64 inside Docker Desktop,
Polars 1.44.2, PyArrow 25.0.1. The container saw 12 logical CPUs but was limited
with `--cpus=2 --memory=1g`; each library used two compute threads and Arrow two
I/O threads. These are experiment constraints, not stakeholder hardware claims.
Three fresh subprocesses per case avoid sharing a process high-water mark.

Each worker creates a deterministic fixture, converts Polars to Arrow and back,
writes Zstandard Parquet in disposable temporary storage, reads it back, checks
exact values/schema/order and creates a bounded preview. Small/wide/null-heavy
cases are fixed synthetic inputs, not representative approved industrial data.
Fixtures include Int64 above 2^53, UInt64 at/above 2^63, Float64, boolean, string,
Date, UTC microsecond Datetime, typed all-null Int64 and nullable Int32 columns.
Empty/single-row cases are additionally checked by the correctness suite.

## Final measured results

Medians across three runs; milliseconds except peak RSS. Raw JSON includes every
run and min/median/max for each metric.

| Case | Rows × columns | Build | To Arrow | From Arrow | Parquet write | Parquet read | Preview | Peak RSS MiB (median; min–max) |
|---|---|---|---|---|---|---|---|---|
| Small | 1,000 × 10 | 5.03 | 0.48 | 2.57 | 1.89 | 66.74 | 0.050 | 152.45; 152.31–154.34 |
| Wide | 5,000 × 128 | 7.01 | 1.02 | 1.00 | 16.44 | 69.83 | 0.041 | 168.04; 167.72–169.85 |
| Null-heavy | 100,000 × 10 | 8.70 | 1.36 | 1.44 | 41.75 | 78.56 | 0.034 | 210.28; 209.59–210.82 |

All nine round-trips passed exact correctness checks. Four unittest methods
passed, covering determinism/empty/single-row/wide round-trips, known reference
values, preview bounds and precision-loss detection. Standalone Ruff lint and
formatting were checked separately from the application's source-only config.

RSS is Linux `ru_maxrss`, converted from KiB to bytes. It includes library
imports, fixture construction, conversions, Parquet I/O, correctness assertions
and the negative control. It is not memory exclusively attributed to one stage
or to the table. Baseline current RSS and Polars estimated table/sample sizes
are also retained separately in JSON. Timings cover individual operations after
imports; they exclude process startup. Parquet reads can include first-use
initialization and benefit from recently written filesystem caches. Three runs
do not establish a statistically robust performance distribution.

## Failed assumptions and integration decisions

1. **Casting large integers through Float64 preserves them:** false. Each worker
   deliberately casts the large-integer column to Float64 and back. Exact
   equality fails in all nine runs, as expected; the test confirms corruption
   detection. Keep integer/unsigned types through interchange, and define safe
   browser serialization for values beyond JavaScript's exact integer range.
2. **All-null data has a useful inferred type:** do not rely on inference.
   The fixture explicitly declares Int64 and confirms it survives both paths.
   Schema propagation must carry the declared type even when no non-null values
   are present. This experiment does not test arbitrary inference policies.
3. **A small preview proves bounded process memory:** unsupported. The full
   fixture is materialized before slicing; RSS far exceeds returned sample size.
   Slices can retain backing buffers. Return-size limits are necessary but do
   not bound loading, joins, intermediate allocations or execution time.
4. **Current SDK types cover Arrow temporal data directly:** false by contract.
   SDK v1 declares string/integer/number/boolean only. The measured Date and UTC
   Datetime types need an explicit future adapter/schema policy; silently turning
   them into untyped strings would lose semantics. Likewise UInt64 width/range
   cannot be fully expressed by the generic SDK integer type. No production SDK
changes or silent widening rules are introduced here.

## Bounded-preview recommendation

Keep the SDK's returned budgets of at most 20 rows and 2,000 cells for this
initial experiment. Slice before converting to Python dictionaries or rendering.
For 128 columns this permits 15 rows (1,920 cells), not 20 rows. The narrow cases
return 20 rows (200 cells). If the schema alone exceeds the cell budget, return
schema with an explicit empty-sample explanation rather than publishing data.

Use projection and bounded source reads/lazy limits where supported. Treat
runtime memory, elapsed time, string byte sizes and cancellation as separate
limits; row/cell counts alone are insufficient. Measure actual source/transform
plans before claiming end-to-end bounded execution. These observations support
the preview design, not a production operating envelope or optimal threshold.

## Scope, references and review

Review follow-up (2026-10-19): removed the CLI `--output` argument after
SonarCloud identified an arbitrary file-write path. The report is always emitted
on stdout; callers choose any destination through their shell. All six unittest
methods pass, including rejection of absolute and relative output arguments
without changing existing files. Ruff checks pass. A fresh three-repeat run
passed all nine correctness checks; its report and current source hashes are in
[review measurements](issue-13-results-review.json). The earlier measurements
above remain historical evidence. Codex implemented and verified this follow-up.

No datasets are persisted in the repository; only sanitized measured JSON is
recorded. Temporary Parquet files are deleted. Production connectors, engine,
SDK adapters and UI acceptance are separate work. #8 remains the agreed
integration prerequisite, now merged through PR #59. Planned independent
reviewer: `MarcElHaddad1`.

Primary references: [Polars DataFrame API](https://docs.pola.rs/api/python/stable/reference/dataframe/index.html),
[Arrow Parquet guide](https://arrow.apache.org/docs/python/parquet).
The experiment verifies behavior for its locked versions; current documentation
does not replace executable version-specific correctness checks.

AI Assistance: Karim requested #13 implementation; Codex created and ran the
experiment, tests and measurements and drafted this note. No separate manual
measurement or authorship by Karim, accepted performance target, stakeholder
approval or completed independent review is claimed.
