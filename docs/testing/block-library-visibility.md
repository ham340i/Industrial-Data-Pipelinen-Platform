# Block library visibility verification

Scope: hide Synthetic Add Constant from new authoring choices while retaining its SDK example, exact-version runtime registration and saved-pipeline metadata. This record covers that initial cleanup; the subsequent production preview implementation has its own [issue #26 verification](issue-26-preview.md) and [updated plan](../planning/issue-26-preview.md).

## Environment and checks

Local checks run on November 10, 2026 on Windows using Node 24.22.2, headless Microsoft Edge through Playwright 1.63.0 and the existing `.venv` Python 3.13.1. The repository targets Python 3.12; this local verification does not establish a Python 3.12 CI result.

- Frontend unit tests: `node node_modules/vitest/vitest.mjs run` from `frontend`: 101 passed.
- Backend suite: `python -m pytest -p no:cacheprovider --basetemp <fresh ignored directory>`: 708 passed. A final strengthening of the catalog assertions was followed by a focused rerun: all 3 catalog tests passed. Starlette and SQLite deprecation warnings remain.
- Frontend ESLint and `npm run build` (TypeScript check plus production Vite build): passed. Prettier checks were scoped to changed frontend files; this record does not claim a clean repository-wide formatting check.
- Backend Ruff lint/format checks on changed Python files: passed. Mypy: all 75 configured source files passed; the final catalog-test changes also passed a focused recheck.
- Real API browser regression: 4 passed (library visibility/saved example, configuration, pipeline persistence, validation). The run used an isolated SQLite database and output directory under ignored `frontend/test-results`, reusing the existing Vite server on port 3000. The initial default browser runner stalled without output; a temporary local config isolated its output and allowed reuse of Vite. No committed runner configuration was changed.
- Documentation links/whitespace and release-plan consistency checks: passed. The release plan retains 34 items and its existing ownership, estimates and dependency graph.

The frontend checks cover production keyboard creation/deletion, hidden-library search and stale drag payload rejection, an all-hidden catalog, malformed visibility metadata, older metadata, and existing example node display/configuration/connections. Backend checks cover catalog visibility, production registry resolution, execution/preview of the retained example, SDK contracts, validation and saved-pipeline round trips.

Real API browser scenarios use Row Count for new-node configuration, graph connections and persistence. A separate scenario seeds an existing Synthetic Add Constant pipeline through the API and verifies reopening and editing it without offering the block in the library.

To repeat the four browser cases with the normal standalone configuration, stop any existing server on its test ports, set `LPS_PYTHON` to the development interpreter, set `LPS_METADATA_PATH` to a fresh test database and run from `frontend`:

```powershell
node node_modules/@playwright/test/cli.js test --config playwright.standalone.config.ts --output test-results/library-regression block-library.spec.ts configuration.spec.ts pipelines.spec.ts validation.spec.ts
```

Use Node 24 on `PATH` and install Playwright Chromium, or set `PLAYWRIGHT_CHROME_PATH` to the installed browser. The local verification used the same four cases with ignored `test-results/library-visibility.config.ts`, which preserves the normal test settings while setting explicit paths, isolating output and reusing Vite. The test API was started and stopped by Playwright; the pre-existing Vite server was left running.

## Assistance and review

Tool: OpenAI Codex. The user approved the cleanup and documentation scope. Codex implemented the change, tests and documentation and ran the reported local checks. Independent human review, GitHub Actions and issue #26 preview acceptance are not claimed.
