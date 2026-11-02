# Issue #29 verification

Scope: Manual/Timer trigger block contracts, the execute API, and a
single-process, no-overlap interval timer with start/stop. Design:
[triggers and execute](../architecture/triggers-and-execute.md).
Branch: `feature/29-manual-timer-triggers`, based on `main` after PR #74.

## Acceptance criteria → tests

| Criterion | Tests |
|---|---|
| Execute API for a saved validated pipeline, returns its run ID | `test_execute_runs_the_latest_revision_and_returns_its_run_id`, `test_execute_unknown_pipeline_is_structured_404` |
| Manual and Timer trigger contracts, separate from tabular ports | `test_manual_trigger_emits_only_a_control_signal`, `test_timer_trigger_emits_only_a_control_signal`, `test_both_triggers_are_registered_as_trigger_type` |
| Start/stop a single-process interval timer with safe no-overlap | `test_start_stop_round_trip_tracks_status`, `test_runs_from_a_slow_timer_never_overlap`, `test_timer_ticks_create_isolated_runs_without_overlap` |
| Invalid/unsupported trigger configuration is a structured error | `test_timer_interval_out_of_bounds_is_rejected`, `test_timer_interval_is_required`, `test_execute_invalid_pipeline_is_structured_422_and_creates_no_run`, `test_timer_start_without_a_timer_trigger_is_structured_422`, `test_timer_start_with_invalid_interval_is_structured_422` |
| No persistent/cron/distributed guarantees; shutdown cleanup | documented in `app/runs/scheduler.py` and the design doc; `test_stop_all_cleans_up_every_running_timer`, `test_shutdown_stops_every_running_timer_thread` |

Additional boundary cases covered: starting a timer twice
(`test_start_twice_raises_already_running`), stopping one that is not
running (`test_stop_when_not_running_raises_not_running`), stopping during
the wait phase returns promptly rather than blocking for the full interval
(`test_stop_between_ticks_returns_promptly`), and a block already running
when `stop()` is called is not killed - cancellation is cooperative, so it
finishes and is recorded as `succeeded`, not `cancelled`
(`test_stop_waits_for_an_in_flight_block_to_finish_rather_than_killing_it`).

All scheduler fixtures use a synthetic `RecordingTrigger` block
(`tests/test_scheduler.py`) with a configurable delay, so overlap and
cancellation timing are asserted directly from recorded wall-clock spans
rather than inferred from side effects.

## Observed results

macOS, Python 3.12.15 virtual environment, November 2, 2026:

- `python -m pytest -q`: **702 passed** (24 new in `test_block_triggers.py`,
  `test_scheduler.py` and `test_execute_api.py`), run twice to rule out
  timing flakiness in the interval-based tests.
- `python -m ruff check`: passed. `python -m ruff format --check`: passed.
  `python -m mypy`: no issues in 75 source files.
- `python3 scripts/check_repository.py` and `python3 scripts/check_docs.py`:
  passed.
- A genuine bug was caught during development: an initial `zip(ordered,
  ordered[1:], strict=True)` in the no-overlap assertion helper always
  raised, since the second argument is deliberately one element shorter.
  Caught by actually running the test (not just by ruff, which had
  suggested adding `strict=`), fixed to `strict=False` with a comment
  explaining the deliberate offset.
- A second mistake was caught before it reached a passing test: assuming a
  cooperative `stop()` mid-execution would mark a single-block run
  `cancelled`. Running it against the real recorder showed `succeeded`
  instead, which is correct - the block was not and could not be
  interrupted. The test and the design doc were corrected to document that
  behavior rather than the original (wrong) assumption.

Hosted CI results are recorded on the PR. No manual UI demonstration
applies: #29 has no UI; it is pure API/engine work, consistent with the
issue's own E2E note (deferred to the Iteration 4 UI integration).
