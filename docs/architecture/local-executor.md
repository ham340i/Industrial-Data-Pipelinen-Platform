# Local DAG executor — issue #22

The executor is a synchronous, single-process library. It snapshots and validates
the complete definition against the SDK registry before any block runs. The
existing lexicographic Kahn scheduler defines node order; incoming edges are
sorted by ID so multi-input ordering does not depend on JSON array order.

Each invocation owns its run identity, state history, diagnostics and typed
Polars input/output storage. SDK v1 tables remain the extension boundary: an
explicit adapter retains declared column order, type and nullability, including
empty/all-null tables. This avoids breaking existing blocks and reuses the #10
CSV/select/Parquet proof. It does incur materialization and copying; lazy and
streaming execution are outside this bounded first implementation.

Nodes transition queued → running → completed/failed. Descendants of failed or
skipped nodes become skipped; independent branches continue. A failed run keeps
successful intermediate outputs and structured node failures. Observational
callbacks cannot change execution outcomes. Cancellation is cooperative between
blocks and through the block context; it cannot interrupt native I/O or undo a
sink's already committed side effects. Unstarted nodes become skipped.

Limits bound graph size and retained rows/cells. They do not impose an operating
system memory or CPU limit on arbitrary block code. Public events contain no
table values, configuration, resource paths or raw exception text. Runtime
frames and resource resolvers are never serialized into pipeline definitions.

The runtime resolves injected blocks; catalog implementations from #16/#18/#20
must meet the same SDK contract. The merged CSV/Select/Parquet catalog is covered by an integration test; the
executor propagates its workspace root policy through the block context. API execution, persisted telemetry, artifact governance
and UI integration belong to #29, #27, #28 and the Iteration 4 workflow.

Design and implementation assistance: OpenAI Codex. Designated reviewer
discussion, independent approval and stakeholder acceptance remain pending.
