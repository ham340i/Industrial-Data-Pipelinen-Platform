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
- `npm run check --prefix frontend`: passed lint, formatting, types, all
  225 unit/component tests and the production build.
- `.venv/bin/python -m pytest -q`: 913 passed, 70 existing deprecation warnings.
- Ruff lint/format and mypy: passed (104 source files).
- Repository, documentation, release-plan and repository-tool tests: passed
  (16 tool tests).
- A separate real API/engine/persistence/query smoke ran the exact synthetic
  CSV/SQL fixture twice and returned `[["A",30],["B",50]]` both times.
- Local Playwright: Chromium launch blocked by the desktop sandbox's macOS
  Mach port permission. No browser acceptance pass is claimed from that attempt.
  CI runs `npm run test:release --prefix frontend` on Linux and Windows and
  uploads HTML/JUnit reports, screenshots, traces and attachments.

The initial frontend checks found an unused test type import and strict
TypeScript fixture typing issues; these were corrected before verification.

CI at `1f37eba` passed backend/frontend/repository/documentation/Compose checks.
The first full browser attempt passed authoring, CSV preview, validation,
seven-block execution and exact Parquet output inspection, then timed out
because the reopening test queried a navigation link as a button. The SQL-only
release scenario passed. Follow-up `b20fcc2` fixes that selector and strengthens
all seven block row-count assertions and log checks. Both OS jobs rerun the
complete release and standalone scenarios; the live PR checks expose their
results, HTML/JUnit reports, failure traces and success screenshot attachments.
No successful browser test is inferred from the earlier timed-out attempt.

Measured fixture flow: CSV `0 → 6`, SQL `0 → 2`, schema validation `6 → 6`,
filter `6 → 5`, join `7 → 4`, aggregate `4 → 2`, sink `2 → 1` (one artifact).
The run/output artifact has two data rows. The release test checks these
measurements, saved revision identity and exact row values in the rendered UI.

## Attribution and review

OpenAI Codex authored the design, code, tests and evidence at the user's
request, using existing team interfaces and preserving prior authorship.
The user selected the issue; no manual student authorship, independent review,
or stakeholder signoff is asserted. Planned reviewer: `@karimikhaeil`.
[PR #89](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/89)
is the review change. Its [live checks and retained release artifacts](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/89/checks)
are the authoritative CI results for each exact revision. Independent review
remains pending. The issue must remain open until its required review and merge gates are met.
