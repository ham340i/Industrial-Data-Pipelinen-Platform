# Issue #19 local project verification

Status: local implementation on `feature/19-local-projects`, based on main after
SDK PR #59. No #9/#13 code is included. Independent review, hosted CI, PR and
merge remain pending. Planned reviewer: `menaboulus`.

## Observed local checks — October 14, 2026

- Python 3.12, repository-locked dependencies, isolated read-only workspace mount:
  235 full backend tests passed, including 19 project tests; 25 deprecation
  warnings. Ruff lint and strict mypy passed (35 files).
- Node 24 with locked frontend dependencies: lint, formatting, TypeScript,
  Vitest (44 tests) and production build passed.
- Repository-tool unittest suite: 16 passed.
- Real isolated Compose smoke passed: both images build, health/assets/proxy work,
  a synthetic SQLite project survives container recreation and reopens via the
  HTTP API. Its uniquely named containers/network/volume were removed.
- Chromium: 2 real-service Compose tests passed, including create/open/reload,
  keyboard focus, last selection in a fresh context, and maximum-length names
  without overflow at 390px viewport width. The 3 existing production-shell
  browser tests passed, including offline retry and the actual transport timeout.
- Backend formatting: 35 files already formatted; documentation checks passed
  across 127 Markdown files; Git whitespace checks passed.
- The Windows repository check still flags the two pre-existing Bash wrappers;
  adding Git Bash to PATH did not resolve it. Hosted Linux verification remains
  pending. No application check was skipped to make the result pass.

Commands used:

```sh
python -m pytest -q -p no:cacheprovider --basetemp /tmp/projects-full
python -m ruff check --no-cache
python -m mypy --cache-dir /tmp/projects-final-types
npm run check
python scripts/smoke_workspace.py
npm exec -- playwright test --config playwright.compose.config.ts
npm run test:browser
```

Backend/frontend checks used containers to supply the target Python/Node versions.
The browser runner additionally uses a disposable Node 24/Chromium image on the
isolated Compose network; the production UI still uses the normal Nginx proxy.
The browser tests contain no HTTP mocks. Full ETL acceptance is outside #19.
The separate production-shell browser suite does mock health traffic, as before.
The recorded real-service run used a uniquely named Compose stack and
`COMPOSE_BASE_URL=http://frontend:8080` on its private Docker network. Browser
screenshots are generated under ignored `frontend/test-results/`.

Initial validation found a missing test-list annotation, unsupported Testing
Library `exact` options, and localStorage cleanup in a Node-only harness.
Those were corrected before the passing checks. No checks were disabled.
Review also exposed stale cached metadata preventing a missing saved project ID
from being cleared. The handling order was corrected and a regression test passes.

## Scope and attribution

All data is synthetic. Project names never become paths. Browser storage contains
only the selected ID, scoped by origin/API base. Metadata uses the existing
SQLite model; no migration or production dependency update was introduced.
This does not claim partner datasets, stakeholder signoff or measured performance.

Karim requested #19 implementation. Codex drafted code/tests/design/docs and
executed the recorded checks. Independent student review remains required;
no separate manual implementation/verification by Karim is asserted.
