# Testing Evidence

## Issues #15 and #14 — October 20, 2026

Local implementation on `feature/15-canvas-14-persistence`, based on commit `b2faa19c41dd85dfd69f51d4f48ebad477c1c1a6`. Results below apply to the working-tree changes, not the unchanged base commit. #15 was implemented and verified first, then #14, as requested by the owner. These results do not certify the entire iteration.

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

Initial installation failed with a full local disk. After space was freed, dependencies installed successfully. Initial checks used Node 22/Python 3.13; final checks use the repository's required major versions and locked backend dependencies. Type checking caught unsupported MUI shorthand props, which were replaced with `sx`. The new browser case initially used a path URL instead of the application's hash route; the test was corrected. Expanded drag/drop testing exposed excessive initial canvas zoom; limiting automatic fit to 100% resolved node overlap at the tested drop location. All listed application test failures were corrected before the final passing runs.

## Review, CI and Manual Verification

Remote CI, independent teammate approval, PR/merge, manual stakeholder demonstration and signoff remain pending. No issue closure, completion tag or completed iteration is claimed. Planned reviewers remain the issue-designated students; no review request has been sent from this session.

## Evidence Links and AI Assistance

Design: [pipeline authoring](../../architecture/pipeline-authoring.md). Usage: [canvas guide](../../frontend/canvas.md). Tests: [graph](../../../frontend/src/state/graph.test.ts), [canvas](../../../frontend/src/Canvas.test.tsx), [persistence UI](../../../frontend/src/PipelineControls.test.tsx), [API/SQLite](../../../tests/test_pipeline_api.py), [real browser workflow](../../../frontend/standalone-tests/pipelines.spec.ts).

Codex authored the implementation, tests and documentation at the owner's request and executed the recorded checks. Human review and personal student contribution verification remain pending.
