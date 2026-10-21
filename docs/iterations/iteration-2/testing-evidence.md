# Testing Evidence

## Issues #15 and #14 — October 20, 2026

Local implementation on `feature/15-canvas-14-persistence`, based on commit `b2faa19c41dd85dfd69f51d4f48ebad477c1c1a6`. The verified implementation is commit `58e86745946c802426cd41bbb5d069f6b3df255e`; it is published in [PR #64](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/64). Results below apply to that implementation, not the unchanged base commit. #15 was implemented and verified first, then #14, as requested by the owner. These results do not certify the entire iteration.

## Environment

macOS arm64; Node 24.22.0/npm 11; Python 3.12.15 with hash-verified `requirements.lock`; frontend `package-lock.json`; local Google Chrome. Temporary Python/Node environments were used without changing system tool versions. Browser integration tests used an isolated temporary SQLite database, synthetic blocks and synthetic project names.

## Automated Tests

- `npm run check --prefix frontend`: lint, formatting, TypeScript, 54 tests in 9 files and production build passed.
- `python -m pytest -q`: 314 tests passed.
- `ruff check`, `ruff format --check`, `mypy`: passed (42 Python files).
- Repository documentation/configuration checks and `git diff --check`: passed.

New tests cover registry discovery, keyboard creation/deletion, serialization, stable IDs, typed connections, cycle/cardinality/duplicate rejection, save/open/rename, stale response protection and failed-save draft retention. Backend tests use real SQLite transactions and cover concurrent writer conflicts, project isolation, malformed/nonportable definitions, retained revisions and rollback after an injected interrupted write.

## Browser Integration

`npm run test:standalone --prefix frontend` with `LPS_PYTHON` selecting the locked Python 3.12 environment, `LPS_METADATA_PATH` pointing to a temporary database and `PLAYWRIGHT_CHROME_PATH` selecting local Chrome: 2 passed. No HTTP mocks in this suite. The authoring case creates a project, adds and moves a node, drags another block onto the canvas, connects typed ports, saves, refreshes, reopens, renames and verifies identical definition/configuration/layout and IDs after another reload.

`npm run test:browser --prefix frontend`: 4 passed. Covers the production build with mocked network responses: navigation, offline/mobile behavior, request timeout and keyboard node add/move/delete.

## Failed Attempts and Resolutions

Initial installation failed with a full local disk. After space was freed, dependencies installed successfully. Initial checks used Node 22/Python 3.13; final checks use the repository's required major versions and locked backend dependencies. Type checking caught unsupported MUI shorthand props, which were replaced with `sx`. The new browser case initially used a path URL instead of the application's hash route; the test was corrected. Expanded drag/drop testing exposed excessive initial canvas zoom; limiting automatic fit to 100% resolved node overlap at the tested drop location. The initial PR Linux standalone run then exposed overlap from the test's fixed drop coordinates under different font/viewport timing. The test now waits for a usable handle, measures the rendered node, drops beside it and fits both nodes before connecting. Local standalone verification with `--repeat-each=3` passed all 6 executions. Remote CI status remains authoritative on the PR.

## Review, CI and Manual Verification

[PR #64](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/64) is open. Remote CI, independent teammate approval, merge, manual stakeholder demonstration and signoff remain pending. No issue closure, completion tag or completed iteration is claimed. The PR identifies Al-Yousef for #15 and adamoug for #14 as the planned independent reviewers. Review requests and current CI status are visible on the PR.

## Evidence Links and AI Assistance

Design: [pipeline authoring](../../architecture/pipeline-authoring.md). Usage: [canvas guide](../../frontend/canvas.md). Tests: [graph](../../../frontend/src/state/graph.test.ts), [canvas](../../../frontend/src/Canvas.test.tsx), [persistence UI](../../../frontend/src/PipelineControls.test.tsx), [API/SQLite](../../../tests/test_pipeline_api.py), [real browser workflow](../../../frontend/standalone-tests/pipelines.spec.ts).

Codex authored the implementation, tests and documentation at the owner's request and executed the recorded checks. Human review and personal student contribution verification remain pending.

## Issue #21 — graph validation before run

Implemented on `feature/21-graph-validation`, branched from `main` at `ebd52150001387d7753501e14d3415bea41e07c6`. The verified implementation is commit `b0b79ac6aae1dda22795a3df00db1e0b69a8bcf4`. Results below apply to that commit, not to the base. They do not certify the iteration. Design: [graph validation](../../architecture/graph-validation.md).

### Environment

macOS 26.6.2 arm64; Python 3.12.15 in the repository `.venv`; Node 24.5.0 / npm 11.5.1 (the repository requires Node 24); Google Chrome 155.0.8059.85 for Playwright. Standalone browser runs used a temporary SQLite metadata database. All fixtures and blocks are synthetic.

### Automated tests

- `python -m pytest -q`: 374 passed (baseline on `main`: 314). New: 60 cases in `tests/test_validation.py`, covering the 12-case fixture matrix (unit and HTTP), order independence under shuffled nodes and edges, loop-only cycle reporting, a 3,000-node chain without recursion, messages that never echo config values, a 422 envelope for malformed or nonportable requests, and no metadata database access. Existing `validate_registry` tests pass unchanged against the shared rule set.
- `python -m ruff check`, `python -m ruff format --check`, `python -m mypy`: passed.
- `npm run check --prefix frontend` (Node 24): lint, formatting, TypeScript, 71 tests in 11 files and the production build passed. New: diagnostic placement, field messages, display-only edge marking, request shape, response parsing, and Builder integration. The integration tests cover node and list messages, edits kept, Run disabled while invalid, pending or failed, re-checking after a fix, no re-check on node moves, and a slow stale answer never enabling Run.
- `npm run test:standalone --prefix frontend` with `LPS_PYTHON=<repo>/.venv/bin/python`, a temporary `LPS_METADATA_PATH` and `PLAYWRIGHT_CHROME_PATH` set to local Chrome, `--repeat-each=3`: 9 passed (3 specs × 3). No HTTP mocks. The new spec checks against the real API that an empty draft and unconnected inputs are reported, messages appear on the right nodes, connecting one input clears only that node's problem, Run stays disabled and node IDs are unchanged.
- `npm run test:browser --prefix frontend`: 4 passed.
- `python3 scripts/check_docs.py`, `check_repository.py`, `check_release_plan.py`, `python3 -m unittest discover -s scripts/tests` and `git diff --check`: passed.

### Not applicable or pending

- **E2E:** scheduled for the Iteration 4 acceptance workflow (#38), once execution (#22) and source blocks (#16) exist. Not run.
- **Valid run in the real UI:** the Release 1 catalog only contains `synthetic.add_constant`, whose input is required, so the real UI cannot yet build an all-valid pipeline. Valid graphs are covered by the fixture matrix with test-only source and sink blocks, and by mocked UI tests.
- **Manual demonstration:** pending. The owner should demonstrate the acceptance criteria on synthetic graphs and record revision, commands and observed outcome here.
- **Review and CI:** PR, remote CI and independent review by @aboudka2003 are pending.

### Failed attempts and resolutions

- Frontend harness tests failed under the machine's default Node 25 (`localStorage.clear is not a function`), including on unchanged `main`. All checks were rerun under Node 24.5.0, as the repository requires.
- FastAPI validates JSON bodies as Python objects, and the strict contracts reject lists for tuples. The validation request now parses the draft through JSON, like `PipelineCreate`.
- One fixture initially expected the wrong order within a group. The deterministic sort was correct, so the fixture was fixed.
- In jsdom, React Flow wraps nodes in `role="button"`, which hides child list roles, so node problem lists are queried by label.
- In the standalone spec, consecutively added nodes overlapped and covered a handle. The spec now drags the second node aside before connecting.

### AI assistance

Tool: Claude Code (Claude Opus 5.5), at the owner's request. Used for: design, backend and frontend implementation, fixtures, tests, documentation, and running the commands above. Human review of the design and code, the manual demonstration, and the owner's own contribution record are pending.
