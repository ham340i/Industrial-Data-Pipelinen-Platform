# Testing Evidence

Status: Foundation checks verified October 4, 2026; full iteration demonstration and acceptance remain pending. Main revision: `eef36f34946746cb57c66e88c0b3af81ab3c7d98`. See the [team audit](../../team-readiness-2026-10-04.md) for current delivery/review evidence.

## Automated Tests

The merged foundation has API/schema/error tests, frontend interaction/client tests and controlled harness-failure tests. Original executed counts and environments are preserved in the [workbench record](../../testing/issue-5-workbench.md), [harness record](../../testing/issue-11-test-harnesses-ci.md) and [workspace record](../../testing/issue-4-local-workspace.md). Latest main's backend/frontend checks passed; these results do not establish tests for undelivered SDK/DAG/ETL stories.

## Integration Tests

Main CI passed the real Compose/Chromium smoke: API and proxy health, shell/direct navigation, non-root services, marker persistence across container recreation and isolated teardown. The marker does not verify metadata models. PR #48 separately tests real SQLite/migrations and remains pending review. PR #51 tests corrected client/API contracts and Windows harness portability; all six hosted checks passed while independent review remains pending.

## Manual Verification

Actual iteration/stakeholder demonstration is not recorded. Use the prepared [demo plan](demo.md), then record commit, environment, observed failures/passes and accessible evidence.

## CI Results

- Main `eef36f3`: [CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/37232745680) and [documentation](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/37232745665), successful.
- Metadata PR #48 `a23c8e5`: [CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/37247597035) and [documentation](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/37247597034), successful; six checks passed, pending review/merge.
- Integration PR #51 `f585040`: [CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/37254078423) and [documentation](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/37254078437), successful; six checks passed, pending review/merge.
- SQL spike PR #52 `5f1f5d6`: [current checks](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/52/checks), all six successful; 23 SQL feature tests passed locally, but [additional synthetic probes](../../testing/pr-52-sql-review.md) reproduce three missed result-corruption cases. Pending corrections and review.

## Failed Tests / Known Problems

The existing harness record documented duplicate correlation headers and a standalone health mismatch. PR #51 reproduces them before correcting production code: 4 backend and 11 frontend failures. Windows execution also exposed POSIX pytest configuration, text line endings and overly short tool-test timeouts; corrections retain every failure-propagation assertion. The metadata/integration PRs are not yet on main. SDK/DAG/first ETL proof have no published implementation PR. A deliberately failing hosted Actions commit followed by recovery remains unrecorded for issue #11.

## Environment

Hosted application checks target Python 3.12 and Node 24 on `ubuntu-latest`, with pinned image digests and locked dependencies. Earlier local environments are preserved in their source records. PR #51's local correction was verified on Windows with Python 3.12.10/Node 24.19.0; Docker was unavailable locally and the real stack was verified remotely.

## Commands Used

Actual package commands and complete outputs are linked from the verification records and workflow runs: locked dependency install; Ruff lint/format; mypy; pytest; frontend `npm run check`; Playwright; `scripts/smoke_workspace.py --browser`; repository/docs/release-plan checks. Each owner must add exact commands, fixtures and results for their later delivered stories.

## Evidence Links

Use the linked workflow runs, [updated traceability](../../release-1/traceability.md) and [team audit](../../team-readiness-2026-10-04.md). A recorded independent PR approval is separate from an author's personal learning, a real iteration demo and stakeholder acceptance.

## Foundation validation during repository organization

The [organization audit](../../testing/iteration-structure-validation.md) records 19 passing local tests, including five API tests on the unchanged FastAPI foundation from `219f067`. This is limited foundation evidence; full iteration testing, integration and demonstration remain pending.

## Workspace issue #4

See the [workspace verification](../../testing/issue-4-local-workspace.md) for real-service smoke results, acceptance mapping and remaining review requirements. Full iteration acceptance is not inferred.
