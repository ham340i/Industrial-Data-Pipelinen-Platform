# Release 2 baseline audit

Audited on November 24, 2026 against `main` at `b51bd93` (after #118). Every status below was re-measured on that commit; earlier audit findings were not carried over without checking.

## Sources

| Source | Where | Notes |
|---|---|---|
| Code Quality Rubric (Releases 1 to 3) | Course document supplied by the team, not in the repository | Thresholds quoted below are from this document |
| Overall Capstone Grading Scheme | Course spreadsheet supplied by the team | R1, R2 and R3 team-grading tabs |
| Release Presentation guide | Course document supplied by the team | Slide order and timing |
| Structure for SOEN 490 | Course document supplied by the team | Repository, issue, tagging and wiki rules |
| Original project proposal / Project Overview | **Not found** in the repository or supplied files | Needed to confirm Release 2 scope; see [scope](../releases/RELEASE_2_SCOPE.md) |
| Release 1 plan and deferred scope | [release-1-plan.md](../release-1-plan.md) | Lists what Release 1 excluded |
| Milestone dates | GitHub milestones 5 to 8 | Iteration 5 Dec 1, 6 Dec 15, 7 Jan 19, 8 (Release 2) Feb 5 |

## Measurements on `b51bd93`

| Measure | Result | How measured |
|---|---|---|
| Backend tests | 1,141 passed, 1 skipped (Linux-only benchmark) | `python -m pytest`, Python 3.12, Linux |
| Python files over 500 lines | 0 | Non-blank lines in `app/` and `scripts/` |
| Python functions over 50 lines | 4: `native_folder_picker.choose_windows_folder` (95), `pipelines/api.update` (90), `preview/service.preview` (55), `runs/scheduler._run_once` (53) | AST line span |
| Python functions with complexity over 15 | 0 | `radon cc` |
| Frontend functions over 50 lines | 27 in 17 files | ESLint `max-lines-per-function` (50, blank lines and comments skipped), tests excluded |
| Frontend functions with complexity over 15 | 12, worst `schema.fieldSchema` 43, `schema.validValue` 41, `RunControls` 40, `BlockConfigPanel` arrow 28, `PipelineControls` 25, `WorkspaceSettings` 24 | ESLint `complexity` (15) |
| Source files with an AI declaration | 190 of 225 (84%) | `scripts/check_ai_declarations.py` |
| Merged feature/fix PRs with an `AI contribution:` level | 2 of 38 (5%) | PR bodies; most have an "AI Assistance" section without the required level |
| Merged feature/fix PRs with a substantive pre-merge review | about 16 of 38 (42%) | Non-author, non-bot review or comment before merge that names a technical property; #51 and #55 matched keywords but were not technical and are excluded |
| User stories with statement, points, hours, priority, risk, feature label, milestone | 34 of 34 | Issue bodies and labels |
| Closed stories with recorded customer signoff label | 0 of 34 | No `stakeholder:*` label exists; the [Release 1 signoff](../stakeholder/release-1-signoff.md) is recorded as a document |
| Git tags / GitHub Releases | none | `GET /tags`, `GET /releases` |
| Release 2 issues | none; milestones 5 to 8 are empty | GitHub milestones |

## Historical findings rechecked

| # | Finding (earlier audit) | Current status | Evidence | Missing work | Priority | Suggested owner | Issue |
|---|---|---|---|---|---|---|---|
| 1 | Incomplete end-to-end pipeline integration | **Resolved** | Release browser tests author, preview, validate, run, inspect Parquet, reopen and rerun against the real API (`frontend/release-tests/author-preview-execute.spec.ts`, `sql-workflow.spec.ts`); CI "Release candidate rehearsal" passes | None for Release 1 scope | n/a | n/a | #31, #36 |
| 2 | Missing SQL, Join, Aggregate, Schema Validation | **Resolved** | `source.sql`, `transform.join`, `transform.aggregate`, `quality.schema_validation` in the block catalog with unit and integration tests (`test_sql_block.py`, `test_transform_blocks.py`, `test_quality.py`, `test_integration_matrix.py`) | None | n/a | n/a | #23, #24, #25 |
| 3 | Preview, execution, monitoring, querying not integrated | **Resolved** | Builder preview, Run controls, Run monitor and Output inspection call the real API; covered by release and standalone browser suites | None for Release 1 scope | n/a | n/a | #26, #29, #30, #28 |
| 4 | Insufficient substantive PR review evidence | **Still open** | About 42% of merged feature/fix PRs have a substantive pre-merge review | Release 2 needs at least 85% for Exceptional; every Release 2 PR needs a technical review comment before merge | Critical | All reviewers | to create |
| 5 | Missing AI contribution declarations | **Still open (partly)** | Files 84% (rubric check needs 90%); PR level stated on 5% of feature/fix PRs (needs 90%) | Add declarations to the 35 files listed by the checker; every Release 2 PR states a level; authors may amend their own Release 1 PR descriptions | Critical | File and PR authors | to create |
| 6 | Incomplete individual contribution records | **Still open** | `docs/individual-contributions/` has none for adamoug, GeorgesOgeil, PenguKev; others miss iterations | Each student writes their own Release 1 record and keeps Release 2 records per iteration | Critical | Each student | to create |
| 7 | Outdated architecture and Wiki documentation | **Partly resolved** | Wiki has 23 pages including architecture and deployment; workspace storage from #114 is documented in `docs/architecture/workspace-settings.md` but not in the Wiki architecture page | Update Wiki architecture for #114 and each Release 2 change; republish the Wiki | Medium | ham340i | to create |
| 8 | Incomplete stakeholder acceptance evidence | **Partly resolved** | [Release 1 signoff](../stakeholder/release-1-signoff.md) recorded (Taconics, represented by ham340i) | Signoff label on accepted stories; Release 2 signoff per feature; partner name still Pratt & Whitney Canada in README, Wiki Home and plans | High | ham340i | to create |
| 9 | Incomplete operational logging and failure recovery | **Resolved for Release 1** | `app/logging_config.py`, structured logs with correlation IDs, run recovery after restart (`test_execution_failures.py`, `test_run_telemetry.py`) | Logging for each Release 2 feature | Low | Feature owners | per feature |
| 10 | Missing release tags and reproducible release evidence | **Still open** | No tags or Releases exist; Release 1 gate evidence names candidate `5d05187`, while `main` has moved on (#114, #116, #118) | Choose the Release 1 commit, update the tag checklist, tag `Release1`, publish the GitHub Release; also tag past iterations if the team agrees | Critical | ham340i | #38 |

## New findings

| Finding | Evidence | Required action | Priority | Owner |
|---|---|---|---|---|
| Windows browser tests fail intermittently on `main` | `Standalone workspace smoke (windows-latest)` red on `bf7d963`; cause traced to a remount race from #114 | Review and merge #119 | Critical | joedaswagger to review |
| Frontend complexity well above the rubric limit | 12 functions over complexity 15 (up to 43) | Refactor `configuration/schema.ts`, `RunControls`, `PipelineControls`, `WorkspaceSettings`, `BlockConfigPanel` with tests kept green | High | Al-Yousef (schema/config), joedaswagger (run and workspace UI) |
| Four Python functions over 50 lines | Listed above | Split or document the exception (the Windows picker wraps a single COM call sequence) | Medium | menaboulus (scheduler), joedaswagger (picker, preview), ham340i (pipelines API) |
| No LICENSE file | Repository root | Team decision (course recommends MIT) | High | Team |
| No GitHub Project board linked | README "Project board" section | Create, share with `moar82`, link in README | High | ham340i |
| Team roster mismatch | Release 2 brief lists 8 students; GitHub history has 10 contributors (GeorgesOgeil and PenguKev merged #88 and #84) | Confirm whether GeorgesOgeil and PenguKev are still on the team | High | ham340i |
| Original proposal not in the repository | Search of repository and supplied files | Add the approved Project Overview (or its scope section) so Release 2 scope can be traced | High | ham340i |
