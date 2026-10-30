# ADR-0004: Portable pipeline JSON and headless topology

Status: Proposed for independent review under issue #9.

## Decision

Store one versioned JSON definition with nodes, edges and optional layout.
Nodes reference exact block ID/version pairs and public configuration. Edges
reference named output/input ports through node IDs; port contracts remain
authoritative in the SDK registry rather than being duplicated in the graph.
Layout positions are optional and excluded from semantic exports and scheduling.

Use strict Pydantic contracts with schema version 1. Reject unsupported versions,
unknown fields, duplicate node/edge IDs and duplicate connections, dangling
references, cycles and unknown layout nodes. Empty/disconnected graphs are valid
authoring documents. Use a min-heap in Kahn's algorithm to order ready nodes by
ID, independently of input-array order. Multiple port edges between two nodes
count as one scheduling dependency.

Structural loading does not require installed blocks. A separate registry check
resolves exact versions, validates configuration and named port compatibility,
and checks required inputs and connection cardinality for a complete graph.
It never executes or previews blocks. A many-valued output cannot connect to a
single-valued input. The later executor still validates actual payloads: an
optional producer may emit nothing, and a connected input is not a guarantee
that data will be available at runtime.

Reuse the metadata portability guard and SDK public-JSON policy for config.
Machine paths and secret references remain external workspace bindings, resolved
by logical resource IDs at runtime. Export and registry validation revalidate
mutable nested dictionaries. This introduces no database migration, HTTP route,
UI change, processing library or execution engine.

## Alternatives and consequences

Embedding block declarations in every graph duplicates the registry and can
drift. Requiring the registry to load a document prevents offline structural
inspection. Sorting by array order makes ordering depend on UI serialization.
Storing layout in a separate file complicates a portable authoring document;
instead, semantic exports explicitly omit it.

These contracts use strict types and conservative port compatibility. Future
format versions require explicit migration; unknown versions are not silently
coerced. Definitions do not capture input snapshots or guarantee reproducible
results from changing source data. Resource bounds and execution semantics are
future engine work.

## Dependency and verification

Implementation started on reviewed SDK PR #59 at `8e816fa`. On October 14,
the feature branch was fast-forwarded onto merged main `80f8dc7`, with identical
SDK source files. The SDK dependency is now merged. See the
[developer guide](../../pipeline-definition.md) and
[verification record](../../testing/issue-9-portable-dag.md).

AI Assistance: Codex drafted the design, implementation, tests and documentation
at Karim's instruction. Independent review and stakeholder acceptance remain
pending; no separate manual authorship or verification is claimed.
