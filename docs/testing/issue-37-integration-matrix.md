# Issue #37 verification

Scope: an API/engine/SQLite integration matrix over the production block
catalog, the compatibility fixes it surfaced, and shared response fixtures
checked by both the backend and the Builder's response parsers.
Branch: `feature/37-block-integration-matrix`, based on `main` after PR #82.
Issue: [#37](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/37).

Every matrix case drives the real FastAPI application through `TestClient`
over a real SQLite metadata database and a real per-project workspace folder
prepared by the project API, using the same validate → save → execute →
run status → artifact path the Builder uses. No block is called directly.

## Acceptance criteria → tests

| Criterion | Tests |
|---|---|
| API/engine/SQLite integration fixtures for validate/execute/preview/status/output paths | `tests/integration_support.py` (`Workbench`: synthetic CSV/JSON/Parquet/SQLite writers, graph builders, one helper per HTTP step) and the `bench` fixture in `tests/conftest.py` |
| Representative source → transform → quality → sink compatibility cases | `test_every_source_publishes_through_every_sink` (4 sources × 2 sinks), `test_select_rename_filter_cast_sort_chain_publishes_typed_rows`, `test_two_sources_fan_in_through_join_and_aggregate`, `test_passing_quality_gates_keep_the_run_publishing` (4 gates), `test_required_gate_failure_blocks_publication_and_registers_nothing`, `test_optional_gate_warns_and_still_publishes`, `test_run_status_paths_list_filter_and_scope_the_matrix_runs`, `test_preview_and_execute_agree_on_the_same_project_folder` |
| Malformed definitions, schema mismatches and timeout/failure responses | `test_malformed_definitions_are_refused_at_save_without_persistence` (5 shapes), `test_validate_reports_block_config_and_port_problems_without_running`, `test_saved_invalid_pipeline_cannot_execute_and_creates_no_run`, `test_declared_csv_schema_that_disagrees_with_the_file_fails_the_source`, `test_sql_result_columns_must_match_the_declared_order`, `test_downstream_type_contract_violations_fail_the_offending_block`, `test_strict_schema_gate_rejects_an_untyped_header_only_csv`, `test_missing_input_file_fails_without_leaking_the_workspace_path`, `test_sql_work_budget_exhaustion_is_a_structured_query_failure`, `test_execute_without_a_workspace_records_a_failed_run_not_a_crash`, `test_preview_time_budget_exhaustion_is_a_structured_timeout`, `test_preview_refuses_gates_sinks_and_unknown_projects_explicitly` |
| Fix observed adapter/contract mismatches with targeted regression tests | see [Mismatches found and fixed](#mismatches-found-and-fixed); regressions: the four `*-parquet` matrix cases, `test_optional_gate_warns_and_still_publishes`, `test_sink_creates_a_missing_output_folder_inside_the_project` |
| Ruff/mypy/ESLint/Prettier and real test/build gates run in Actions and capture results | unchanged gates in `.github/workflows/ci.yml`; pytest and Vitest now write JUnit XML that the backend and frontend jobs upload as workflow artifacts (`backend-test-results`, `frontend-test-results`) even when a step fails |

Frontend/backend contract: `tests/test_integration_contracts.py` captures the
real `execute`, `GET /runs/{id}` (succeeded and failed), run list, artifact
metadata, artifact query, validation report and error-envelope responses into
`tests/fixtures/contracts/*.json` and asserts the live responses keep the
recorded shape (keys and JSON types). `frontend/src/api/contracts.test.ts`
feeds the same files through `parseRun` and `parseReport`, so a response
change that the Builder cannot parse fails CI on whichever side drifted.
Regenerate after an intentional change with
`LPS_UPDATE_CONTRACT_FIXTURES=1 python -m pytest tests/test_integration_contracts.py`
and commit both the fixtures and the parser change together.

## Mismatches found and fixed

1. **Executed artifacts could not be queried through the API.** The execute
   API (#29) runs sinks with `workspace_root=<root>/<project id>`, so a
   Parquet sink publishes to `<root>/<project id>/<resource_ref>`. The
   artifact query endpoint (#28) resolved `resource_ref` beneath the bare
   workspace root, so every artifact produced by a real run answered
   `409 artifact_unavailable`; only the unit tests, which placed files
   directly under the root, passed. `app/artifacts/api.py` now resolves the
   artifact inside the producing run's project folder. The existing
   `tests/test_artifact_api.py` helper was moved to register files where
   execute actually publishes them, and `docs/artifacts.md` /
   `docs/architecture/artifact-governance.md` describe the project-scoped
   path.
2. **A sink into a missing output folder failed as an atomic-publication
   error.** `prepare_project` creates only `inputs/`; a sink configured with
   `outputs/result.parquet` failed with `write_failed` ("Output could not be
   published atomically"), which does not tell the operator what to do.
   `FileSink` now creates the missing parent folder before writing. This is
   safe because `resource_path` has already proven the resolved target lies
   inside the project workspace; traversal, suffix and aliasing checks are
   unchanged.

Behaviours observed and deliberately kept, with tests that pin them:

- Executing a saved pipeline while no workspace is configured records a
  failed run with `workspace_required` rather than refusing the request, so
  the failure appears in run history like any other block failure.
- SQLite has no boolean storage class: a SQL source must declare such a
  column as `integer`; the matrix's SQL case expects `1`/`0`.
- A preview of a sink names the first unsupported ancestor on its input path
  (the quality gate), because capability is checked along the whole path.
- Saving accepts drafts that do not validate (#21); the execute API refuses
  them with `422` and the first diagnostic, creating no run.

Mistakes in the matrix itself that running it caught before any fix was
attributed to the product: a second run of a no-clobber CSV sink fails with
`output_exists` by design (the status-path test now uses `overwrite:
replace`); pipeline names are unique per project (the helper now generates a
fresh name); and the 422 message for malformed definitions legitimately
contains a `/` character, so the leak assertion now checks for the real
workspace path instead.

## Observed results

macOS, Python 3.12.15 virtual environment, Node 22.21.0, November 12, 2026,
revision: this branch before the pull request was opened.

- `python -m pytest -q`: **880 passed** (39 new: 18 in
  `test_integration_matrix.py`, 17 in `test_integration_failures.py`, 4 in
  `test_integration_contracts.py`). The new modules run in under two seconds.
- `python -m ruff check`: passed. `python -m ruff format --check`: passed.
  `python -m mypy`: no issues in 104 source files.
- `npx vitest run src/api/contracts.test.ts`: 4 passed. `npx eslint`,
  `npx prettier --check` and `npx tsc --noEmit` on the touched frontend
  files: passed.
- `python3 scripts/check_repository.py` and `python3 scripts/check_docs.py`:
  passed.

Hosted CI results, including the uploaded JUnit artifacts, are recorded on
the pull request. No manual UI demonstration applies: the matrix is
API-level by design, and the UI side is covered by the parser contract tests
above; the Iteration 4 acceptance workflow (#38) exercises the integrated UI.

## Limitations

- The matrix uses synthetic fixtures of a few rows. It proves contract
  compatibility, not throughput; see the [performance plan](../performance/performance-plan.md).
- Timeout coverage is deterministic rather than wall-clock based: the SQL
  case exhausts the block's VM-step budget and the preview case sets the
  time budget to zero. Real slow inputs are not simulated.
- Timer-triggered execution is covered by the #29 suite and was not
  duplicated here.
