# Pipeline authoring — issues #14 and #15

The React Flow canvas edits the existing schema-version-1 pipeline contract. Stable UUIDs identify nodes and edges; layout positions are separate from block configuration. Zustand owns the unsaved graph, while TanStack Query owns registry and saved pipeline lists. The registry endpoint exposes SDK public metadata only. Client connection checks mirror typed port compatibility, cardinality and DAG constraints; backend authoring validation remains authoritative. Saving incomplete block configuration is permitted; execution readiness is checked separately by [graph validation (#21)](graph-validation.md).

## Persistence (#14)

Project-scoped endpoints use SQLite Pipeline and immutable PipelineRevision entities. Creates atomically save the name and revision 1; PUT saves the name and definition together; PATCH renames without changing the definition. Both update operations require the observed `expected_revision`. Successful changes append a revision. Names are unique within a project. Read/list/update queries always enforce project ownership.

`Database.transaction(write=True)` takes SQLite's writer lock with BEGIN IMMEDIATE before reading the current revision. Concurrent writers serialize; a stale writer returns 409 rather than overwriting a newer revision. Errors roll back both metadata and definition changes. No schema migration is required. A failed/ambiguous network response retains the local draft; a retry may receive a conflict if the previous save committed.

The editor disables mutations while requests are pending. Generation checks discard late responses after a project switch or draft reset. Opening a saved pipeline asks before discarding unsaved edits. API failures retain the draft. Save a copy allows conflict recovery under another name. Export JSON is enabled only after saving the current draft and exports the validated portable graph, without UI selection/measurements.

Saving validates structural version-1 graph rules and the existing credential/path portability boundary. It deliberately allows incomplete block configuration and disconnected inputs; execution readiness is reported by `POST /api/v1/pipelines/validate` ([#21](graph-validation.md)). The portability policy detects known credential keys and machine paths, not arbitrary secret strings under otherwise public fields.

AI assistance: Codex designed, implemented and tested this change at the user's request. Independent review, CI, manual stakeholder demonstration and acceptance remain pending.
