# AI assistance disclosure

Disclose meaningful AI assistance in each affected issue and PR, including generated code, designs, documentation, debugging and tests. Use `None` if no meaningful assistance occurred. Do not infer or retroactively attribute historical work to AI.

```text
AI Assistance:
- Tool:
- Purpose:
- Human contribution:
- Verification performed:
```

Recommended commit footer:

```text
AI-Assisted: Codex used for <purpose>; reviewed and verified by <contributor>.
```

Replace placeholders with facts. Do not claim human review until it happens. Contributors remain responsible for correctness, originality, security and understanding the work. Never send secrets, confidential agreements or unapproved stakeholder data to AI tools. Summarize assistance in iteration and release records.

## This repository foundation

- Tool: OpenAI Codex.
- Purpose: audit the initial README-only repository and draft repository tooling, templates and documentation.
- Human contribution: supplied project requirements; review/edits and acceptance pending.
- Verification performed: see [actual local validation](../docs/testing/repository-validation.md). Local checks do not establish product correctness or GitHub Actions success.

The Wiki navigation and publishing helper were also drafted with Codex from these repository documents. Local checks and source-link verification are recorded in the validation report; human review remains pending.

## Compliance follow-up

Codex inspected live GitHub configuration, configured supported labels/milestones/protection, drafted additional onboarding/consent/contribution documentation, and updated tooling/tests for milestone date normalization and maintained Wiki links. The user supplied requirements; independent human review remains pending. See [issue #2](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/2), its linked PR and the [compliance audit](../docs/SOEN490_COMPLIANCE_AUDIT.md) for actual verification. This does not claim a student personally authored the generated work.

## Release 1 planning

Codex drafted the Release 1 backlog, initial estimates, balanced primary/reviewer allocation, dependency graph, target-architecture documentation and plan checks from the supplied team brief. The brief supplies the partner, stack, roster, dates and product goal; it does not establish implementation or stakeholder approval. Student refinement, design, code, tests, reviews and signoffs remain future work. Live issue creation/assignment is planning activity, not an individual student contribution claim.

## Iteration structure reorganization

Tool: OpenAI Codex. Used to inspect repository/GitHub state and draft iteration, acceptance, traceability and workflow documentation. The user supplied the scope and preservation rules; human review and acceptance remain pending. Existing application implementation and student work retain their authorship. Actual checks and limitations are recorded in the [organization audit](../docs/testing/iteration-structure-validation.md).

## Issue #17 configuration panel

Tool: OpenAI Codex. Yousef directed delivery. Codex adapted the earlier local
panel draft to the merged graph/registry/persistence/validation contracts, added
tests, fixed mobile canvas sizing and executed the checks and browser demonstration.
See the [verification record](../docs/testing/issue-17-configuration.md) and
[individual record](../docs/individual-contributions/Al-Yousef-iteration-2.md).
PR #66 subsequently received @ham340i's approval and merged October 21, 2026.
Stakeholder acceptance remains pending.

## Iteration 2 sources, transforms and sinks (#16, #18, #20)

Tool: OpenAI Codex. Yousef directed the expanded delivery. Codex reused the
existing team headless proof and SDK contracts, implemented the bounded file
adapter and nine blocks, added golden/negative/integration/browser tests,
prepared documentation, and ran the recorded checks and real browser
demonstration. Historical authorship remains intact. The original issue owners
remain assigned; their independent review and stakeholder acceptance are pending.
See [verification](../docs/testing/iteration-2-file-blocks.md) and
[Yousef's actual contribution record](../docs/individual-contributions/Al-Yousef-iteration-2.md).

## Issue #10 headless ETL proof

Codex authored the bounded SDK/DAG runner, Polars selection, Parquet read-back
verification, synthetic fixtures, regression tests and documentation at
the user's request. The user selected the issue and requested a PR; independent
human review and stakeholder acceptance remain pending. Actual verification and
limitations are recorded in [the testing evidence](../docs/testing/issue-10-headless-etl.md).

## Issue #27 run telemetry

Tool: Claude Code. Assisted with the run recorder, interrupted-run recovery,
log redaction, run status/detail APIs and their tests
([PR #74](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/74)).
Verified by 30 automated tests ([record](../docs/testing/issue-27-run-telemetry.md)).
Correction found in review: two failure logs included full exception text,
which could leak bound SQL values, and were reduced to the exception type.

Further corrections found in `ham340i`'s review of
[PR #74](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/74)
(Claude Code, verified by new/updated automated tests, one per item):
the `0002` migration dropped and recreated `runs` via a batch CHECK-constraint
add, which fails with a foreign-key error on any workspace that already has
artifact rows referencing a run; changed to plain `ADD COLUMN`/`DROP COLUMN`
(no table rebuild) and moved the `duration_ms >= 0` invariant from a DB CHECK
constraint to an ORM `@validates` method. The credential redactor's
key/value regex missed JSON-quoted keys (`"password": "..."`) entirely and
truncated quoted multi-word values at the first space; both are now matched
and replaced in full. It also only redacted backslash-style Windows paths,
missing forward-slash absolute paths (`C:/Users/...`); the path rule now
matches both separators. The run/block row-count recorder collapsed "no
tabular data was measured" (e.g. a trigger emitting only a `ControlSignal`)
into a reported `0`, indistinguishable from a genuinely empty table; it now
preserves `None` for unmeasured counts while keeping the separate, intentional
convention that a block with no input edges at all reports `rows_in=0`.

A follow-up review on the same PR found the redaction fix above was still
incomplete: its quoted-value regex excluded both quote characters
universally (`[^"']`) instead of only the matching delimiter, so a credential
containing the *other* quote character, or an escaped matching quote, either
skipped the redaction rule entirely or had the match end early and leak the
remainder - confirmed persisted in `Run`/`RunBlock.error_reason` and returned
from `GET /api/v1/runs/{id}`. Replaced with a delimiter-specific,
escape-aware pattern (`"(?:\\.|[^"\\])*"` / the single-quote equivalent) and
added regression tests covering both quote types, escaped quotes, and the
persistence/API path directly, not just the redactor unit.

A second follow-up found the JSON/dict-style rule still only matched when
the dictionary key and value used the *same* quote style (e.g.
`{"password": "secret"}` or `{'password': 'secret'}`); a mixed pair like
`{"password": 'secret'}` matched neither that rule nor the bare key=value
rule, so the value passed through completely unredacted - again confirmed
persisted and returned from the API. The key's quote style is now matched
independently of the value's, and a regression test was added for both
mixed-style orderings.

## Issue #29 Manual and Timer triggers, execute API

AI contribution: below 50%.
Tool: Claude Code. Assisted with the Manual/Timer trigger block contracts,
the execute and timer start/stop/status APIs, the single-process no-overlap
interval scheduler, and their tests
([design](../docs/architecture/triggers-and-execute.md),
[verification](../docs/testing/issue-29-triggers-and-execute.md)).
Verified by 24 new automated tests (702 passing overall), run twice to rule
out timing flakiness, plus manual smoke tests of every execute/timer HTTP
path against a real SQLite database before the automated tests were written.

Two mistakes were caught and corrected during development, not after:
a `zip(..., strict=True)` in a test helper's deliberately length-offset
pairwise comparison always raised (fixed to `strict=False`), and an initial
assumption that stopping a timer mid-execution would mark a single-block run
`cancelled` was wrong - cooperative cancellation cannot preempt a block
already running, so it finishes and is correctly recorded as `succeeded`.
The test and the design doc were corrected to document the real behavior.

`adamoug`'s review of [PR #76](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/76)
found four real concurrency gaps in the stop/shutdown path, all confirmed
and fixed, not argued with: a timed-out `stop()` returned as if the timer
were gone while its thread could still be running; that same timed-out
`stop()` left the pipeline id free for a replacement timer to start
concurrently with the old thread's still-finishing block; the loop's
stop-check and `stop()`'s own signal/cancel step used separate locks,
leaving a window where a tick could start at the exact instant `stop()`
ran; and `stop_all()` (used right before the app closes the database at
shutdown) had the same bounded-join gap, so a slow block could still be
running under a database the shutdown path had already closed. Fixed by
having `stop()` report whether the thread actually exited (raising a new
`TimerStopTimedOut`, mapped to a structured 409, instead of lying), keeping
a timed-out timer registered until it truly exits, merging the stop-check
and signal/cancel onto one lock, and making `stop_all()` fall back to an
unbounded join so it never returns early. See
[the updated verification record](../docs/testing/issue-29-triggers-and-execute.md)
for the four regression tests, including a deterministic one that drives
the exact lock race instead of relying on timing.

## Issue #33 validation recovery

OpenAI Codex implemented the validation recovery slice and its regression
tests using the team's existing Builder, configuration and validation
contracts. See the [verification record](../docs/testing/issue-33-validation-recovery.md)
for checks and integration dependencies. The issue requirements came from
the team. Independent teammate review and acceptance remain pending.

On November 9, Yousef requested completion of his remaining capstone work.
Codex audited the draft, reproduced and fixed private-error disclosure and
missing keyboard-focus cases, added regressions, ran the recorded checks and
updated iteration/contribution evidence. See the same verification record for
failed attempts, final results and unresolved preview/run dependencies.

On November 11 (UTC), Codex reconciled PR #81 with current main, retained both
contributors' documentation, and reran the checks recorded above. The work
updates the existing draft branch; it does not claim independent approval or
completion of the remaining preview/run error-recovery acceptance cases.

## SQL source and workflow preparation (#23, #31)

Tool: OpenAI Codex. The user requested work on assignments for `aboudka2003`.
Codex generated a registered SQLite source, bounded-query integration, saved-run
controls, tests, design and operator documentation, and ran local verification.
An existing SQL row-width-check edit was preserved. Human design/code review,
CI and stakeholder acceptance remain pending. Issue #31 is dependency-blocked
for preview and artifact inspection. See the
[verification record](../docs/testing/issue-23-31-sql-workflow.md); this does not
claim that the student manually authored or independently tested generated code.
