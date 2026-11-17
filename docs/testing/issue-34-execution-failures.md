# Issue #34 execution failure verification

Status: implemented and locally verified on November 17, 2026, in uncommitted
changes on `feature/34-stabilize-execution-failures-and-output-cleanup` based on
`cc5ebdf11677d1dd6a8ba74e2ce6273ff3db429e`. This base hash does not identify the
implementation changes. No commit, push, PR, hosted CI, independent approval,
stakeholder signoff or release completion is asserted.

Issue: [#34](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/34).
Design: [execution failure and recovery](../architecture/execution-failure-recovery.md).

## Acceptance mapping

| Criterion | Executed evidence |
|---|---|
| Failure propagation and dependent skips | Existing executor diamond/independent-branch cases; `test_failed_stage_preserves_target_and_registers_no_output` covers real source, transform and sink failures; lifecycle-hook and post-publication budget cases verify final node state wins over SDK success. |
| No success metadata from unsuccessful writes | CSV/Parquet partial-write, flush, publication and cancellation cases; interruption cases; `test_finalization_failure_rolls_back_outputs_and_closes_run` injects registration and final commit failures. |
| Bounded cleanup and timer reentry prevention | Cleanup-error tests preserve primary/publication outcome; scheduler tests reject starts and concurrent drains, signal all workers first, share one deadline and retain timed-out workers; lifespan test prevents database disposal after timeout. |
| Repeat-run, empty-data and failure-injection regressions | `test_repeat_failure_recovery_and_empty_output`, explicit overwrite/no-clobber tests, real SQL and DuckDB connection closure cases, and failed-tick recovery. |
| Recovery documentation and observed defects | [Operator guidance](../execution.md#failure-recovery-34), architecture design, transaction retry tests, secondary-abort failure followed by startup recovery, and real-browser failure/correction/rerun. |

New integrated cases live in `tests/test_execution_failures.py`. Focused additions
also extend `test_artifact_registration.py`, `test_file_blocks.py`,
`test_scheduler.py`, and `test_execute_api.py`. No production executor or artifact
schema change was needed: existing dependent-skip and completed-sink contracts
passed their acceptance cases.

## Observed results

Windows, CPython 3.13.1 (`.venv`), Node 22.12.0, npm 11.8.0:

- Initial fault regressions: **10 failed, 78 passed**, reproducing cancellation
  publication, failed finalization, masked cleanup errors and recorder bookkeeping
  defects before the fixes.
- Final full backend suite: **881 passed**, 56 existing Starlette/SQLite
  deprecation warnings, 42.20 seconds.
- Ruff lint and format checks passed; **101 files** already formatted. Mypy
  passed for **101 source files**.
- `npm run check` in `frontend`: lint, formatting, typecheck, **169 tests across
  21 files**, and production build passed.
- Real API/browser monitoring and recovery scenario: **1 passed** using installed
  headless Microsoft Edge through `PLAYWRIGHT_CHROME_PATH`.
- Repository, documentation, release-plan and whitespace checks passed;
  repository-tool unittest discovery passed **16 tests**. The generated mobile
  failure screenshot was inspected after the automated overflow assertion.

The browser scenario creates isolated test metadata and a project workspace,
executes a successful control-only pipeline, then fails a real CSV source with
Select Columns and Parquet Sink dependents. It checks skipped blocks, absent
failed-run artifacts, history isolation, preserved draft edits and mobile overflow.
It writes a synthetic CSV, corrects the source through the configuration form,
saves revision 2 and clicks **Run saved pipeline**. The recovered run completes
all blocks, registers a two-row Parquet artifact, and leaves the failed run
available in history. This is automated browser evidence, not human signoff.

The first browser attempt could not launch because Playwright's Chromium binary
was absent. The Edge retry executed the scenario successfully in 5.2 seconds.
Windows runner teardown then required stopping only its spawned isolated API and
Vite processes; afterward Playwright exited successfully with `1 passed (2.2m)`.
This runner cleanup limitation is separate from the timer shutdown unit/API tests.
CI's Python 3.12 and Node 24 environments were not run locally; Node 22 is outside
the frontend's declared supported range even though these checks passed.

## Reproduction

From the repository root, using an environment with the locked dependencies:

```powershell
.\.venv\Scripts\python.exe -m ruff check --no-cache
.\.venv\Scripts\python.exe -m ruff format --check
.\.venv\Scripts\python.exe -m mypy --cache-dir .venv/mypy-34
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.venv/pytest-34-verification
.\.venv\Scripts\python.exe scripts/check_repository.py
.\.venv\Scripts\python.exe scripts/check_docs.py
.\.venv\Scripts\python.exe scripts/check_release_plan.py
.\.venv\Scripts\python.exe -m unittest discover -s scripts/tests -q
git diff --check
```

The final recorded full run used `--basetemp=.venv/pytest-34-final`. For focused
checks, pass `tests/test_execution_failures.py tests/test_file_blocks.py
tests/test_artifact_registration.py tests/test_scheduler.py tests/test_execute_api.py`
to pytest. All fixtures are synthetic; test workspaces are disposable.

From `frontend`, with ports 8000 and 3000 free:

```powershell
npm run check
$env:LPS_PYTHON = (Resolve-Path '..\.venv\Scripts\python.exe').Path
$env:LPS_METADATA_PATH = Join-Path (Get-Location) 'test-results/issue34-browser-metadata.sqlite3'
$env:LPS_WORKSPACE_ROOT = Join-Path (Get-Location) 'test-results/issue34-browser-workspaces'
$env:PLAYWRIGHT_CHROME_PATH = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
npm run test:standalone -- run-monitoring.spec.ts
```

Use the configured Playwright Chromium instead if installed, by omitting the Edge
override. The runner refuses to reuse existing servers. Do not point these test
variables at a real project database or workspace.

## In-app checks

These steps are a repeatable operator checklist, not a claim of an additional
human demonstration:

1. Create a test project and configure its workspace in Settings. Create
   `inputs/issue34.csv` in that project's workspace folder:

   ```csv
   sensor,reading
   A,10
   B,20
   ```

2. Connect CSV Source to Select Columns to Parquet Sink. Configure references
   `inputs/issue34.csv` and `issue34-result.parquet`, select
   `["sensor","reading"]`, and choose sink overwrite `error`. Save, wait for
   validation and run. Expect all blocks completed and a two-row artifact.
3. Run again. Expect `output_exists`, a failed sink and no new artifact for that
   run; the previous file must remain unchanged. Select `replace`, save and run
   again; expect a new successful run.
4. Point the source at a missing CSV, save and run. Expect a failed source,
   skipped dependents and no registered output for that run. Inspect its source,
   correct the reference, save and rerun. Prior failure evidence must remain.
5. Use a header-only CSV with the same columns. With overwrite `replace`, expect
   success, a valid schema and 0 rows. Restore the original CSV and expect 2 rows.
6. Check run identifiers, saved revision, block states, root errors, row counts
   and artifact links. Existing output bytes do not imply a failed run succeeded.

Commit/registration faults, publication checkpoints and timer races require the
backend injections; clicking Preview cannot establish those guarantees.

## Limits and assistance

An uncooperative block cannot be forcibly stopped by a Python thread. Shutdown's
deadline bounds waiting and reports unfinished cleanup; process isolation would
be needed to guarantee finite resource release. Complete files can remain without
metadata after publication followed by failure. Failed temporary deletion can
leave a sibling temporary file. Neither condition is silently treated as success.
Successful independent branches retain their outputs; no pipeline-wide rollback
is promised.

The user supplied the issue, requested the investigation and approved the plan.
OpenAI Codex produced the implementation, tests, documentation and recorded local
verification. No named teammate implementation or independent review is inferred.
