# Release 2 iteration plan

Dates are the GitHub milestone due dates from the course brief. Features refer to the [Release 2 scope](../releases/RELEASE_2_SCOPE.md), which is still a proposal until approved at the start of Iteration 5. Owners and reviewers are in [team allocation](TEAM_WORK_ALLOCATION.md).

Rule for every story: it closes only when its acceptance criteria are checked, its tests (success, invalid input, failure) pass in CI, a reviewer other than the author left a technical comment before merge, and the PR states its AI contribution level.

## Iteration 5: close Release 1 and set up Release 2 (to December 1)

| Objective | Issues / work | Acceptance criteria | Evidence of completion |
|---|---|---|---|
| Close Release 1 | Merge #119; choose the Release 1 commit; tag `Release1`; publish the GitHub Release with the deployment record | Tag exists; Release names commit, environment, date and outcome | Tag and Release URL |
| Approve Release 2 scope | Scope review with the stakeholder representative | Approved scope recorded with any changes | Signoff record for the scope |
| Stories ready | Create F1 to F9 stories with statement, points, hours, priority, risk, feature label, owner and reviewer | All 9 on the right milestones | Issue list |
| Design notes | One short design note or ADR per feature (alternatives, chosen approach, tests) | Linked from each story | `docs/architecture/decisions/` |
| Structure gap | Refactor the frontend functions over complexity 15, starting with `configuration/schema.ts` and `RunControls` | Complexity at most 15; all frontend tests pass | ESLint report in the PR |
| Declaration gap | Add AI declarations to the 35 files the checker lists | Checker reports at least 90% | `scripts/check_ai_declarations.py` output |
| F1 groundwork | Golden-output equality harness (eager vs lazy) on the synthetic datasets | Harness runs in CI and passes on the eager path | Test file and CI run |

Dependencies: scope approval before story assignment; #119 before the Release 1 tag.

## Iteration 6: backend cores (to December 15)

| Objective | Stories | Acceptance criteria | Testing |
|---|---|---|---|
| Lazy execution | F1 | Lazy chains for file sources and row-wise transforms; eager fallback with logged reason | Equality tests on all golden datasets; memory benchmark |
| PostgreSQL source | F3 (backend) | Secret references, SELECT-only, limits, typed output | CI PostgreSQL service; auth, timeout and bad-SQL tests |
| New transforms | F4 (backend) | Expression whitelist, type checks, Union, Deduplicate | Golden outputs; invalid expression and schema mismatch tests |
| Quality rules | F5 (backend) | Rules evaluated with counts and samples; warn or fail | Boundary values, empty input, all-fail cases |
| Schedules | F9 (backend) | Persisted cron schedules; restart recovery; no overlap | Restart test; missed-run policy tests |
| Revision API | F2 (backend) | List, diff, restore as new revision | Diff tests; restore keeps run links |

Checkpoint on December 8: each backend PR open for review.

## Iteration 7: product integration (to January 19, includes the holiday break)

| Objective | Stories | Acceptance criteria | Testing |
|---|---|---|---|
| Frontend for F2 to F5 and F9 | F2, F3, F4, F5, F9 | Configured and used from the builder; errors shown in context | Component tests; one browser test per feature |
| Preview profiling and keyboard connection | F6 | Profile within row budget; keyboard connection announced | Browser test using only the keyboard |
| Run comparison | F7 | Compare two runs; slow-run flag | Telemetry fixtures; UI test |
| Output query builder | F8 | Filter, sort, group, export CSV with limits | Server validation tests; browser test |
| End-to-end workflow | All | One release test builds a pipeline using a Release 2 block, runs it on a schedule, compares runs and exports output | Release browser suite on Linux and Windows |

## Iteration 8: stabilize and release (to February 5)

| Objective | Work | Acceptance criteria | Evidence |
|---|---|---|---|
| Security | Review new connectors and expressions against the Wiki security requirements | Every requirement has a test | `test_security_boundaries.py` additions |
| Performance | Measure F1 against eager on the 2M-row workload | Memory and time recorded with method | Performance Wiki page |
| Regression and quality | Full CI green; complexity and declaration checks pass | Structure and AI checks pass | Test report |
| Alpha deployment | Install the candidate on a tester workstation; run set tasks | Feedback recorded and triaged into issues | Feedback record |
| Documentation | Release notes, Wiki architecture and deployment pages, AI usage sections | Docs checks pass | Release notes |
| Release | Candidate rehearsal; stakeholder signoff; tag `Release2`; GitHub Release | Tag created only after tests, reviews and signoff | Tag and Release URL |
| Demonstration | Release 2 video with live demo and code walkthrough | Meets the presentation guide | Video link in README |

## Tracking

Progress is tracked on the GitHub milestones, and planned against actual points are recorded in each iteration's release notes. Any scope change is recorded on the story with its reason.
