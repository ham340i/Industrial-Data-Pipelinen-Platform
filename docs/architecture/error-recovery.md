# Contextual error recovery (#33)

## Design

Reuse Builder validation, selected-node preview and saved-run controls. Recovery
only selects configuration or retries a read; it never reloads or rewrites the
user's draft. Preview remains bounded and side-effect free. Issue #30 provides
run history and monitoring through the shared run API.

- Validation gates execution against the current semantic draft. During
  revalidation, the previous diagnostics are marked as stale and their
  navigation actions are disabled. Fieldless recovery focuses an invalid
  configuration control, the first editable control, or the region when no
  editable control is available.
- Preview errors refer to the exact requested draft and a node present in that
  snapshot. An unknown node or pipeline-wide failure stays a readable notice.
  Retry and cancellation keep keyboard focus on the persistent preview control.
  Edits, selection and project changes discard stale responses.
- Run sends the opened saved revision as an optional expected_revision. The
  server checks it when selecting the immutable revision ID; a conflict creates
  no run. Legacy no-body clients and timers retain their existing behavior.
- Run results retain their actual revision. A failure can focus configuration
  only while the result revision and semantic draft match the submitted saved
  snapshot. Newer unsaved edits stay untouched and historical failures are
  labeled instead of being applied to the new graph.
- A result refresh keeps the last loaded run status and evidence visible.
  A failed refresh labels that evidence and offers a GET retry. A client-error
  response reports a refusal. A transport failure, malformed acknowledgment or
  unexpected server failure directs the user to run history before trying again.
- The API supplies redacted runtime reasons. Request failures use fixed public
  client messages rather than arbitrary HTTP bodies or thrown exception text.

## Tradeoffs and integration

An optional revision precondition preserves older clients while protecting the
Builder from executing a newer teammate save. Merely comparing revision numbers
in the UI after execution would discover the mistake too late. Holding a write
lock for the whole execution is unnecessary because revision records are immutable.

The saved-run controls and the #30 monitor share the run detail parser and cache.
History without a matching saved snapshot presents historical evidence. Independent
review and stakeholder acceptance remain pending.
