# Contextual error recovery (#33)

## Design

Reuse Builder validation, selected-node preview and saved-run controls. Recovery
only selects configuration or retries a read; it never reloads or rewrites the
user's draft. Preview remains bounded and side-effect free. Monitoring/history
belongs to #30 and is not duplicated here.

- Validation diagnostics apply only to the current semantic draft. Existing
  field focus and fallback recovery notices remain the shared navigation path.
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
- Failed result reads can be retried without another execution. Execute itself
  is never automatically retried: a lost response may hide a started run.
  Recovery text distinguishes that uncertainty from a definite revision refusal.
- The API supplies redacted runtime reasons. Request failures use fixed public
  client messages rather than arbitrary HTTP bodies or thrown exception text.

## Tradeoffs and integration

An optional revision precondition preserves older clients while protecting the
Builder from executing a newer teammate save. Merely comparing revision numbers
in the UI after execution would discover the mistake too late. Holding a write
lock for the whole execution is unnecessary because revision records are immutable.

This work adds recovery to existing controls; it does not import unmerged #30
monitoring changes. That work can reuse the revision guard and configuration
focus path. History without a matching saved snapshot must not present errors as
current-draft diagnostics. Independent review and stakeholder acceptance remain
separate from automated verification.
