# Release 2 test report

Records only test runs that actually happened, with the commit and environment. Release 2 features are added as they land.

## Baseline before Release 2 work

| Date | Commit | Environment | Suite | Result |
|---|---|---|---|---|
| 2026-11-24 | `b51bd93` (`main`) | Linux, Python 3.12 | Backend `python -m pytest` | 1,141 passed, 1 skipped (`test_workload_benchmark.py` runs on non-Linux hosts only) |
| 2026-11-18 | `fbc2e82` (PR #119) | Linux, Node 24 | Frontend `npm run check` (ESLint, Prettier, TypeScript, Vitest, build) | 25 files, 238 tests passed |
| 2026-11-18 | `fbc2e82` (PR #119) | Linux, Chromium, real API | Standalone browser suite | 16 passed |
| 2026-11-18 | `fbc2e82` (PR #119) | Linux, Chromium, real API | Release browser suite | 2 passed |
| 2026-11-18 | `fbc2e82` (PR #119) | GitHub Actions | Full CI, including Windows standalone and Compose smoke | 9 of 9 checks passed |

## Known failures on `main`

| Failure | Since | Cause | Fix |
|---|---|---|---|
| `Standalone workspace smoke (windows-latest)` fails intermittently | #114 (`bf7d963` red) | Workspace pages remounted when the workspace setting first loaded, wiping typed input | #119, awaiting review |

## Coverage

Backend line coverage was 96% at Release 1 (CI report). It is re-measured in the Release 2 candidate run.

## Release 2 features

| Date | Commit | Feature | Suite | Result |
|---|---|---|---|---|
| 2026-11-24 | `90f1b97` (PR #132) | F1 step 1, frame-native Select/Rename/Filter (#121) | Backend `python -m pytest`; ruff; mypy strict | 1,174 passed, 1 skipped (1,141 existing plus 33 new); lint and types clean |
| 2026-11-24 | `90f1b97` vs `b51bd93` | F1 step 1 | 4-node chain benchmark, Linux, Python 3.12 | 150,000 rows: 11.0 s / 333 MiB on `main`, 1.37 s / 266 MiB on the branch |
