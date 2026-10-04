# Issue #4 workspace verification

Date: 2026-10-04 (America/Toronto). Owner: ham340i. Branch: `feature/4-local-workspace`. Base: `13aedf6` (current main when work started).

## Scope and acceptance mapping

| Acceptance criterion | Implementation / evidence |
|---|---|
| Frontend/backend layout without moving tools/docs | Existing `frontend/` and `app/` preserved; [design](../architecture/local-workspace.md) |
| Compose real shells and persistent metadata | Root `compose.yml`, pinned multi-stage frontend image, non-root API image, named volume at `/var/lib/lps` |
| Startup/stop/reset and lock instructions | [Workspace guide](../local-workspace.md); clean-clone validation recorded below |
| Safe environment defaults and isolated data | Root `.env.example`, loopback-only ports, allowlisted Docker contexts, no host data/secret mounts |
| Real shell/health smoke after dependencies | `scripts/smoke_workspace.py`, real backend proxy and Chromium test; no mocked health responses |

## Observed local checks

- `python3 -m unittest discover -s scripts/tests -v`: 16 passed, including two workspace configuration tests.
- `npm run check` under Node 24: lint, format and types passed; 22 tests passed; production build passed.
- `python3 scripts/smoke_workspace.py`: passed real API and proxy health, frontend assets, SPA fallback, non-root metadata writes, persistence across down/up and isolated teardown.
- Docker Desktop Engine 29.3.1, Compose 5.1.1, macOS ARM64. Application runtime: Python 3.12 and Node 24 from digest-pinned images. Repository test runner: Python 3.13.

Backend checks in the Python 3.12.15 image: 24 pytest tests passed; Ruff lint/format and mypy passed (12 source files). Nine pre-existing Starlette deprecation warnings were emitted. Final implementation revision `9651490` was validated in the separate clean clone (initially cloned at `fd83984`, then fast-forwarded to the final implementation). `python3 scripts/smoke_workspace.py --browser` passed: Chromium connected to the real API, Builder direct navigation/refresh worked, both containers ran without root, metadata survived container recreation and the isolated test stack/volume was removed. No existing developer volumes were modified.

The clean clone installed dependencies with `npm ci --ignore-scripts`. Both documented lock regeneration commands passed with no Git diff: `npm install --package-lock-only --ignore-scripts` under the pinned Node 24/npm 11 image, and `uv pip compile --universal --generate-hashes --python-version 3.12 requirements-dev.txt -o requirements.lock` under uv 0.12.23. The Python command resolved 35 packages.

Final repository, documentation and release-plan checks passed; `git diff --check` passed. The later evidence commit changes documentation only. CI and independent review are not yet claimed.

## Limits and troubleshooting encountered

The first attempt with an empty temporary Docker configuration could not discover the Compose plugin. Adding Docker Desktop's CLI plugin directory to that temporary configuration resolved it; no repository workaround or user Docker settings change was required. The first Chromium download timed out; Playwright retried successfully.

The first browser smoke attempt correctly reached the real API but incorrectly expected the Overview-only health message on the Builder page. The test was corrected to check Builder navigation and refresh against the actual shell design.

The metadata test writes a synthetic marker; it does not claim a working database schema. Full ETL workflow and Iteration 4 E2E acceptance remain separate work. Repository Definition of Done still requires passing remote CI, an independent student review and merge. No stakeholder acceptance is asserted.

AI assistance: Codex generated the workspace implementation, documentation and tests and executed the recorded checks at the user's request. Human review is pending.
