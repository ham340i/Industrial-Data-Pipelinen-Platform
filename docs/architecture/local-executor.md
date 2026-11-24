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

## Frame-native blocks (Release 2, #121)

Until Release 1, every node converted its input frames into `Table` rows (Python dictionaries), the block converted them back to a Polars frame, and the result went through the same round trip again: four full conversions per node, plus row-by-row validation. Spike #109 measured this as the main cost and recommended frame-native blocks before fused lazy plans.

A block now opts in with `frame_native = True` and implements `_execute_frames`, which receives and returns `Frame` objects (`app/blocks/frames.py`). The executor always calls `Block.run_frames`:

- Frame-native blocks get the same lifecycle as `run`: configuration validation, started/succeeded/failed events and port checks. `checked_frame` enforces what `Table` validated per row (exact column types, no nulls in non-nullable columns, finite numbers) using whole-column operations, then gives the block a clone so it cannot change another branch's input.
- Blocks that are not frame-native, or that override `before_execute`/`after_execute` (which take Tables), go through `run` exactly as before.
- Select, Rename and Filter are frame-native. Each has one implementation on frames that both paths call, and `tests/test_frame_native_blocks.py` checks both paths return equal results, errors and events.

Measured on a 150,000-row source, Select, Rename and Filter chain (Linux, Python 3.12): 11.0 s and 333 MiB peak on `main` (`b51bd93`), 1.37 s and 266 MiB with frame-native blocks. The source still produces a `Table`; making sources frame-native is the next step of #121.
