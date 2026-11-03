# Run telemetry: issue #27

Durable run and block evidence, stored in the local SQLite metadata database,
so an operator can work out what happened after a run finishes or the process
stops.

## Components

| Module | Responsibility |
|---|---|
| `app/runs/service.py` | `execute_revision(db, executor, revision_id)` loads an immutable revision, runs it and returns `RunOutcome(run_id, state, context)`. Trigger/execute APIs (#29) call this; it exposes no HTTP route. |
| `app/runs/recorder.py` | `RunRecorder` persists executor `on_state` callbacks. `recover_interrupted` closes runs a previous process left unfinished. |
| `app/runs/redaction.py` | Masks credentials, bearer tokens, URL user info and absolute paths, then bounds text to 512 characters. |
| `app/runs/api.py` | Read-only `GET /api/v1/runs` and `GET /api/v1/runs/{run_id}`. |
| `migrations/versions/0002_run_telemetry.py` | Adds run duration/error columns plus the `run_blocks` and `run_events` tables. |

```text
execute_revision ──▶ Executor.execute(on_state=recorder.on_state)
                         │ each state transition (own short write transaction)
                         ▼
                 runs / run_blocks / run_events  ◀── recover_interrupted (startup)
                         ▲
                 recorder.finish(context)  — reconciles final block evidence
                         │
          GET /api/v1/runs, GET /api/v1/runs/{id}
```

## Design decisions

- **Live writes plus a final reconcile.** Each transition is committed as it
  happens, so a crash leaves a `running` row instead of nothing. `finish` then
  overwrites block states, counts and errors with the executor's result, which
  is authoritative. This repairs any live write that failed: the executor
  ignores callback errors, so the recorder logs them at `WARNING`.
- **Truthful terminal state.** At API startup, `recover_interrupted` moves
  `queued`/`running` runs to `failed` with code `interrupted`, fails running
  blocks and skips queued ones. An unexpected executor exception (including
  `KeyboardInterrupt`) gets code `execution_failed`. Nothing is ever reported
  as succeeded unless the executor completed it.
- **Invalid pipelines create no run.** The executor validates before its first
  callback, and the run row is created on that first callback.
- **Unknown is not zero.** `rows_in`/`rows_out` are `NULL` when a block did not
  complete or produced no tabular output (for example, a sink's `rows_out`). A
  measured empty table is stored as `0`. A run's `row_count` is the sum over leaf
  nodes (sinks count rows received, other leaves count rows produced), and it is
  `NULL` if any leaf did not complete.
- **Monotonic durations.** `duration_ms` comes from `time.monotonic()`, which
  can be injected for tests. `started_at`/`ended_at` are wall-clock UTC for
  display only.
- **Root cause first.** A run's `error` is the first direct failure in
  topological order. Downstream `dependency_failed` skips are symptoms.
- **Cancelled vs failed.** If the caller's `Cancellation` token was cancelled,
  the run is stored as `cancelled`. The executor itself reports `failed`.
- **No datasets in metadata.** Events store fixed messages and codes only, such
  as `Node n1 failed` or `Block csv.read@1 started`. Failure reasons pass
  through `redact` before storage.

Alternatives considered: a single write when the run finishes was simpler, but
a crash would leave no evidence. A separate log file was rejected because it
would split one run's evidence across two stores with no transactional link.

## API contract (`schema_version: 1`)

`GET /api/v1/runs?project_id=&pipeline_id=&state=&offset=0&limit=20`
returns `{items, total, offset, limit}`, newest first. `limit` must be 1–100.

`GET /api/v1/runs/{run_id}` returns a summary plus:

- `blocks`: `position`, `node_id`, `block_id`, `block_version`, `state`
  (`queued|running|completed|failed|skipped`), timestamps, `duration_ms`,
  `rows_in`, `rows_out`, `error {code, reason}`
- `events`: `sequence`, `created_at`, `level` (`info|warning|error`),
  `node_id`, `kind` (`state|block`), `code`, `message`
- `outputs`: artifact links from `output_endpoints` for this run only. Sinks
  registering artifacts is #28.

Summary fields: `id`, `project_id`, `pipeline_id`, `pipeline_revision_id`,
`revision`, `state` (`queued|running|succeeded|failed|cancelled`),
`created_at`, `started_at`, `ended_at`, `duration_ms`, `row_count`, `error`.

Errors use the standard envelope: `404 run_not_found`, and `422
validation_error` for a malformed UUID, state or page bounds.

## Limits

One local process per metadata file. Recovery assumes no other live process is
writing runs. The project has no retention or pruning policy for run history
yet. UI views of this data come with the Iteration 4 workflow.
