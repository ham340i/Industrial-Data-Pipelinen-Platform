# Testing plan and continuous integration

## What is tested and how

| Level | Tool | What it covers | Where |
|---|---|---|---|
| Backend unit | pytest | Each block (golden outputs, missing columns, invalid casts, nulls, overflow), pipeline model, validation rules, redaction, scheduler | [tests/](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_transform_blocks.py) |
| Backend API | pytest with FastAPI's test client | Every route's success and error contract, including the error envelope and correlation ID | [tests/test_api.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_api.py), [tests/test_contract.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_contract.py) |
| Backend integration | pytest with a real SQLite file and real Parquet files in a temporary folder | API to engine to blocks to metadata to files, in one process; failure propagation and clean-up | [integration matrix](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_integration_matrix.py), [failures](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_integration_failures.py), [contracts](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_integration_contracts.py) |
| Security | pytest | Path traversal and symlink escape, unsafe SQL, credential redaction and the shared secret policy, Parquet decompression bombs, locked artifact queries, workspace containment | [file blocks](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_file_blocks.py), [file policy](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_file_policy.py), [SQL source](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_sql_source_contract.py), [redaction](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_run_redaction.py) |
| Frontend unit | Vitest and React Testing Library | Components, editor state, response parsers | [frontend/src](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/Canvas.test.tsx) |
| Frontend to API contract | Vitest with MSW; captured API responses shared as fixtures with the backend tests | The client rejects malformed payloads and accepts exactly what the API returns | [contracts test](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/api/contracts.test.ts) |
| Browser smoke | Playwright (Chromium) | The production build loads and reaches the API | [browser-tests](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/browser-tests) |
| Deployed stack | Playwright against Docker Compose, and a standalone run on Linux and Windows | Real services, browser connectivity, metadata persistence across restart | [compose-tests](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/compose-tests), [standalone-tests](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/standalone-tests) |

Mocks and stubs: MSW intercepts HTTP in frontend tests; pytest's `monkeypatch` and `unittest.mock` replace clocks, filesystem calls and failing collaborators in backend tests. Integration tests use real SQLite, Polars, Arrow and DuckDB, not mocks.

## Results at Release 1

- Backend: 1,070 tests pass (one Linux-only benchmark test is skipped elsewhere). Line coverage measured with `pytest --cov=app` is 96%. Coverage is measured on demand and is not yet a CI gate.
- Frontend: 226 unit and HTTP-mock tests pass.
- Every closed Release 1 feature has at least one test of its behaviour and one failure or boundary case. Per-feature evidence is in [docs/testing](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/testing/testing-plan.md).
- End to end: the author, preview, execute and output-inspection workflow and the SQL workflow run in Playwright against the real stack ([#31](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/31), [release-tests](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/release-tests/author-preview-execute.spec.ts)).
- Security: adversarial regression tests for every boundary probed in [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32) ([test_security_boundaries.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_security_boundaries.py)).
- Performance: the workload benchmark checks its outputs against an independent oracle ([#35](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/35), [test_workload_benchmark.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/tests/test_workload_benchmark.py)).

Performance testing is described on the [Performance](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Performance) page.

## Continuous integration

GitHub Actions runs on every pull request and every push to `main` ([ci.yml](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/.github/workflows/ci.yml), [documentation-check.yml](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/.github/workflows/documentation-check.yml)).

| Job | Steps |
|---|---|
| Repository checks | Configuration and syntax, limited secret patterns, release-plan consistency, repository-tool tests |
| Documentation checks | Local links, anchors and whitespace in every Markdown file |
| Backend checks | Install the hash-pinned lock, Ruff lint, Ruff format check, mypy strict, pytest; upload JUnit results |
| Frontend checks | `npm ci`, ESLint, Prettier, TypeScript, Vitest, production build, Chromium smoke; upload JUnit results |
| Compose workspace smoke | Build both images, start the stack, browser test, restart and check persistence, tear down |
| Standalone workspace smoke | Same without containers, on Ubuntu and Windows |

A failing job blocks the merge. Superseded runs on the same branch are cancelled.

## Code review and approval

- `main` is protected: one approving review from someone other than the author, an up-to-date branch, passing required checks and resolved conversations. Administrators are not exempt.
- Each work item names its reviewer in advance, so review load is spread across the team.
- An approval must state what was examined, for example the validation paths, the tests, or the authorization check. A bare approval does not count as a review.
- A requested change is fixed or answered in the thread before merge.
- Pull requests are merged with a merge commit, never squashed, so each author's commits remain visible.
- Every pull request states its AI contribution level and the files that received substantial AI assistance ([template](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/.github/PULL_REQUEST_TEMPLATE.md)).

Known gap: branch protection currently requires only the repository and documentation checks. The backend, frontend and Compose jobs run on every pull request but are not yet marked as required; the repository owner must add them.
