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
