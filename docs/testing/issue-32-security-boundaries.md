# Issue #32 verification

Scope: harden the file, SQL and configuration security boundaries by
probing the existing controls, fixing the gaps that probing actually found,
and pinning the result with adversarial regression tests. No identity
platform or industrial network access is assumed.
Branch: `feature/32-security-boundaries`, based on `main` at `c4cc967`.
Issue: [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32).

## Gaps found and fixed

Each gap was reproduced before the change; the regression test fails or
the reproduction succeeds against the previous code.

| Gap | Reproduction before the fix | Fix |
|---|---|---|
| Run-log redaction missed compound keys | `redact("client_secret=abc123")`, `db_password=`, `access_token=`, `refresh_token:`, `{"db_password": "s3"}`, `passphrase=`, `private_key=` and `Authorization: Basic …` were returned unchanged | `app/runs/redaction.py`: keys may carry a prefix but must end with a credential word; non-Bearer Authorization schemes masked |
| Timer tick failures logged exception text | `logger.exception` wrote the traceback and message (paths, bound SQL values) | `app/runs/scheduler.py` logs the exception type only, like `execute_revision` |
| Divergent credential-key lists | `client_secret`, `db_password`, `github_token`, `private_key` were accepted into saved definitions; so were `postgres://user:pass@host` and `~/file` values | `app/secret_policy.py` shared by `require_public_json`, `portable_definition` and `SqlSourceConfig` |
| Standalone SQLite reader was unconfined | `read_sqlite_source` opened any absolute or `~` path, echoed it in errors, and `SELECT randomblob(1000000000)` allocated 1 GB | Workspace-relative `database_path`, resolution inside `workspace_root`, path-free errors, `query_only`, length/step/row/byte budgets |
| Parquet decoding was unbounded | A 442-byte file (dictionary page repeating a 50 KB string for 2,000 rows) was accepted with `max_bytes=1048576` and decoded to 100,000,000 bytes; its writer-declared page size was only ~50 KB | Metadata row/cell check, declared-page budget, dictionary-aware decoded-size check before expansion (execution and preview) |
| DuckDB artifact connection was unlocked | Only the fixed SQL template restricted file access and extension loading | `locked_connection`: no extension install/autoload, `allowed_paths` = the artifact, external access off, configuration locked |
| Dependency updates covered only Actions | Dependabot watched `github-actions` only; audits had never been recorded | pip and npm ecosystems added; in-range fixes applied (see below) |

Controls probed and found sound (now pinned by tests, not changed):
`resource_path` traversal/symlink confinement for sources and sinks, project
folder aliasing, the lexical read-query policy, the SQLite authorizer
(`pragma_*` table-valued functions and `load_extension` are denied), fixed
public error messages, and loopback-only Compose publishing.

## Acceptance criteria → tests

| Criterion | Tests |
|---|---|
| Workspace path confinement including traversal/symlink policy | `tests/test_security_boundaries.py`: `test_traversal_and_machine_paths_are_refused_before_persistence` (7 refs), `test_symlinked_inputs_folder_cannot_read_outside_the_project`, `test_symlinked_input_file_is_refused_by_preview_and_execute`, `test_sink_cannot_write_through_a_symlinked_output_folder`, `test_sink_replace_cannot_overwrite_a_symlinked_target_file`; `tests/test_sql_source_execution.py`: `test_database_path_must_be_a_workspace_relative_database` (12 paths), `test_symlink_escaping_the_workspace_is_refused_without_its_path`; existing unit coverage in `tests/test_file_blocks.py` and `tests/test_integration_failures.py` |
| Read-only SQL/artifact-query restrictions and bounded inputs | `test_sql_write_queries_are_refused_at_validation` (5), `test_sql_introspection_and_extensions_are_refused_at_runtime` (3, database hash unchanged); `test_engine_budgets_stop_resource_exhausting_queries`, `test_row_and_file_budgets_are_enforced`, `test_query_and_parameters_are_bounded`; `tests/test_artifact_query.py`: `test_locked_connection_reads_only_the_resolved_artifact`, `test_locked_connection_refuses_reconfiguration_writes_and_extensions` (5); `tests/test_file_policy.py`: `test_parquet_dictionary_bomb_is_refused_before_expansion`, `test_parquet_large_declared_pages_are_refused_before_reading`, `test_parquet_row_count_is_checked_from_metadata_before_decoding`, `test_dictionary_strings_within_budget_decode_to_plain_values`, `test_decoded_bytes_counts_dictionary_expansion`, and the budget boundaries `test_parquet_decode_budget_is_sixteen_times_capped_at_one_gib` (5), `test_parquet_declared_pages_just_within_and_just_over_the_budget`, `test_parquet_declared_pages_at_the_one_gib_cap` (2); `tests/test_file_preview.py`: `test_parquet_preview_refuses_dictionary_expansion_before_decoding`; `test_oversized_input_fails_with_a_limit_code`, `test_malformed_input_fails_without_echoing_its_contents` |
| Env/example separation; no credentials in saved/exported definitions | `tests/test_env_examples.py` (6): example files hold only non-credential names/values, `.env*` ignored except examples, both Docker contexts exclude `.env`, `Settings` has no credential fields; `tests/test_secret_policy.py` (50); `tests/test_pipeline_api.py`: `test_credentials_never_reach_saved_definitions` (5, create and update, nothing persisted). Definitions are exported only through the pipeline GET responses, which return what `PortableJSON` admitted at write time |
| Redact sensitive error/log fields; review actual dependency findings | `tests/test_run_redaction.py`: `test_compound_keys_and_auth_schemes_are_masked` (12), `test_lookalike_words_are_not_redacted` (4); `tests/test_scheduler.py`: `test_failed_tick_logs_the_exception_type_without_its_text`; path-free error assertions throughout `tests/test_security_boundaries.py`; [dependency review](#dependency-review) |
| Abuse/regression fixtures and remaining threat-model decisions | `tests/test_security_boundaries.py` (21 API-level cases); [accepted risks](../security/security-plan.md#accepted-risks-and-threat-model-decisions) |

## Dependency review

Run on this branch on 2026-11-15 with pip-audit 2.10.1 against
`requirements.lock` and npm 10.9.2 against `frontend/package-lock.json`.

| Finding | Reachability | Action |
|---|---|---|
| certifi 2026.7.22 (PYSEC-2026-4320) | Runtime (httpx) | Upgraded to 2026.10.23 inside the declared range |
| opentelemetry-api 1.45.0 (CVE-2026-114603, CVE-2026-126360) | Runtime (FastAPI) | Upgraded to 1.45.2 inside the declared range |
| pytest 8.4.2 (PYSEC-2026-1845, predictable `/tmp/pytest-of-{user}` on multi-user UNIX) | Test-only | **Open.** Fix is 9.0.3, outside `pytest>=8,<9`; needs a separate major upgrade |
| follow-redirects 1.16.0 (high) | axios Node adapter; absent from the built browser bundle | Lockfile fix to 1.16.3 |
| vite 8.3.1 (high, dev server/launch-editor) | Development server only | Lockfile fix to 8.3.8 |
| undici 8.11.2 (high) | Dev tooling | Lockfile fix to 8.12.4 |
| zod 4.6.5 (high, memory on oversized collections) | Dev tooling (transitive) | Lockfile fix to 4.6.7 |
| minimatch via typescript-eslint/eslint (7 moderate) | Lint only | **Open.** The only offered fix is a typescript-eslint downgrade |

Python locks were regenerated with
`uv pip compile --universal --generate-hashes --python-version 3.12 requirements-dev.txt -o requirements.lock --upgrade-package certifi --upgrade-package opentelemetry-api`,
which changed only those two pins. The npm lock was changed with
`npm audit fix --package-lock-only --ignore-scripts`; `package.json` is
unchanged. After the change pip-audit reports only pytest and npm audit
reports 7 moderate, 0 high.

## Commands and results

Environment: macOS 26.5.2 (arm64), Python 3.13.4 in a local virtualenv
installed from `requirements.lock` with `--require-hashes` (CI uses 3.12),
Node 22.16.0 / npm 10.9.2 (CI uses Node 24). Revision: the branch head of
the PR.

```text
python -m ruff check                      All checks passed!
python -m ruff format --check             passed
python -m mypy                            Success: no issues found in 112 source files
python -m pytest                          1052 passed (913 before this branch; +139 new)
python3 scripts/check_repository.py       Repository checks passed (456 files)
python3 scripts/check_docs.py             Documentation checks passed
python3 scripts/check_release_plan.py     passed
python3 -m unittest discover -s scripts/tests   Ran 16 tests, OK
(frontend) npm ci --ignore-scripts && npm run check
                                          lint, format, typecheck, 209 tests, build: exit 0
```

The backend, repository and documentation rows were rerun after the
review follow-up below. The frontend row is from the first round: the
follow-up changed no frontend file. CI reruns every job on the new head.

E2E: not applicable. No Builder UI behavior changed; the Playwright suites
were not rerun locally (`npm run check` covers the frontend unit tests and
the production build with the updated lockfile). CI runs the browser jobs.

Manual demonstration on synthetic fixtures (scratch directory, not
committed): the redaction probe above, the SQLite authorizer probe
(`pragma_database_list`, `pragma_table_info`, `pragma_compile_options` and
`load_extension` denied; `randomblob(1e9)` allowed before the fix), the
Parquet bomb (accepted before, `file_limit` after) and the DuckDB lock probe
(second file, `COPY`, `ATTACH`, `INSTALL` and `SET enable_external_access`
all refused).

## Review follow-up (PR #88)

`menaboulus`'s rubric review of
[PR #88](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/88)
at `a5d8c18` asked for structural fixes, AI declarations and a boundary
test. Each item became its own commit; behavior is unchanged except
where stated.

| Review item | Change | Evidence |
|---|---|---|
| Put the dictionary-size check in its own helper module | `app/blocks/parquet_decode.py` holds the decode budget, declared-page sum, dictionary-aware decoded size and the shared Arrow → SDK type map. Execution and preview both import it | Existing Parquet tests unchanged and passing |
| `files.py` 734 lines (limit 500) | Writers moved to `app/blocks/file_sinks.py`; CSV preview moved to `app/blocks/csv_preview.py` | `files.py` 412 lines; largest new module 304 |
| Complexity of `CsvSource._preview` (17), `JsonRecords.__next__` (22), `preview_json` (16), `preview_parquet` (23) | Split into one helper per step; the JSON preview moved to `app/blocks/json_preview.py` so `file_preview.py` stays under 500 lines | Highest complexity in the touched block modules is 8 (ruff C901); none over 50 statements (PLR0915) |
| `NotImplementedError` placeholders | `FileSource._read` and `FileSink._write` are `@abstractmethod` | `test_file_block_hooks_are_abstract` (2) |
| `print` in `scripts/check_repository.py` | Comment explains it is the CLI's report | Repository checks pass |
| AI level missing from file headers | `# AI contribution: <level>` on every Python file the PR touches, from `git blame` shares | Per-file list in [AI_USAGE.md](../../.github/AI_USAGE.md#issue-32-file-sql-and-configuration-security-boundaries) |
| Boundary test for the Parquet declared-page budget | Tests at the 16× edge (real file) and at the 1 GiB cap (declared size substituted, real comparison) | 8 new cases; a `>=` mutation and a removed cap are each caught |

Two drifts were checked for while splitting `preview_parquet`: the check
order, where a corrupt file still reports `unsupported_type` before
`invalid_parquet`; and the sample slicing, where a footer that
under-declares its rows still fails the metadata/sample comparison. Both
were kept.

## AI assistance

Tool: Claude Code (Claude Opus 5.5). Used to probe the existing controls,
draft the fixes, tests and this record, and run the checks above.
Human contribution: issue owner direction, scope decisions and review.
Verification: every fix has a regression test; fail-before was confirmed
for the scheduler test and by direct reproduction for redaction, SQLite,
Parquet and DuckDB. Independent student review is pending.
