# Manual and Timer triggers, execute API: issue #29

Lets an operator start a saved, validated pipeline definition without
editing its source - either on demand, or on a simple local interval -
without a new scheduling framework.

## Components

| Module | Responsibility |
|---|---|
| `app/blocks/triggers.py` | `ManualTrigger` and `TimerTrigger` block contracts. Both are `block_type="trigger"` and only ever emit a `ControlSignal` on a `kind="control"` port - never tabular data. `TimerTriggerConfig.interval_seconds` is bounded (1 second to 24 hours: "bounded Timer"). |
| `app/runs/scheduler.py` | `TimerScheduler` / `_Timer`: one background thread per running pipeline timer, single-process and in-memory only. |
| `app/pipelines/api.py` | `POST .../execute`, `POST .../timer/start`, `POST .../timer/stop`, `GET .../timer`, nested under the existing pipelines router. |

```text
POST .../execute ────────────────────────▶ execute_revision(db, executor, revision_id)
                                                  (#27's engine entry point)

POST .../timer/start ──▶ read trigger.timer node's saved config ──▶ TimerScheduler.start
                                                                           │
                                               thread: wait(interval) ─▶ run ─▶ loop
                                                                           │
POST .../timer/stop ───▶ TimerScheduler.stop ─▶ cancels + joins the thread
```

## Design decisions

- **Execute selects the latest saved revision, optionally guarded.** The body
  may contain `{"expected_revision": 1}` (#33). It must be a positive integer;
  omission or null preserves legacy behavior. If it differs from the latest
  saved revision, the API returns `409 revision_conflict` without creating a
  run. The check and immutable revision-ID capture use the same transaction;
  a later save cannot silently change the selected execution. There is no separate
  "validate before execute" step: `Executor.execute` already validates (#21)
  before running anything, and an invalid pipeline creates no run row, same
  as calling `execute_revision` directly. The API only adds a structured
  `invalid_pipeline`-style error response (the first diagnostic, same shape
  `PipelineDefinition.validate_registry` already uses) on top of that.
- **The timer's interval lives in the saved pipeline, not the request.**
  `timer/start` takes no body: it reads `interval_seconds` from the
  pipeline's own `trigger.timer` node, re-validates it with
  `TimerTriggerConfig` (pipelines are saved without block-level validation,
  by existing design - see `/pipelines/validate`), and only then starts the
  timer. A pipeline with no Timer trigger, or an invalid interval, is refused
  with a structured 422 before anything starts.
- **No-overlap is structural, not a lock.** One dedicated thread per running
  timer both waits out the interval and runs the pipeline, in that order, in
  a loop; the next wait cannot start until the current run has returned, so
  two ticks of the same timer can never be in flight together. This also
  means a block slower than the interval simply delays the next tick rather
  than overlapping it.
- **Stopping is cooperative, not preemptive.** `stop()` sets the pipeline's
  `Cancellation` token immediately and then waits (bounded by a timeout) for
  the thread to return. A block already running cannot be interrupted mid-call
  (Python cannot preempt a thread), so a one-node timer's in-flight run still
  finishes successfully and is recorded truthfully as `succeeded`. If Stop arrives
  after a tick is accepted but before its block starts, the run is `cancelled`.
  Cancellation only skips
  work that has not started yet, exactly like the rest of the executor.
- **A timed-out `stop()` is reported honestly, not swallowed.** If the bound
  elapses while a block is still running, `stop()` raises `TimerStopTimedOut`
  (surfaced over HTTP as a retryable `409 timer_stop_timed_out`) rather than
  returning as if the timer were gone. The timer stays registered as
  stopping, so a replacement `start()` for the same pipeline is rejected
  until the old thread has actually exited - never left free to run the same
  pipeline concurrently with it. The loop's own decision to start a tick and
  `stop()`'s decision to cancel/signal share one lock, so a tick can never
  begin after `stop()` has already set the stop signal, even if the tick's
  own interval wait happens to time out at that exact instant.
  `stop_all()` (used at application shutdown, right before the database is
  closed) takes the stricter option instead of the bounded one: it falls
  back to an unbounded wait rather than ever letting shutdown proceed while
  a timer thread might still touch the database.
- **No persistence, no cron, no distributed guarantees.** Timers exist only
  in the process's memory. A restart loses every running timer - callers
  must call `timer/start` again - and if the process dies mid-tick, the
  normal `recover_interrupted` startup path (#27) closes the stuck `running`
  row the same way it would for any other crash. This is a deliberate Release
  1 scope limit, not an oversight: see the engineering notes on issue #29.

## Limitations

- Timers are per-process and non-durable; there is no multi-instance or
  multi-process coordination, and nothing survives a restart.
- A single, long-running block cannot be stopped mid-execution; only the
  *next* tick is prevented.
- `execute` always targets the latest revision; there is no way to execute
  an older, specific revision through this API. `expected_revision` is a
  precondition, not a historical-revision selector. See [error recovery](error-recovery.md).
