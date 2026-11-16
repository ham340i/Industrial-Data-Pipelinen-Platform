# Issue #31 workflow verification

Date: November 16, 2026. Base: `c4cc967` (current `origin/main` when fetched).
Branch: `feature/31-author-preview-execute`. Synthetic fixtures only.

## Scope and design

[Design](../design/issue-31-workflow.md). All nine prerequisites (#14, #23,
#24, #25, #26, #28, #29, #30, #33) were closed when checked through GitHub on
November 16. Their merged contracts are present in the base revision.

The configuration form now accepts the closed, locally referenced object lists
published by Validate Schema and Aggregate. Validation invokes the actual
validation API; the obsolete simulated run action has been removed. Saved
revision execution remains the single UI run action. Both immediate results
and persisted run history expose governed, bounded Parquet output tables.

The new real-service Playwright scenario authors all seven blocks and six
connections in the UI, samples CSV, validates and saves, runs the full engine,
checks statuses/timings/logs and exact aggregates (`A:30`, `B:50`), reloads and
reopens the project/pipeline, reruns, provokes a missing SQL table failure, and
uses the failed-block configuration link to repair/save/rerun successfully.
It attaches graph/run/row evidence and a success screenshot. No HTTP or engine
mocks are used in this acceptance suite.

## Local verification

Environment: macOS, Python 3.12.10, Node 24.19.0, dependencies installed from
`requirements.lock` and `frontend/package-lock.json`.

- `.venv/bin/python -m pytest -q`: **913 passed**, 70 existing deprecation warnings.
- Backend lint, formatting, types, repository/docs checks: pending final record.
- `npm run check --prefix frontend`: pending final record.
- Local Playwright: Chromium launch blocked by the desktop sandbox's macOS
  Mach port permission. No browser acceptance pass is claimed from that attempt.
  CI runs `npm run test:release --prefix frontend` on Linux and Windows and
  uploads HTML/JUnit reports, screenshots, traces and attachments.

The initial frontend checks found an unused test type import and a strict
TypeScript fixture union issue; both were corrected before final verification.

## Attribution and review

OpenAI Codex authored the design, code, tests and evidence at the user's
request, using existing team interfaces and preserving prior authorship.
The user selected the issue; no manual student authorship, independent review,
or stakeholder signoff is asserted. Planned reviewer: `@karimikhaeil`.
PR, CI and independent review status will be recorded when available. The
issue must remain open until its required review and merge gates are met.
