# Issue #28 artifact governance verification

Status: local branch verification in progress on
`feature/28-parquet-artifact-query`. Independent review, hosted CI, PR approval
and merge are not yet recorded.

## Acceptance mapping

| Acceptance criterion | Evidence |
|---|---|
| Register artifact identity, schema, row count and producing run/revision | `test_completed_sink_registers_bounded_metadata_and_provenance`; `test_executor_output_is_registered_and_queryable_by_artifact_id` |
| Expose metadata and bounded local DuckDB query/read endpoint | `test_metadata_exposes_provenance_without_a_machine_path`; `test_query_returns_only_the_requested_bounded_projection` |
| Restrict queries to registered artifacts and supported read-only operations | `test_policy_rejects_sql_unknown_columns_and_oversized_requests`; `test_only_registered_parquet_artifacts_can_be_queried`; API safe-error cases |
| Persist metadata only after successful artifact publication | `test_failed_sink_does_not_register_an_artifact`; existing atomic sink tests; executor integration |
| Document type boundaries and verify provenance | [Design](../architecture/artifact-governance.md); typed/null round-trip and producing revision assertions |

Additional cases cover migration of populated databases, unknown legacy schema,
unsafe stored references, missing files, CSV rejection, duplicate projection
names, row/column/cell limits, pagination look-ahead, true sink row counts and
immediate/timer workspace propagation.

## Observed focused checks

Windows, Python 3.12, hash-pinned dependencies, November 2, 2026:

- Registration/query/run tests: **20 passed**.
- Artifact API/query/registration/run API/telemetry: **38 passed** with five
  existing Starlette 422-constant warnings.
- Executor integration/scheduler/pipeline API: **21 passed** with five existing
  Starlette warnings.
- Metadata plus query migration checks: **56 passed** with five Python 3.12
  SQLite datetime-adapter warnings.
- Complete backend suite: **720 passed, 1 skipped, 47 warnings** in 47.81
  seconds. The skip is the existing Windows symbolic-link restriction.
- Ruff check passed, Ruff format reported **86 files already formatted**, and
  mypy reported no issues.
- Documentation, release-plan, repository and repository-tool checks passed.

Repository/document scripts are checked separately below. Hosted CI remains to
be recorded after the pull request is opened.

## Reproduction

```powershell
python -m pytest tests/test_artifact_registration.py `
  tests/test_artifact_query.py tests/test_artifact_integration.py -q `
  -p no:cacheprovider
python -m pytest tests/test_artifact_api.py tests/test_run_api.py `
  tests/test_pipeline_api.py -q -p no:cacheprovider
python -m ruff check --no-cache
python -m ruff format --check --no-cache
python -m mypy --cache-dir "$env:TEMP/issue-28-mypy"
```

All fixtures use synthetic data. Browser E2E remains assigned to the Iteration
4 integrated workflow; Issue #28 exposes backend contracts only.

AI assistance: I explained Issue #28, the required behavior and what needed to
be done. Codex implemented the code, tests and documentation at my direction. I
then manually ran the recorded focused and full verification commands and
checked their results. Independent teammate review remains pending.
