# Author, preview, execute and inspect (#31)

Base: `c4cc967` on November 16, 2026. All nine declared prerequisites are
closed in GitHub and integrated into current main. Independent reviewer:
`karimikhaeil`; review and stakeholder acceptance remain pending.

## Boundaries and decisions

The builder already owns validation, persistence, selected-node preview and
saved-revision execution. Integrate those contracts rather than introducing
another execution path. Preview remains bounded and capability-based: CSV can
be sampled; unsupported whole-input quality/SQL/aggregate previews explain the
limitation. Running uses the complete real engine and saved revision.

The public Pydantic schemas for Validate Schema and Aggregate use local
`$defs` references to closed objects within arrays. Extend the existing JSON
list editor to validate those object members, required fields, defaults and
unknown fields. Resolve only bounded, nonrecursive local definitions; reject
remote references and unsupported schema rules. Keep invalid drafts visible.
This follows the existing JSON list interaction and avoids a block-specific
form that can drift from the registry. The backend remains authoritative for
cross-field rules.

Use the existing governed artifact query API for bounded output tables.
Bind responses to artifact, run and pipeline revision; remount inspection on
identity changes and cancel obsolete queries. Show errors without retaining
rows from a different request. Never load files directly from browser paths.
Integrate inspection into both immediate execution and persisted run history.

## Acceptance proof

Playwright uses real local API/Vite/Chromium, isolated metadata/workspaces,
deterministic synthetic CSV and SQLite fixtures, and UI authoring/connections.
It must validate, preview CSV, save, execute all seven blocks, inspect exact
Parquet aggregates and telemetry, reload/reopen/rerun the same graph, and
recover from a real execution failure. HTTP and engine mocks are excluded from
this acceptance suite. Unit tests cover nested-schema regressions and artifact
adapter identity/shape boundaries. CI runs the release suite and retains its
report, screenshots and traces.

AI assistance: OpenAI Codex authored this design, implementation, tests and
verification records at the user's direction. No human authorship, review,
or stakeholder approval is asserted.
