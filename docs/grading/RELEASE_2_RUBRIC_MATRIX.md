# Release 2 rubric matrix

Status of `main` at `b51bd93` (November 24, 2026) against the Release 2 thresholds of the Code Quality Rubric and the Overall Capstone Grading Scheme. Measurements are in the [baseline audit](../audits/RELEASE_2_BASELINE_AUDIT.md). Statuses: PASS, PARTIAL, FAIL, NOT VERIFIED, NOT APPLICABLE (only where the rubric allows it). A PASS here is the team's own assessment, not a grade.

Owners are proposals until the team confirms them in [team allocation](../planning/TEAM_WORK_ALLOCATION.md).

## Code Quality Rubric (38% of the team grade)

### 1. Feature implementation and volume of work

Exceptional for Release 2: at least 8 substantive features and at least 85% of planned substantive stories implemented.

| Requirement | Current status | Exceptional requirement | Evidence | Required action | Owner |
|---|---|---|---|---|---|
| Substantive Release 2 features | NOT VERIFIED | 8 or more | No Release 2 stories exist yet; Release 1 delivered 14 substantive features | Plan 9 substantive features in [scope](../releases/RELEASE_2_SCOPE.md), so 8 completed is 89% | All |
| Planned stories implemented | NOT VERIFIED | 85% or more | Milestones 5 to 8 empty | Create the Release 2 stories, then close them only with tests and review | All |

The rubric does not say whether Release 1 features count again in Release 2. The plan assumes they do not.

### 2. Automated testing

Exceptional: at least 80% of features tested, at least 80% with an edge/error test, integration and project-specific tests satisfied.

| Requirement | Current status | Exceptional requirement | Evidence | Required action | Owner |
|---|---|---|---|---|---|
| Release 1 features tested | PASS | 80% | 1,141 backend tests pass; each Release 1 block family has success and failure tests; browser suites cover the workflows | Keep green | All |
| Integration testing | PASS | Demonstrated | `test_integration_matrix.py` (API, engine, blocks, SQLite, Parquet); release and standalone browser suites against the real API | Add one integration test per Release 2 feature | Feature owners |
| Project-specific testing (security, performance, data processing) | PASS for Release 1 | Satisfied | `test_security_boundaries.py`, `test_workload_benchmark.py`, golden-output transform tests | Extend for each Release 2 feature; record in [test report](../testing/RELEASE_2_TEST_REPORT.md) | Feature owners |
| Release 2 features tested with edge cases | NOT VERIFIED | 80% and 80% | Features not built | Acceptance criteria in every story require a success, invalid-input and failure test | Feature owners |

### 3. Code structure and maintainability (Exceptional: all applicable checks)

| Check | Current status | Evidence | Required action | Owner |
|---|---|---|---|---|
| 1. File size ≤ 500 lines | PASS | No Python or frontend source file over 500 non-blank lines | Keep | All |
| 2. Function size ≤ 50 lines | FAIL | 4 Python functions and 27 frontend functions over 50 lines | Split the long functions or document a specific exception (long React components are mostly JSX) | See audit |
| 3. Complexity ≤ 15 | FAIL | 12 frontend functions over 15, up to 43 | Refactor `configuration/schema.ts`, `RunControls`, `PipelineControls`, `WorkspaceSettings`, `BlockConfigPanel`, `RunMonitor`, `Projects`, `PreviewPanel`, `Canvas` | Al-Yousef, joedaswagger |
| 4. Class responsibilities | PASS | Block classes, services and recorders each have one job (`app/blocks/`, `app/runs/`) | Keep in review | Reviewers |
| 5. Coupling | PASS | Layered `api → service → engine → blocks`; no import cycles found | Keep | Reviewers |
| 6. Cohesion | PASS | Modules grouped by feature (`app/preview`, `app/runs`, `app/artifacts`) | Keep | Reviewers |
| 7. Duplication | NOT VERIFIED | No duplication scan in CI | Add a duplication report (SonarCloud already computes it) to the test report | menaboulus |
| 8. Unfinished/unused code | PASS | No TODO/FIXME for required behaviour in `app/` or `frontend/src` | Keep | All |
| 9. Architecture documentation | PARTIAL | Wiki architecture and domain diagrams exist; workspace storage changes from #114 are not in the Wiki | Update Wiki for #114 and each Release 2 change | ham340i |
| 10. Naming conventions | PASS | Wiki Naming Conventions page | Keep | All |
| 11. Performance considerations | PASS | Wiki Performance page; data budgets; spike #109 | Update when lazy execution lands | ham340i |

### 4. Input validation, error handling and logging (Exceptional: all 9)

| Check | Current status | Evidence | Required action | Owner |
|---|---|---|---|---|
| 1. Input validated | PASS | Pydantic models, block config schemas, graph validation | Same standard for new blocks | Feature owners |
| 2. Required/invalid values handled | PASS | `test_validation.py`, configuration panel tests | Same | Feature owners |
| 3. No silent exceptions | PASS | No bare `except: pass` in `app/` | Keep | Reviewers |
| 4. No internal details exposed | PASS | Error envelope in `app/schemas/errors.py`; redaction tests | Keep | Reviewers |
| 5. File/DB/external failure handling | PASS | `test_execution_failures.py`, `test_integration_failures.py` | Same for new connectors | aboudka2003 |
| 6. Central logging | PASS | `app/logging_config.py` | Keep | All |
| 7. Log levels | PASS | INFO for lifecycle, WARNING for failures in runtime logs | Keep | All |
| 8. Useful log context | PASS | Run, node and correlation IDs in log lines | Keep | All |
| 9. No sensitive data in logs | PASS | `test_run_redaction.py`, `test_secret_policy.py` | Same for new connectors | aboudka2003 |

### 5. Security practices (no LLM in the product; Exceptional: all 8)

| Check | Current status | Evidence | Required action | Owner |
|---|---|---|---|---|
| 1. No committed credentials | PASS | Repository secret check in CI; `.env.example` only | Keep | All |
| 2. Server-side authentication where required | NOT APPLICABLE | Single-user, loopback-only workstation app; no accounts by design (Wiki Security) | Revisit if Release 2 adds remote access | ham340i |
| 3. Server-side authorization | NOT APPLICABLE | Same reason; project folder containment enforced server-side | Same | ham340i |
| 4. Parameterized queries | PASS | SQLAlchemy ORM; SQL source runs read-only statements with validation | Same for a new connector | aboudka2003 |
| 5. No user input to shell/eval | PASS | No `eval`/`shell=True` on user input in `app/` | Keep | Reviewers |
| 6. Password hashing | NOT APPLICABLE | No passwords stored | n/a | n/a |
| 7. No hardcoded sensitive config | PASS | Environment variables and secret references | Keep | All |
| 8. Project-specific security requirements | PASS for Release 1 | Path containment, read-only SQL, decompression and size limits (`test_security_boundaries.py`); documented on Wiki Security | Add requirements for each Release 2 connector | adamoug |

### 6. Code review quality (Exceptional: at least 85% substantive reviews)

| Requirement | Current status | Exceptional requirement | Evidence | Required action | Owner |
|---|---|---|---|---|---|
| Substantive pre-merge review rate | FAIL for Exceptional (about 42%, Expected band) | 85% | Baseline audit | Every Release 2 feature/fix PR gets a named reviewer whose comment names what was checked; reviewer change requests answered before merge | All reviewers |

### 7. Traceability, change tracking and commit quality (Exceptional: 12 to 13 checks)

| Check | Current status | Evidence | Required action | Owner |
|---|---|---|---|---|
| 1. Feature labels | PASS | `feature:*` labels on all stories | Same for Release 2 | ham340i |
| 2. Story statement | PASS | 34 of 34 | Same | Story owners |
| 3. Points and hours | PASS | 34 of 34 | Same | Story owners |
| 4. Priority and risk | PASS | 34 of 34 | Same | Story owners |
| 5. Planning information | PASS | Milestones and feature labels | Same | ham340i |
| 6. Implementation evidence linked | PASS | Stories link PRs | Same | Story owners |
| 7. Tests and customer signoff | PARTIAL | Tests linked; signoff only as a document, no label on stories | Create `stakeholder:approved` label and apply it to accepted stories | ham340i |
| 8. Story-to-code PRs | PASS | Feature PRs reference issues | Same | All |
| 9. Test traceability | PASS | Feature PRs add tests | Same | All |
| 10. Commit messages | PARTIAL | Most are descriptive; some are vague ("more", "fix" in #114) | Descriptive commit messages in Release 2 | All |
| 11. Commits reference issues | PARTIAL | Many do; some do not | Reference the issue in each commit or PR | All |
| 12. Release tags and notes | FAIL | No tags or GitHub Releases | Tag `Release1` and publish its Release; tag `Release2` at the end | ham340i |
| 13. Personal contribution | PARTIAL | Records missing for 3 contributors, partial for others | Each student writes their own records | Each student |

### 8. Responsible use of AI-generated code (Exceptional: all applicable checks)

| Check | Current status | Evidence | Required action | Owner |
|---|---|---|---|---|
| 1. Tools listed | PARTIAL | `.github/AI_USAGE.md` lists Codex, Copilot reviewer and Claude Code; #72 names Copilot for test design, which is not listed as a coding tool | Add Copilot as a coding assistant | adamoug |
| 2. AI-assisted features named | PARTIAL | Most Release 1 features listed; #114 workspace storage missing | Add #114 and each Release 2 feature | Feature owners |
| 3. Source-file declarations ≥ 90% | FAIL | 84% (35 files missing) | Add declarations to the listed files | File authors |
| 4. PR declarations ≥ 90% | FAIL | 5% of merged feature/fix PRs state a level | Every Release 2 PR states a level; authors may amend their own Release 1 PRs | All |
| 5. Traceable AI-assisted features | PASS | Feature sections in AI_USAGE.md reference PRs | Same for Release 2 | Feature owners |
| 6. Verification evidence | PASS | Sections cite tests and reviews | Same | Feature owners |
| 7. Problems and corrections | PASS | Several sections record defects found in AI output | Same | Feature owners |

### 9. Quality controls, dependencies, containers and deployment (Exceptional: all applicable)

| Check | Current status | Evidence | Required action | Owner |
|---|---|---|---|---|
| 1. Linter config | PASS | Ruff, mypy strict, ESLint | Keep | All |
| 2. Formatter config | PASS | Ruff format, Prettier | Keep | All |
| 3. Tests in CI | PASS | Backend, frontend, browser jobs | Keep | menaboulus |
| 4. Static analysis in CI | PASS | Lint and type checks; SonarCloud | Keep | menaboulus |
| 5. Dependency/security scanning | PASS | Dependabot (Actions, pip, npm); SonarCloud | Merge or close Dependabot PR #107 | MarcElHaddad1 |
| 6. CI on PRs/pushes | PASS | `ci.yml` on pull_request and push | Keep | menaboulus |
| 7. Manifest | PASS | `requirements.txt`, `package.json` | Keep | All |
| 8. Locked dependencies | PASS | `requirements.lock` with hashes, `package-lock.json` | Keep | All |
| 9. No unused dependencies | PASS | Every listed runtime dependency is imported | Recheck when adding connectors | Feature owners |
| 10. No duplicate libraries | PASS | One HTTP client (axios), one state store (zustand) | Keep | Reviewers |
| 11. Third-party attribution | NOT VERIFIED | No copied third-party code found; no LICENSE or NOTICE file | Add LICENSE; confirm no copied code | Team |
| 12. Container config | PASS | `docker/api.Dockerfile`, frontend image | Keep | MarcElHaddad1 |
| 13. Container exclusions | PASS | `.dockerignore` | Keep | MarcElHaddad1 |
| 14. Multi-service config | PASS | `compose.yml` | Keep | MarcElHaddad1 |
| 15. No container secrets | PASS | Compose uses `.env`; no secrets in images | Keep | MarcElHaddad1 |
| 16. Deployment architecture | PASS | Wiki Deployment Plan and Infrastructure | Update for Release 2 | MarcElHaddad1 |
| 17. Deployment plan and release strategy | PASS | Wiki describes stakeholder, alpha, beta stages | Record actual Release 2 stage | MarcElHaddad1 |
| 18. Deployment record | FAIL | No GitHub Release records a deployed version | Publish Release 1 and Release 2 records with tag, environment, date, outcome | ham340i |

## Overall Capstone Grading Scheme (team tracks)

| Criterion | Current status | Exceptional requirement | Evidence | Required action | Owner |
|---|---|---|---|---|---|
| PA-1 Problem identification | PASS | Precise framing; risks mitigated by actual decisions | Wiki Home, Risks; spike #109 decision | Update risks for Release 2 | ham340i |
| PA-2 Modelling | PARTIAL | Models consistent and revised | Architecture, domain, SDK diagrams; Figma | Revise diagrams for #114 and Release 2 | ham340i |
| PA-3 Problem solving | PARTIAL | Thorough engineering notebook with rejected alternatives | Issue threads, spikes, ADRs | Keep an engineering journal per iteration | All |
| INV-1 Deployment plan | PARTIAL | Assumptions justified and revisited | Wiki deployment plan | Revisit after alpha testers | MarcElHaddad1 |
| INV-2 Experiments | PARTIAL | Baseline comparisons | Spikes #35, #109 with baselines | One measured experiment per Release 2 performance change | karimikhaeil |
| INV-3 Data collection | PARTIAL | Systematic instrumentation and user studies | Run telemetry and logs; no user study | Run an alpha session with logged tasks | karimikhaeil |
| INV-4 Feedback into plan | PARTIAL | Traceable plan changes from feedback | Release 1 signoff recorded | Link each Release 2 scope change to feedback | ham340i |
| DE-2 Idea selection | PARTIAL | Alternatives evaluated against criteria | ADRs, spike decisions | ADR for each major Release 2 design | Feature owners |
| DE-4 Validation and velocity | PARTIAL | On plan with explicit validation | Release 1 delivered all planned items late | Track planned vs actual per iteration | ham340i |
| UET-1/2 Tools | PASS | Integrated and justified | CI gates, Wiki tool justification | Keep | All |
| CO-3 Documentation | PARTIAL | Complete and usable by outsiders | README, Wiki, release notes | Release 2 notes, updated Wiki | MarcElHaddad1 |
| CO-4 Oral presentation | NOT VERIFIED | Clear, well-paced, strong visuals | Release 1 video is slides only | Release 2 video must include the live demo and code walkthrough | Team |
| PR-1 Legal and licensing | FAIL | Proactive legal/licensing work | No LICENSE | Choose a license; record data and IP decisions | Team |
| PR-2 Professional practice | PARTIAL | Stakeholder and instructor praise | Release 1 signoff | Release 2 stakeholder review | ham340i |
| IES-1/2 Society and sustainability | PARTIAL | Specific, evaluated mitigations | Societal risks in deck and Wiki | Evaluate one mitigation with evidence | Al-Yousef |
| EE-1 Accountability | PARTIAL | Ethics raised proactively | Legal and ethical Wiki page | Record ethical decisions in Release 2 | Team |
| EE-2 Equity | PARTIAL | Equity visible in design | Diversity statement names keyboard connections and French UI as Release 2 candidates | Deliver keyboard connection (in scope) | joedaswagger |
| EPM-2 Economics | PARTIAL | Real figures, critically examined | Economic page; rate not agreed | Agree rate; measure time saved in alpha | ham340i |
| EPM-3 Planning | PARTIAL | Detailed, realistic, risk-prioritized | This plan | Keep plan and actuals current | ham340i |

## Individual track (15%)

ITW-1 to ITW-4 come from peer evaluations and LLL from each student's reflection. Both are written by the students; this repository only provides [templates](../individual-contributions/TEMPLATE.md). Status: NOT VERIFIED.
