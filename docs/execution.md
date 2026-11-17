# Local execution — issue #22

The synchronous engine is available as `app.execution.Executor`. Install the
root hash-pinned dependencies using the [developer guide](getting-started.md).
Pass a `PipelineDefinition` and a `BlockRegistry` containing exact block versions:

```python
from app.execution import Executor

result = Executor(registry).execute(definition, resolve_resource=resolve_resource)
print(result.run_id, result.state, result.node_states)
```

`registry`, `definition` and the optional resource resolver are supplied by the
caller. Production file blocks also require `workspace_root=Path(...)`; the
executor passes this trusted runtime directory through to their path policy. The resolver maps approved logical names to local paths; the engine does
not invent filesystem access policy. Runs receive unique UUIDs by default, or
accept a caller-provided nonblank `run_id` for telemetry correlation.

- `result.inputs` / `result.outputs` map node → port → tuple of `Frame` or
  `ControlSignal`. A frame pairs an eager Polars `DataFrame` with the SDK
  `DataSchema`, preserving nullability even for empty tables.
- `Frame.from_table` / `Frame.to_table` bridge SDK v1 blocks and Polars. Integer
  values must fit signed 64-bit; numbers must be representable as float64 without
  losing numeric value. Unsupported values fail with `invalid_frame`.
- `result.history` records run/node queued, running and completed/failed states;
  dependent nodes that cannot run are skipped. `result.failures` retains
  structured codes, reasons, node IDs and fields. Successful outputs survive
  failures in other branches.
- `InvalidPipeline.diagnostics` reports preflight failures before any lifecycle
  callbacks or block execution. Invalid structural definitions fail during model
  validation. `BlockError` reports invalid runtime options and graph limits.
- Pass `on_state` for observational state notifications. Exceptions from this
  callback are ignored. SDK lifecycle events are retained in `block_events`;
  an SDK success can precede an engine data-budget/adapter failure, so final
  node state is authoritative.
- Pass a `Cancellation` token and call `cancel()` to stop future scheduling.
  Blocks may call `context.check_cancelled()` for cooperative interruption.
  Cancellation produces failed runs and skipped unstarted nodes. It cannot undo
  completed sink writes or force-stop an uncooperative block.
- `ExecutionLimits` defaults to 1,000 nodes, 10,000 edges, 1,000,000 retained rows
  and 10,000,000 retained cells across stored inputs and outputs. Input budgets
  are checked before invocation, output budgets before Polars conversion. These
  are retention limits, not process memory limits while a block is executing.

Runs are isolated, but a registry holds block instances: block implementations
must avoid mutable per-run instance state. This engine schedules sequentially;
concurrent calls against stateful blocks are not supported. No lazy execution,
distributed workers, automatic retries or sink rollback is provided.

Run the synthetic source/transform/Parquet golden integration:

```sh
python -m pytest tests/test_execution.py -q
```

This reuses the exact issue #10 fixture and primitive implementations. A second
integration test executes the merged production CSV, Select Columns and Parquet
blocks using their workspace policy. No new execute endpoint is exposed; API/UI wiring and governed artifacts
remain separate issues. Run persistence is provided by
[`app.runs.execute_revision`](architecture/run-telemetry.md) (#27). See the
[design](architecture/local-executor.md) and
[verification record](testing/issue-22-local-executor.md).

## Failure recovery (#34)

In the builder, save the graph and wait for successful validation before choosing
**Run saved pipeline**. **Run monitoring** identifies each run and saved revision,
shows completed/failed/skipped blocks, and preserves earlier run evidence. Use
**Inspect** to open the affected block without clearing your current draft.

For a failed source or transform, correct its resource/configuration, save and
rerun. Failed dependencies skip downstream blocks; other independent branches
continue. Failed or skipped sinks have no registered output. A previous successful
output file may still exist: file existence alone is not evidence that this run
succeeded. Zero-row tables with declared columns can complete successfully and
report 0 rows; unknown measurements remain unknown.

An existing output with `overwrite=error` fails safely with `output_exists`.
Choose a new relative output reference or explicitly select `replace` when
replacement is intended. Input files and output parent directories must already
exist within `<workspace root>/<project UUID>/`. Saving a new root does not move
existing data. Preview never exercises output publication.

A write cancelled before publication preserves the previous target. A successful
publication cannot be undone by Stop. An unexpected finalization failure attempts
to mark the run failed; if the metadata store is unavailable, restart recovery
closes interrupted records. A complete but unregistered output can remain after
publication followed by failure. Inspect it before choosing an explicit rerun
policy; the application does not automatically delete it or retry the pipeline.

If logs report temporary cleanup failure, stop affected execution and inspect
`.lps-*.tmp` siblings in that output directory. Remove only files verified to be
leftovers, after confirming no worker is using them. Published targets are not
temporary cleanup candidates. Do not purge the workspace indiscriminately.

Timer Stop can report `409 timer_stop_timed_out` while a block finishes. During a
scheduler drain, starts return `409 timer_scheduler_draining`. Shutdown has one
30-second timer-drain deadline; timeout reports incomplete shutdown and retains
database ownership for active workers. Wait for cooperative completion and retry
draining. Process termination is the fallback for a permanently stuck block and
may leave interrupted run evidence and temporary files for recovery on restart.

See the [failure-boundary design](architecture/execution-failure-recovery.md) and
[repeatable in-app checks](testing/issue-34-execution-failures.md#in-app-checks).
