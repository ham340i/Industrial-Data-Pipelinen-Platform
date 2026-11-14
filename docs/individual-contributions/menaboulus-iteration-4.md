# menaboulus – Iteration 4 (Release 1)

Period / release: Iteration 4, Release 1 (due November 17, 2026).

## Summary

Issue [#37](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/37):
an API/engine/SQLite integration matrix over the production block catalog.
It found and fixed two cross-feature contract mismatches that no feature's own
tests could see, and added shared response fixtures that both the backend and
the Builder parsers check in CI. Record of what was actually run:
[verification](../testing/issue-37-integration-matrix.md).

## Engineering Design

- Drive the real application (FastAPI `TestClient`, real SQLite metadata,
  real project workspace folder prepared by the project API) rather than
  calling blocks directly, so the matrix tests the adapters between
  features (#21 validation, #26 preview, #27 telemetry, #28 artifacts, #29
  execute) and not the blocks again.
- One synthetic dataset shared by every source format, so a case can assert
  identical rows regardless of reader; SQLite's missing boolean type is
  declared explicitly instead of hidden.
- Contract drift is caught by *shape*, not values: fixtures captured from the
  real API are compared by keys and JSON types on the backend and parsed by
  the frontend's own guards, so neither side can change a response alone.
- Alternative considered: a Playwright end-to-end run. Rejected for this
  issue because the acceptance workflow (#38) already owns it and an
  API-level matrix is faster, deterministic and runs on every PR.

## Implementation

- `tests/integration_support.py`, `tests/conftest.py` (`bench` fixture)
- `tests/test_integration_matrix.py`, `tests/test_integration_failures.py`,
  `tests/test_integration_contracts.py`, `tests/fixtures/contracts/*.json`
- `frontend/src/api/contracts.test.ts`, `frontend/vite.config.ts` (JUnit on CI)
- Fixes: `app/artifacts/api.py` (project-scoped artifact query),
  `app/blocks/files.py` (sink creates a missing output folder),
  `app/workspace.py` `project_data_folder` shared by `app/preview/service.py`,
  `app/pipelines/api.py` and `app/runs/scheduler.py` (review follow-up);
  `tests/test_artifact_api.py` updated to register files where execute
  publishes them
- `.github/workflows/ci.yml`: JUnit capture and artifact upload for the
  backend and frontend test steps
- Docs: `docs/artifacts.md`, `docs/architecture/artifact-governance.md`,
  this record and the verification record

## Issues

- [#37](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/37) (primary owner)

## Pull Requests

- [PR #85](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/85) (author), opened November 12, 2026 from
  `feature/37-block-integration-matrix`; review requested from `Al-Yousef`,
  the planned reviewer per the issue. Review and merge pending.

## Commits

On `feature/37-block-integration-matrix`, each referencing #37; see the
[commit list on PR #85](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/85/commits).

## Tests

39 new backend tests and 4 frontend parser tests; full backend suite 880
passing with Ruff, Ruff format and mypy clean. Commands, environment and
counts: [verification record](../testing/issue-37-integration-matrix.md#observed-results).

## Reviews

- Reviewed [PR #81](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/81)
  (Builder validation errors) on November 12, 2026 with six inline technical
  comments: a config-value leak through the pydantic error allowlist, an
  incorrect "may have started a run" message for refused 4xx responses, run
  detail disappearing on one failed poll, a status live region flapping on
  every poll, diagnostics flashing on every keystroke, and a removed focus
  fallback. Follow-up by the author is pending.

## Problems Solved

- Artifacts produced by a real run returned `409 artifact_unavailable` from
  the query API because execute publishes under the project folder and the
  query resolved under the bare workspace root. Found by the Parquet sink
  cases, fixed in the artifact API, pinned by those cases.
- A sink into `outputs/...` failed with a misleading atomic-publication
  error because only `inputs/` is pre-created. Fixed in the sink; pinned by
  a regression test.

- Al-Yousef's review of PR #85 showed the project-scoped query trusted a
  symlinked project folder, that execute and timers had the same gap, and
  that the contract bridge was type-only. Fixed with one shared containment
  rule and parser-rule checks on both sides; see the
  [review section](../testing/issue-37-integration-matrix.md#al-yousefs-review-of-pr-85).

- The re-review found the listing-based lookup broke case-only renames on
  case-insensitive filesystems and that the contract bridge was not bound
  to the Builder's request ids and pagination; both fixed with tests, see
  the [re-review section](../testing/issue-37-integration-matrix.md#al-yousefs-re-review-of-pr-85-at-48adc20).

## Failed Attempts / Experiments

- First version of the status-path test ran the same no-clobber CSV sink
  twice and "found" a failure that was the documented `output_exists`
  behaviour. Corrected the test rather than the product.
- First frontend contract test used `new URL(..., import.meta.url)`; Vite
  rewrote it into an asset import and refused to serve a file outside the
  package. Switched to `node:path` resolution.

## What I Learned

Feature-level tests can all pass while the product path between two features
is broken: #28's tests placed files where #28 looked, not where #29 writes.
Integration fixtures that go through the real API are the only tests that
would have caught it.

## AI Assistance

Tool: Claude Code (Anthropic). AI contribution: 50% or more AI-generated.
Generated/suggested work: the integration fixtures, matrix and failure-path
tests, contract fixtures and their frontend test, the two fixes, the CI
capture steps and the documentation drafts, run and corrected against the
real suite. My own design, changes and verification: issue selection,
scope and constraints (no co-author trailers, repository quality rules),
decision to keep the two documented behaviours unchanged, and the review of
PR #81 as recorded above. Independent human review of the generated code is
pending on the pull request.

## Evidence Links

Design and results: [verification record](../testing/issue-37-integration-matrix.md)
→ code on `feature/37-block-integration-matrix` → [PR #85](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/85) (review pending) →
CI: on the PR → iteration: [Iteration 4 testing evidence](../iterations/iteration-4-release-1/testing-evidence.md).

## Record identification

Developer: menaboulus
Iteration: 4 (Release 1)

## Assigned Stories

[#37](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/37);
design, implementation, tests and reviews are described in the sections above.

## Problems Encountered

Unresolved: none known. Deferred by design: wall-clock timeout simulation and
throughput, see the verification record's limitations.

## Independent Learning

Vite's `import.meta.url` asset rewriting and its `server.fs` allow-list
(found while making the shared fixtures readable from the frontend tests);
SQLite progress handlers as a deterministic work budget instead of
wall-clock timeouts.
