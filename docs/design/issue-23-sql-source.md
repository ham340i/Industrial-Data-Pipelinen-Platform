# Read-only SQL source design (#23)

The approved dialect is local SQLite. The portable SDK block stores a logical
`resource_ref`, a read query, named parameters encoded as JSON text, and an
explicit scalar schema. Runtime `BlockContext.resolve_resource` and
`workspace_root` resolve the local database; paths and credentials stay outside
the graph. SQLite requires no credentials. Remote database authentication and
secret providers remain outside this SQLite implementation.

Reuse the spike query validator, SQLite authorizer and URI read-only opening.
Use `mode=ro`, `query_only`, a VM instruction budget and bounded row fetching.
Reject duplicate columns, undeclared/mismatched scalar types, unsupported BLOBs,
and over-budget results. Explicit schema preserves empty/all-null outputs and
feeds the existing SDK/Polars adapter and Join block. Errors contain fixed codes
and messages, never database paths, SQL text or bound values.

JSON text parameters keep the existing generated configuration form compatible;
parse and validate the object before binding. This is less convenient than a
structured object editor but avoids extending the shared form contract. Literal
values must be supplied with named SQLite placeholders, never interpolation.

Issue #31 remains integration-gated by #26, #28, #30 and #33. No preview or
artifact-query contract is invented here. Independent review and stakeholder
acceptance remain pending. Implementation and tests are Codex-assisted.
