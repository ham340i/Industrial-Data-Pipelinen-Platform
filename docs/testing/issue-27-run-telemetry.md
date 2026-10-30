# Issue #27 verification

Scope: durable run and block telemetry, interrupted-run recovery, log
redaction, and the run status/detail APIs. Design:
[run telemetry](../architecture/run-telemetry.md).
Branch: `feature/27-run-telemetry`, based on `main` at `1adfd01`.

## Acceptance criteria → tests

| Criterion | Tests |
|---|---|
| Persist run ID, pipeline/revision ID, status, start/completion times and duration | `test_success_persists_run_block_timings_and_counts`, `test_durations_use_the_injected_monotonic_clock` |
| Record block states/timings, row counts, redacted logs and structured errors | `test_success_…`, `test_measured_zero_rows_differ_from_unknown_counts`, `test_block_failure_is_structured_redacted_and_root_caused`, `tests/test_run_redaction.py` |
| Expose run status/detail APIs with a stable schema | `test_detail_has_a_stable_schema_and_links_artifacts`, `test_list_filters_paginates_and_orders_newest_first`, `test_invalid_requests_return_error_envelopes` |
| Failures and interrupted processes leave a truthful terminal/recoverable state | `test_unexpected_crash_leaves_a_truthful_terminal_state`, `test_restart_closes_interrupted_runs_once_and_keeps_finished_ones`, `test_metadata_survives_restart_and_interrupted_runs_are_closed`, `test_cancellation_is_recorded_as_cancelled`, `test_persistence_failures_are_logged_not_silently_dropped` |
| Isolation between runs and links from artifacts to run metadata | `test_runs_of_one_revision_are_isolated`, `test_detail_has_a_stable_schema_and_links_artifacts` |

Failure and boundary cases covered: an invalid pipeline creates no run row, an
unknown revision is reported, malformed UUID/state/page bounds return 422,
an unknown run returns 404, a block failure's reason contains a password and an
absolute path, cancellation happens mid-run, the engine crashes after starting,
the process dies mid-run and restarts, and the metadata database is unavailable
during a callback.

All fixtures are synthetic blocks in `tests/run_support.py` running on a real
file-backed SQLite database migrated to head. The existing
`test_migration_round_trip_and_schema_drift` also covers migration `0002`
(upgrade → `alembic check` → downgrade → upgrade).

## Observed results

macOS, Python 3.12.15 virtual environment, October 29, 2026:

- `python -m pytest -q`: **576 passed**. The 30 new #27 cases are in
  `test_run_telemetry.py`, `test_run_api.py` and `test_run_redaction.py`.
- `python -m ruff check`: passed. `python -m ruff format --check`: 66 files
  formatted. `python -m mypy`: no issues in 66 source files.
- `ruff --select C901,PLR0915` (max complexity 15) reports nothing in the
  new or changed files. The remaining reports are already on `main`, in
  `app/execution/runtime.py` and `app/pipelines/validation.py`.
- `python3 scripts/check_repository.py`, `python3 scripts/check_docs.py` and
  `git diff --check`: passed.
- Mutation check: with startup recovery disabled and failure reasons stored
  unredacted, 3 of these tests failed. They passed again after reverting.

Hosted CI results are recorded on the PR. No manual UI demonstration applies:
#27 has no UI, and run views come with the Iteration 4 workflow (E2E is
deferred there).

