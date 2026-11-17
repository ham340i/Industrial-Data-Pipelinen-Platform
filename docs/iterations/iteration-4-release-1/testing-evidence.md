# Testing Evidence

Status: Scoped results recorded below; whole-iteration acceptance is pending.

## November 9: issue #33 validation slice

[Draft PR #81](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/81)
contains validation retry, graph preservation, diagnostic focus and privacy
regressions. The follow-up passed 99 frontend tests and 708 backend tests with
one existing host-dependent skip, plus lint, formatting, types and build.
The Chrome/FastAPI validation scenario passed with real services.

[Detailed evidence](../../testing/issue-33-validation-recovery.md) records the
baseline revision, commands, environment, reproduced bugs, failed attempts and
dependency contracts. These are scoped checks, not full release acceptance.
Preview/run integration, independent review and stakeholder signoff are pending.
The remaining template sections below cover whole-iteration evidence.

## November 11: issue #33 preview/run recovery

The same [PR #81](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/81)
now extends merged preview #83 with snapshot-bound configuration recovery and
saved-run revision guards. Backend verification passed 858 tests with one existing
Windows symlink skip, plus Ruff and mypy. The [current verification record](../../testing/issue-33-validation-recovery.md#november-11-previewrun-extension-utc)
tracks final frontend/browser checks, failure cases and remaining human acceptance.
No independent student approval or whole-iteration acceptance is claimed.

## Automated Tests

Not recorded. Add actual evidence and distinguish planned checks from executed checks.

## Integration Tests

Not recorded. Add actual evidence and distinguish planned checks from executed checks.

## Manual Verification

Not recorded. Add actual evidence and distinguish planned checks from executed checks.

## CI Results

Not recorded. Add actual evidence and distinguish planned checks from executed checks.

## Failed Tests / Known Problems

Not recorded. Add actual evidence and distinguish planned checks from executed checks.

## Environment

Not recorded. Add actual evidence and distinguish planned checks from executed checks.

## Commands Used

Not recorded. Add actual evidence and distinguish planned checks from executed checks.

## Evidence Links

Not recorded. Add actual evidence and distinguish planned checks from executed checks.

## Issue #30 feature verification

[Run monitoring evidence](../../testing/issue-30-run-monitoring.md) records actual
component, API and real-browser checks, environment and limitations. Whole-release
acceptance, independent review and stakeholder signoff remain pending.

## Issue #37 feature verification

[Integration matrix evidence](../../testing/issue-37-integration-matrix.md)
records the API/engine/SQLite compatibility matrix (39 backend tests, 4
frontend parser contract tests), the two cross-feature mismatches it found
and fixed, the exact commands, environment and counts, and the CI result
capture. Whole-release acceptance, independent review and stakeholder
signoff remain pending.

## November 16: issue #31 workflow integration

[Design](../../design/issue-31-workflow.md) and
[executed verification](../../testing/issue-31-workflow.md) cover nested
quality/aggregate forms, real validation, saved execution, governed output
inspection, and the full real-service Playwright acceptance scenario.
All prerequisite issues were closed when checked. Independent review and
stakeholder acceptance remain pending; this is not whole-iteration signoff.
