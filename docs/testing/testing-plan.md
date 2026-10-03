# Testing plan

## Current state and philosophy

No application or product tests exist. Repository tooling is checked with Python standard-library unit tests, syntax validation, local Markdown links and configuration checks. Product testing must demonstrate observable correctness under representative inputs, including failure paths; passing repository CI is not product validation.

## Planned product testing

| Layer | Required evidence when implemented |
|---|---|
| Unit | Block contracts, graph validation, schema mapping, nulls, types and deterministic transformations |
| Integration | Connector → engine → validator → output using synthetic fixtures and isolated storage; credentials supplied only in approved environments |
| End-to-end | Author a pipeline, run it, inspect previews/errors, save/reload and reproduce a run |
| ETL correctness | Golden outputs, row counts, join cardinality, ordering assumptions, numeric precision, encodings, dates/time zones and idempotency |
| Data validation | Schema drift, missing fields, duplicate keys, invalid types, quality-rule thresholds and rejected-row policy |
| Regression | A failing reproducer for each fixed defect where practical |
| Performance | Representative sizes, runtime, peak memory and preview latency; see [measurement plan](../performance/performance-plan.md) |
| Security | Path traversal, malformed/oversized files, unsafe queries, credential leakage, API exposure and dependency review |
| Manual | Keyboard navigation, readable error messages, install/upgrade, cancellation and recovery |
| Stakeholder acceptance | Demonstrated revision, acceptance criteria, authorized feedback and linked [signoff](../stakeholder/signoff-template.md) |

Use deterministic synthetic fixtures by default. Stakeholder data requires explicit approval and must stay outside Git. Define tolerances for numeric results; never silently relax expected outputs to make tests pass.

## CI integration

Current commands are in [README](../../README.md#running-tests); results belong in [validation](repository-validation.md). Workflows run on PRs and pushes to main with read-only permissions. No runtime dependencies exist, so installation/caching, product lint/format/type checks, application tests, build and dependency audits are not applicable yet. With the first application PR, commit the chosen ecosystem lockfile, use frozen installs and dependency caching keyed by it, and add actual lint/format/type/test/build commands. Add integration checks when the components exist.

## Ownership and review

The issue owner owns test design, fixtures and recorded evidence. An independent teammate reviews expected outcomes, failure cases and acceptance criteria, then approves the PR after CI passes. Record skipped checks with reasons; a skipped required test is unresolved work. The release coordinator collects results at the release revision. Owners are assigned per issue; no team roster is fabricated.

## Definition of Done

Apply the [project-wide checklist](../planning/definition-of-done.md). A story needs tests appropriate to its behavior, passing CI, independent review and required stakeholder evidence. Attach command, revision, environment, result and any limitations to the PR and iteration record.

## Issue #11 application harnesses and CI gates

Backend Ruff, mypy and pytest configuration, a hash-pinned lockfile, shared API fixtures, API contract tests and a `Backend checks` CI job were added alongside the existing frontend gate. Controlled harness tests in both stacks prove that a broken fixture makes each check fail. See [actual verification](issue-11-test-harnesses-ci.md). The "not applicable yet" statements under CI integration above describe the state before issues #5 and #11.

## Issue #5 frontend foundation

The first implemented feature adds Vitest/Testing Library/MSW tests and Playwright production-shell smoke tests. See [actual verification](issue-5-workbench.md) and [runnable commands](../frontend/workbench.md). Synthetic health mocks verify the UI boundary; they do not establish backend/engine integration or release acceptance.
