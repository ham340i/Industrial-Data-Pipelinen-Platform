# Issue #10 headless ETL verification

Local verification on October 21, 2026, macOS arm64 / Python 3.13.0, branch
`feature/10-headless-etl`, based on `202a183`; implementation commit `5f56766`.
[PR #67](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/67)
is open with menaboulus requested for independent review. See the
[design and reproduction commands](../../experiments/headless_etl/README.md).

## Observed results

- `python -m pytest tests experiments/headless_etl/test_spike.py -q`:
  **386 passed**, including 12 spike cases; 38 upstream Starlette deprecation warnings.
- `python -m experiments.headless_etl.spike`: `verified: true`, three rows,
  columns `sensor_id`, `reading`; all three nodes emitted started/succeeded.
- Spike Ruff lint and format checks passed.
- Root Ruff lint, format and mypy checks passed.
- Repository, documentation and whitespace checks passed.

The golden test checks exact values, column order, Arrow string types and
non-nullable schema after reading the actual Parquet file. Other cases cover
header-only input, reordered selection, malformed CSV, missing selection,
duplicate selection, unknown version/port, existing output preservation and
cleanup after a partial write. Invalid graphs fail before I/O. Block failures
retain safe node identities and stop downstream execution.

Local dependencies were installed from root development ranges, with Polars
1.38.1 and PyArrow 23.0.1. Existing hosted CI uses the root hash lock on Python 3.12. The spike has a
separate generated hash lock and explicit test command. GitHub rejected the
initial workflow update because the available token lacks workflow scope; the
PR preserves existing workflows. A dedicated hosted spike check is follow-up
work. Local success is not a hosted CI result.

## Observations and limitations

The initial local implementation used Python selection; live issue inspection
identified the explicit Polars criterion, and selection now executes through a
Polars DataFrame. No failed performance experiments or benchmark results are
claimed. PyArrow's sandboxed CPU-cache probing emitted permission diagnostics;
the read-back verification still passed.

The SDK and DAG from #8/#9 are reused, including configuration validation,
versioned registry resolution, edge routing, lifecycle events and safe errors.
The three spike blocks provide starting points for #16/#18/#20. The reference
runner informs #22; resource authorization, numeric/date/null CSV semantics,
streaming, concurrency, cancellation, retries, run persistence and production
telemetry remain follow-up work. Whole-table copies are intentionally accepted
for this small proof, with no scalability claim.

UI E2E is not applicable to this headless spike; integration into the Iteration 4
acceptance workflow remains future work. No stakeholder data was used.
Independent student review, stakeholder demonstration and merge remain pending.

AI assistance: Codex designed, implemented and verified this change at the
user's request. No independent human implementation or review is asserted.
