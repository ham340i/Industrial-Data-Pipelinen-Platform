# Workspace and run UI: branch verification

Verified November 17, 2026 (America/Toronto) for `fix/miscellaneous` at
`f905232`, including its preceding commits `86b2e66` and `035f42a`, plus the
browser-test corrections described below. This records local evidence; hosted
CI, independent teammate review, and stakeholder acceptance remain pending.

## CI failures prevented

Six browser specifications still expected UUID data folders, a separate Save
workspace button, the removed settings-status container, inline run events,
and successful/skipped block cards. They now use the approved behavior:

- Seed files in the saved pipeline's named folder, after folder allocation.
- Save the source before previewing in the release authoring scenario, and
  reselect it after saving resets editor selection. Check subsequent revisions.
- Confirm workspace paths with Enter; check saved precedence through the API.
- Inspect failed blocks only, and locate successful nodes on the canvas.
- Assert the release graph's seven block row counts through persisted API
  evidence while checking the compact result and Parquet rows in the UI.
- Scope immediate-result locators to avoid matching both execution and history.
- Check renamed pipeline outputs in the renamed data directory.

Changed specifications: `frontend/standalone-tests/{preview,recovery,run-monitoring,workspace}.spec.ts`
and `frontend/release-tests/{author-preview-execute,sql-workflow}.spec.ts`.
No test was disabled and the release row-count/output oracle remains enforced.

## Environment and dependency installation

Windows; isolated CPython 3.12.16 and Node 24.22.3, matching CI's major/minor
runtime requirements. Runtime downloads and test data remain in ignored
`test-results/` directories. Python dependencies were installed from
`requirements.lock` with `--only-binary :all: --require-hashes`. Frontend
`npm ci --ignore-scripts --no-audit --no-fund` completed in an isolated checkout
using the committed frontend lockfile. Application dependencies and lockfiles
were not changed.

Browser verification uses Playwright's pinned Chromium 153.0.8010.12, build
1243. Earlier exploratory browser checks also passed with Microsoft Edge.
Real API and frontend servers use isolated metadata/workspaces on loopback
ports 8015/3015 because the developer's application occupies 8000/3000. A
temporary, ignored launcher sets the test frontend's allowed origin. The
tracked browser scenarios are unchanged by that launcher. Only the OS folder
dialog is stubbed in the workspace browsing scenarios; persistence, execution,
artifact queries, and log downloads use the real API.

## Results

| CI check | Local result |
| --- | --- |
| `python scripts/check_repository.py` | Passed: 511 tracked files at the initial check |
| `python scripts/check_docs.py` | Passed: 208 tracked Markdown files at the initial check |
| `python scripts/check_release_plan.py` | Passed: 34 items, eight students, acyclic dependencies |
| `python -m unittest discover -s scripts/tests -q` | 45 passed |
| `python -m ruff check` | Passed |
| `python -m ruff format --check` | Passed: 123 files |
| `python -m mypy` | Passed: 123 source files |
| `python -m pytest` with isolated temp directory and JUnit output | 1,138 passed; four Linux-only benchmark cases skipped on Windows |
| `npm run check` | Passed: lint, Prettier, TypeScript, 236 Vitest tests, production build |
| Production-shell browser scenarios | Four passed in pinned Chromium |
| Standalone and release browser scenarios against Vite development | 18 passed: 16 standalone and two release |
| Standalone and release browser scenarios against production preview | 18 passed: 16 standalone and two release |

The pytest run emitted 80 existing warnings; none failed a check. The skipped
benchmark cases require Linux RSS/process behavior and must run in hosted CI.
The API tests include native-picker access policy, migration/backups/bindings,
workspace isolation, rename/execution locking, timer workspace ownership, and
complete redacted log exports.

## Limits and remaining gates

- Docker's engine pipe is unavailable on this machine. Ubuntu WSL cannot start
  because its required Windows virtualization service is unavailable. Compose
  smoke and release-candidate install/backup/reset/restore rehearsal could not
  run locally; their GitHub Actions jobs remain required.
- Linux backend behavior and the four benchmark cases remain hosted-CI checks.
- Actual native folder selection was not manually repeated in this verification
  pass. Browser tests stub the dialog and backend tests exercise its contract.
- Windows leaves some test-server processes alive during Playwright teardown;
  only the identified isolated test services were stopped. The user's running
  application was preserved. This affects local teardown timing, not assertions.
- The six test changes and this record must be committed/pushed before a PR's
  hosted checks can validate them. Local success does not assert hosted CI is green.

Local JUnit/log artifacts live under the ignored root `test-results/` directory;
frontend Vitest JUnit output can be regenerated with `CI=true npm run check`.
Synthetic desktop/mobile screenshots are generated by the browser scenarios.
Attach selected evidence to the PR rather than committing private test data.

## Follow-up: Linux mypy failure

Hosted Linux type checking reported that `os` had no `listdrives` attribute in
`app/workspace.py`. The Windows-only call was guarded by `os.name`, which mypy
did not use to exclude that branch under its Linux platform definitions. The
earlier Windows type check therefore missed the error.

`local_drives` now uses an explicit `sys.platform == "win32"` branch, which
mypy recognizes. Windows still enumerates its drives; other platforms return
the filesystem root. No type errors are suppressed and the artifact-upload
step is unchanged: the missing pytest XML was a consequence of the preceding
type-check failure preventing pytest from running.

Follow-up verification on Python 3.12.16:

- `python -m mypy --platform linux`: passed, 123 source files.
- `python -m mypy --platform win32`: passed, 123 source files.
- Ruff lint and formatting: passed.
- Workspace picker/settings/storage tests: 40 passed; JUnit XML generated at
  `test-results/ci-platform-fix.xml`.

These checks validate both platforms' type information; they do not substitute
for running the application or full backend suite on Linux.

## Follow-up: nonempty workspace fixture

The standalone workspace-repair scenario failed during setup with `ENOTEMPTY`.
CI's development and production-preview invocations reuse metadata and workspace
data. The fixed project name could collide with previous attempts, and its
hard-coded folder path could reference an older populated folder.

The scenario now creates a unique, short project name for every attempt. It
resolves the new pipeline folder and workspace to their real paths, verifies
that the folder is a descendant of the workspace, and removes only that
pipeline folder with `rm(..., { recursive: true, force: true })`. A synthetic
file is deliberately placed in its inputs folder before removal, so the
nonempty cleanup case is exercised on every run.

Verification used the same isolated metadata database and workspace across two
development attempts followed by two production-preview attempts, in pinned
Chromium with Node 24/Python 3.12. All four passed. A populated folder using the
old fixed name was retained and its marker file remained unchanged. TypeScript,
ESLint, Prettier, and the production build passed. No full-suite rerun is claimed
for this test-only follow-up.

## AI assistance

AI contribution: 50% or more AI-generated.

OpenAI Codex reviewed the branch/workflows, updated the six browser scenarios,
ran the recorded checks, and drafted this record and PR description. The author
supplied the UX requirements and directed this verification. No independent
human review or stakeholder signoff is inferred from automated checks.
