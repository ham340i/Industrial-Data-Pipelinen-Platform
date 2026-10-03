# Issue #11 test harness and CI verification

Scope: [Application test harnesses and real stack CI gates](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/11). Branch: `feature/11-test-harnesses-ci`, based on `62d02bb` (main after [PR #43](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/43) and [PR #44](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/44)). Validation date: 2026-10-03. Pull request: [#46](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/46). Hosted failure/pass run links and independent review are pending and must be linked here before the issue is closed.

## What this change adds

Existing application source, existing tests and the existing `Repository checks`, `Documentation checks` and `Frontend checks` jobs are unchanged. This change adds:

| Area | Addition |
|---|---|
| Backend configuration | `pyproject.toml` with Ruff (lint and format), mypy (strict for `app/`) and pytest settings scoped to `app/` and `tests/` |
| Backend dependencies | `requirements-dev.txt` (Ruff, mypy) and the generated, hash-pinned `requirements.lock` |
| Backend shared fixtures | `tests/conftest.py` with a `client` fixture |
| Backend contract tests | `tests/test_contract.py`: OpenAPI versioned routes, request boundaries, error envelope, correlation ID, unhandled-error redaction and CORS |
| Backend harness tests | `tests/test_harness_failures.py`: pytest, Ruff lint, Ruff format and mypy each fail on a broken synthetic fixture |
| Frontend harness tests | `frontend/src/test/harness.test.ts`: ESLint, Prettier, TypeScript and Vitest each fail on a broken synthetic fixture |
| CI | `Backend checks` job in `.github/workflows/ci.yml` |

## Acceptance evidence

| Acceptance criterion | Implementation | Verification |
|---|---|---|
| pytest and Vitest/React Testing Library harnesses with meaningful shell/contract tests | pytest configuration, shared fixture and 14 new contract test cases; the Vitest/Testing Library/MSW harness from issue #5 is reused | 24 backend tests and 22 frontend tests pass locally |
| Ruff/mypy and ESLint/Prettier against actual source | Ruff and mypy configured for `app/` and `tests/`; ESLint/Prettier from issue #5 cover `frontend/` | All four commands pass on the real source and fail on broken fixtures |
| Locked installs and useful dependency caching | `pip install --only-binary :all: --require-hashes -r requirements.lock` with the setup-python pip cache keyed on the lockfile; the frontend job already uses `npm ci` and the npm cache keyed on `package-lock.json` | Clean virtual environment installed from the lockfile, then all backend tests passed |
| Backend checks and frontend lint/tests/build using verified package commands | `Backend checks` job; existing `Frontend checks` job | Each command below was run locally; hosted results pending |
| Preserve documentation/repository checks and avoid empty-success placeholder tests | Existing jobs untouched; every new test asserts observable behavior; pytest uses strict markers/config and fails when nothing is collected | Repository, release-plan and documentation checks pass |

## Executed validation

Environment: macOS (arm64), Python 3.12.15, Ruff 0.16.10, mypy 2.4.0, pytest 8.4.2, Node 25.8.1, npm 11.11.0. The project targets Node 24; the local machine had Node 25, so the frontend results below are local evidence only and the Node 24 result must come from the hosted `Frontend checks` job.

Backend, from the repository root:

- `python -m pip install --only-binary :all: --require-hashes -r requirements.lock` in a new virtual environment: installed 34 pinned packages.
- `python -m ruff check`: passed.
- `python -m ruff format --check`: 12 files already formatted.
- `python -m mypy`: no issues in 12 source files.
- `python -m pytest`: 24 passed (5 existing API tests, 14 contract cases, 5 harness tests).

Frontend, from `frontend/`:

- `npm ci --ignore-scripts`: installed from `package-lock.json`.
- `npm run check`: ESLint, Prettier, TypeScript, 22 Vitest tests (18 existing, 4 harness) and the production build passed.
- Playwright browser smoke tests were not run locally for this change; they remain in the hosted `Frontend checks` job.

Repository:

- `python3 scripts/check_repository.py`, `python3 scripts/check_release_plan.py`, `python3 scripts/check_docs.py` and `python3 -m unittest discover -s scripts/tests`: passed (14 tool tests).

## Failure propagation

Controlled tests of the harness run on every CI run. Each writes a synthetic fixture to a temporary directory, runs the real tool in a subprocess and asserts a non-zero exit code; a passing control fixture proves the tool actually ran.

| Check | Broken fixture | Asserted result |
|---|---|---|
| pytest | `assert 1 + 1 == 3` | exit 1, `1 failed` |
| pytest | directory with no tests | exit 5 |
| Ruff lint | unused import | exit 1, `F401` |
| Ruff format | unformatted assignment | exit 1 |
| mypy | `str` returned from an `int` function | exit 1, `return-value` |
| ESLint | unused variable | exit 1, `no-unused-vars` |
| Prettier | unformatted statement | exit 1 |
| TypeScript | `string` assigned to `number` | non-zero, `TS2322` |
| Vitest | `expect(1 + 1).toBe(3)` | exit 1, `1 failed` |

Manual local demonstration on 2026-10-03, each change reverted afterwards:

- Changing one expected value in `tests/test_contract.py`: `python -m pytest` reported `1 failed, 23 passed` and exited 1.
- Adding a temporary file with an unused import and a mistyped assignment under `tests/`: `python -m ruff check` exited 1 (`F401`) and `python -m mypy` exited 1 (`assignment`).
- Changing one expected value in `frontend/src/test/harness.test.ts`: `npm test` reported `4 failed | 18 passed` and exited 1.

Hosted demonstration (a deliberately failing commit turning the Actions run red, followed by the restored commit turning it green): pending. Link both runs here.

## Design tradeoffs

- **Lockfile format.** A universal, hash-pinned `requirements.lock` compiled with uv installs with plain pip on Linux, macOS and Windows, so contributors do not need uv unless they change dependencies. A Poetry/uv project file would have required restructuring `requirements.txt`, which predates this issue.
- **Scope of Ruff and mypy.** They cover `app/` and `tests/`. `scripts/` is standard-library repository tooling written in a different style and already checked by `scripts/check_repository.py`; bringing it under Ruff would mean reformatting files outside this issue.
- **Rule set.** Ruff uses `E`, `F`, `W`, `B` and `UP`. Import sorting (`I`) is left off because the existing files would need reordering.
- **mypy strictness.** `app/` is checked in strict mode. Tests may omit `-> None`, because the existing API tests do; their bodies are still type-checked.
- **Wheels only.** The locked install passes `--only-binary :all:` so pip never runs a package setup script. SonarCloud flagged the first version of the CI step on PR #46 for omitting it. Every locked package publishes a wheel for Python 3.12 on Linux x86_64 and macOS arm64 (verified with a clean install and `pip download`).
- **Separate CI steps.** The backend job runs one tool per step so the failing check is visible in the Actions summary.
- **Harness tests use subprocesses.** This exercises the same commands and exit codes that CI depends on instead of mocking them.

## Findings and limitations

- `app/main.py` imports `Awaitable` and `Callable` without using them. Ruff reports this as `F401`. Because this issue adds checks without editing application source, `pyproject.toml` ignores `F401` for that one file; the entry should be removed when the file is next changed.
- Error responses carry the `X-Correlation-ID` header twice, once from the middleware and once from the error response. The contract test compares the set of header values so it does not hide or depend on this.
- The frontend health client requests `/health`, while the API serves `/api/v1/health`. The frontend tests mock the request, so no existing test exercises the two together. This needs a decision by the owners of issues #5 and #6.
- Starlette emits deprecation warnings for `HTTP_422_UNPROCESSABLE_ENTITY` and for using `httpx` with its test client. They do not fail the run.
- Dependabot is configured for GitHub Actions only, so `requirements.lock` and `package-lock.json` are not updated automatically.
- `Backend checks` and `Frontend checks` are not yet required by branch protection. A repository administrator must add them after the first successful hosted run.
- End-to-end testing of this behavior is not applicable to this tooling task until the Iteration 4 acceptance workflow.

## AI assistance

Tool: Claude Code (Anthropic). Purpose: configuration, tests, CI job, documentation and the local verification recorded above. Human contribution observed: task direction, the instruction to leave existing code unchanged, and the issue requirements. Human code review and independent verification: pending.
