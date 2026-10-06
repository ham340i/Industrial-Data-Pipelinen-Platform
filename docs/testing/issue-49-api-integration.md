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

Yousef led and delivered the API/workbench integration fixes, regression tests and documentation, with AI assistance. Independent teammate review is tracked in PR #51. Existing implementation authors retain their attribution.

## Windows standalone follow-up - October 5, 2026

The team's Windows report revealed a second integration defect: the default Vite development origin was `http://127.0.0.1:5173`, while the API allowed only localhost/127.0.0.1 on port 3000. The browser still displayed its connection warning after applying PR #51's versioned-route fix. A real browser regression against separate Uvicorn/Vite processes reproduced the warning on main and on the routing-only branch. Earlier mock-based shell tests and the same-origin Compose proxy could not catch this CORS mismatch.

Vite development and production preview now default to port 3000 with strict port selection. The API allowlist is unchanged. Windows onboarding calls the Python 3.12 virtual environment directly, avoiding POSIX `source` and PowerShell activation-policy changes. The new standalone Playwright test runs real services without HTTP mocks, verifies the 200 versioned health response and allowed-origin header, checks the connected UI, navigates to Builder and tears down both services. CI adds Windows/Linux standalone jobs; Windows also runs the complete backend and frontend checks. Both development and built-preview modes are covered.

The team's `ast-serialize==0.12.1` installation failure was not reproduced: a fresh Windows x64/Python 3.12.10 virtual environment installed main's unchanged hash-pinned lock successfully, including that package. [PyPI's release files](https://pypi.org/project/ast-serialize/0.12.1/#files) include compatible Windows x64 wheels. The teammate's exact interpreter, architecture and pip version remain unknown; troubleshooting requests those details if the documented Python 3.12 setup still fails. No dependency downgrade, lock rewrite or hash-check bypass is warranted by the observed result.

Local follow-up checks: all 33 backend tests, Ruff lint/format, mypy, all 25 frontend tests, frontend lint/format/types/build, repository checks, documentation links, Release 1 planning and all 16 repository-tool tests passed. The real development browser smoke passed in 14.1 seconds and the built-preview smoke passed in 8.1 seconds, both with normal Windows process permissions and exit code 0. Both ports rejected connections afterward, verifying service cleanup. The sandboxed smoke reached the connected UI but could not finish Windows child-process cleanup; the test-owned processes were identified and stopped before the successful rerun. Clean-clone frontend files were normalized to the branch's existing LF policy without additional source changes.

Publication, hosted Windows/Linux job results and independent approval remain pending for this follow-up. Docker is unavailable locally; existing hosted Compose results refer to the earlier published PR head. This connection check does not establish a complete ETL workflow or stakeholder acceptance.
