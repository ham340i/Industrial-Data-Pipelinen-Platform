# Issue #49 API and workbench integration

Date: October 4, 2026 (America/Toronto). Base: `eef36f34946746cb57c66e88c0b3af81ab3c7d98`. Scope: [issue #49](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/49). Independent student review and merge are pending.

## Reproduced failures

The standalone workbench used `http://127.0.0.1:8000/health`, although the API exposes `/api/v1/health`. Compose's explicit `/api/v1` base worked, and the unit/browser mocks reproduced the wrong standalone URL. Correcting the literal fixture and adding bare-host cases before changing production code made the API client suite fail: 11 failures, 2 passes. The failures included an unhandled GET to `/health` and the incorrect default/base-path assertions.

The API middleware appended a correlation header already set by validation error responses. Replacing the old set comparison with an exact single-header assertion and exercising 200/422/500 responses with supplied, generated and invalid IDs produced 4 failures and 19 passes before the fix. All failures were duplicate headers on validation errors.

## Implementation

- The default frontend base and example configuration include `/api/v1`. Bare HTTP(S) hosts receive that prefix; explicit paths and the supported Compose relative base are preserved.
- Unit and browser fixtures use the backend's actual versioned route.
- Middleware replaces existing correlation headers case-insensitively before adding the authoritative value. The error handler keeps its fallback header because an unhandled 500 response can be emitted outside this middleware.
- Two pytest harness subprocesses use a temporary INI file rather than POSIX-only `/dev/null`. This is the same portable fix already proposed in [PR #48](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/48), included here so this independent branch can run the full Windows suite.
- Unused API imports and their existing temporary lint exemption are left to PR #48. A merge preflight caught an adjacent import overlap when both branches attempted this cleanup; keeping it solely in the metadata PR lets the two feature branches merge cleanly. No new lint exemptions are added here.
- `.gitattributes` keeps text at LF across platforms. The Windows host's `core.autocrlf=true` initially caused Prettier to reject 17 otherwise unchanged files; normalizing their line endings produced no extra source diff.
- ESLint and TypeScript harness controls exceeded Vitest's default five-second timeout on this Windows host. The tool tests now consistently allow 120 seconds for their pair of bounded 60-second subprocesses, retaining every passing-control and broken-fixture assertion. Application test timeouts are unchanged; [Vitest test options](https://vitest.dev/api/test#timeout) document this per-test setting.

## Local verification

Environment: Windows, Python 3.12.10 and Node 24.19.0. Python execution uses the neighboring PR #48 virtual environment; the API/harness dependencies are the same locked versions as main. Extra metadata packages installed there are unused by this branch. Frontend dependencies were installed independently with `npm ci --ignore-scripts --no-audit --no-fund`.

- `python -m ruff check .`: passed.
- `python -m ruff format --check .`: passed, 12 files formatted.
- `python -m mypy`: passed, 12 source files.
- `python -m pytest -q`: 33 passed, including the actual pytest/Ruff/mypy failure-propagation controls. Existing Starlette deprecation warnings remain.
- `npm run check`: lint, format, types, 25 unit/harness tests and production build passed after the Windows portability corrections.
- `npm run test:browser` with `PLAYWRIGHT_CHROME_PATH` pointing to installed Chrome: all 3 production-shell, mobile/recovery and timeout checks passed. These tests use the corrected versioned route mocks.
- Repository configuration, documentation links, release-plan validation and all 16 repository-tool tests passed. Git Bash's bin directory was added to the check process PATH for Bash syntax validation; no host settings were modified.

Docker is unavailable on this host. The existing hosted Compose smoke must pass on the exact PR head before merge. Browser shell tests use route mocks; they do not establish a real standalone backend connection. No full ETL workflow or stakeholder acceptance is asserted.

## AI assistance

Codex identified and reproduced the failures, implemented the corrections and ran the recorded checks at Al-Yousef's direction. Independent teammate review is tracked in PR #51. Existing implementation authors retain their attribution.
