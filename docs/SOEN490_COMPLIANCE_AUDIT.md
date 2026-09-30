# SOEN 490 compliance audit

This is the compliance follow-up snapshot before the later Release 1 assignment brief. The [Release 1 setup report](release-1-setup-report.md) records the subsequent target stack, assigned product backlog, workload and dependency verification. Earlier missing-backlog/stack findings below are historical, not claims about the later plan.

## Current delivery status

[PR #3](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/3) contains this follow-up on `docs/2-soen490-compliance`, tracked by [issue #2](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/2). Implementation commit [9c41b3b](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/commit/9c41b3b69c6df6b0e5141cabf199f2ee367c9057) passed both PR workflows. The PR is open and blocked on the required independent review; changes are not claimed merged or accepted. New follow-up commits use the authenticated account’s GitHub noreply attribution; historical commits remain unchanged.

## Audit scope and baseline

Follow-up baseline: commit `609b617`. All 72 tracked files were inspected (142,320 bytes), including scripts, tests, workflow/configuration files and documentation. The working tree was clean. This audit uses the supplied SOEN 490 brief; it does not independently certify the official course rubric.

- Implemented: Python standard-library repository checks, Bash GitHub setup wrappers, JSON catalogs, Markdown documentation, GitHub issue/PR forms, Actions and Dependabot configuration, and a Wiki publisher.
- Product frontend/backend, frameworks, database, domain classes, API endpoints, authentication and application deployment: absent. All ETL architecture is proposed.
- Dependencies: no application manifest, lockfile, third-party Python packages or required environment variables. Python 3.11+ is the documented tooling minimum; the audited local interpreter is 3.13.0.
- Real commands: `python3 scripts/check_repository.py`, `python3 scripts/check_docs.py`, `python3 -m unittest discover -s scripts/tests -v`. Application install, development server, build, lint, typecheck and deployment commands do not exist.
- Live GitHub baseline: repository-admin API access; existing collaborator access; 13 generic/Dependabot labels; no milestones; no user-story issues; one open Dependabot PR; unprotected main; two passing Actions workflows on the baseline commit.
- Projects query failed with `INSUFFICIENT_SCOPES`: the current token has repository scope but lacks Projects scope. Wiki is enabled, but its Git repository still returned not-found over SSH.
- Existing foundation has many useful templates. Missing or weak areas: detailed onboarding, consent/EULA applicability, personal contribution records, explicit traceability, current GitHub evidence, stronger story/PR fields, and evidence-based risks.

## Privacy review

No obvious credentials, student IDs, private contact details or manufacturing datasets were found in tracked file contents. The email-shaped match in `scripts/publish_wiki.py` is the expected SSH remote, not a personal email. The existing commit metadata uses a non-noreply contributor email; confirm intended public attribution and use GitHub noreply for future commits if desired. No history has been rewritten and no email values are repeated here. Pattern checks do not guarantee that all sensitive data is absent.

## Requirement coverage and actions

Status applies to the stated requirement. Complete policies/templates do not establish product completion. This follow-up preserves existing filenames/hierarchy instead of duplicating the requested flat-layout examples.

| Requirement | Current status | What was found | What needs to change | Action taken | Manual action required | Evidence/link |
|---|---|---|---|---|---|---|
| Single repository | ✅ Complete | One source repository; Wiki sources also tracked here | Keep canonical docs together | Preserved hierarchy; Wiki is navigation only | None | [README.md](README.md) |
| Correct repository organization | ✅ Complete | Useful existing docs and scripts | Add missing entry points without duplicate topic documents | Added root contributing/security and targeted guides | None | [../README.md](../README.md) |
| README | ✅ Complete | Status/onboarding present; CI/deployment detail weak | Expose actual capability and evidence | Added developer, CI, deployment and documentation navigation | None | [../README.md](../README.md) |
| Project summary <= one paragraph | ✅ Complete | One proposed-product paragraph | Give it explicit heading | Added Project Summary heading | Validate product scope | [../README.md](../README.md) |
| Developer getting started guide | ⚠️ Partial | No detailed guide; no application | Document real commands and unavailable components | Created complete command/applicability guide | Implement first product slice before it can run | [getting-started.md](getting-started.md) |
| Wiki/documentation TOC | ⚠️ Partial | Canonical index present; Wiki enabled but Git unavailable | Improve navigation; publish only when reachable | Index and prepared Wiki pages linked | Save first Wiki Home and run publisher; verify access | [../scripts/github-setup/wiki-setup.md](../scripts/github-setup/wiki-setup.md) |
| GitHub Project | 👤 Manual action required | API lacks Projects scope | Create/reuse and configure actual board | Recorded scope error and exact UI/CLI steps | Owner configures board or grants project scope | [GITHUB_PROJECT_SETUP.md](GITHUB_PROJECT_SETUP.md) |
| Project shared with moar82 | 👤 Manual action required | Not inspectable with current scope | Verify invitation and item visibility | Explicit access instructions | Share with moar82 and verify access | [planning/github-project-setup.md](planning/github-project-setup.md) |
| GitHub milestones = iterations | ✅ Complete | No milestones | Create all 13 without duplicates | Created exact dates/names; verified live reconciliation | Confirm course changes/submission time if any | [milestones.md](milestones.md) |
| Two iterations planned ahead | ⚠️ Partial | Policy exists; no approved product backlog | Prepare real near-term scope | Documented planning and bounded candidate discussions | Team estimates/assigns upcoming product work | [milestones.md](milestones.md) |
| Feature labels | ✅ Complete | Only generic labels; prior catalog speculative | Separate actual infrastructure from proposed product areas | Created infrastructure feature and management labels; preserved existing labels | Approve product feature scope before adding labels | [github-labels.md](github-labels.md) |
| User-story issues | ❌ Missing | Only Dependabot PR at baseline; no product stories | Create real stakeholder-backed stories | Created actual technical setup issue #2, not fake product stories | Team supplies and assigns product stories | [traceability.md](traceability.md) |
| Full user-story format | ✅ Complete | Existing form combines some test requirements | Make unit/integration and completion requirements explicit | Improved existing user_story.yml; no duplicate chooser form | None for template | [../.github/ISSUE_TEMPLATE/user_story.yml](../.github/ISSUE_TEMPLATE/user_story.yml) |
| Story points | ⚠️ Partial | Required prompts exist; no estimated product stories | Capture real values and issue metadata | Strengthened story checklist; infrastructure task has a real milestone | Team estimates/prioritizes product stories; do not invent values | [../.github/ISSUE_TEMPLATE/user_story.yml](../.github/ISSUE_TEMPLATE/user_story.yml) |
| Priority/value | ⚠️ Partial | Required prompts exist; no estimated product stories | Capture real values and issue metadata | Strengthened story checklist; infrastructure task has a real milestone | Team estimates/prioritizes product stories; do not invent values | [../.github/ISSUE_TEMPLATE/user_story.yml](../.github/ISSUE_TEMPLATE/user_story.yml) |
| Risk | ⚠️ Partial | Required prompts exist; no estimated product stories | Capture real values and issue metadata | Strengthened story checklist; infrastructure task has a real milestone | Team estimates/prioritizes product stories; do not invent values | [../.github/ISSUE_TEMPLATE/user_story.yml](../.github/ISSUE_TEMPLATE/user_story.yml) |
| Feature assignment | ⚠️ Partial | Required prompts exist; no estimated product stories | Capture real values and issue metadata | Strengthened story checklist; infrastructure task has a real milestone | Team estimates/prioritizes product stories; do not invent values | [../.github/ISSUE_TEMPLATE/user_story.yml](../.github/ISSUE_TEMPLATE/user_story.yml) |
| Milestone assignment | ⚠️ Partial | Required prompts exist; no estimated product stories | Capture real values and issue metadata | Strengthened story checklist; infrastructure task has a real milestone | Team estimates/prioritizes product stories; do not invent values | [../.github/ISSUE_TEMPLATE/user_story.yml](../.github/ISSUE_TEMPLATE/user_story.yml) |
| Ideal-time estimate | ⚠️ Partial | Required prompts exist; no estimated product stories | Capture real values and issue metadata | Strengthened story checklist; infrastructure task has a real milestone | Team estimates/prioritizes product stories; do not invent values | [../.github/ISSUE_TEMPLATE/user_story.yml](../.github/ISSUE_TEMPLATE/user_story.yml) |
| Engineering evidence linked | ⚠️ Partial | Earlier setup lacks issue chain | Demonstrate actual follow-up chain | Issue #2, issue branch, audit and PR links | Add actual product design/code and personal evidence | [traceability.md](traceability.md) |
| Tests linked | ⚠️ Partial | Real tool tests; no product tests | Link commands/results to issues and PR | 12 tool tests and validation evidence recorded | Implement product tests with product work | [testing/testing-plan.md](testing/testing-plan.md) |
| Stakeholder signoff field | ✅ Complete | Field/template already present | Keep pending approval explicit | Retained required status and strengthened PR prompt | Obtain actual required signoffs later | [stakeholder/signoff-template.md](stakeholder/signoff-template.md) |
| Proper commits | ⚠️ Partial | Real setup commits; independent review pending | Follow conventions prospectively | Issue-linked branch/commits and truthful AI disclosure | Teammate reviews PR; no history rewrite | [../.github/CONTRIBUTING.md](../.github/CONTRIBUTING.md) |
| Issue references in commits | ⚠️ Partial | Historical setup commits lack references | Reference actual issue going forward | Follow-up tracked under #2; historical gap documented | Preserve accurate future references | [traceability.md](traceability.md) |
| AI acknowledgement | ✅ Complete | Policy exists; documentation entry point missing | Cover own design/verification and generated work | Added guide and follow-up disclosure; strengthened PR fields | Humans record real contribution/review | [ai-usage.md](ai-usage.md) |
| PR template | ✅ Complete | Design/testing present; iteration/feature absent | Explicit milestone, feature, personal work and signoff | Expanded existing template | None for template | [../.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md) |
| Meeting minutes | ⚠️ Partial | Template only; no meetings recorded | Require actual records and note-taker rotation | Documented rotation; preserved course fields | Record real attendance, decisions and actions | [meetings/README.md](meetings/README.md) |
| Risks | ⚠️ Partial | Hypothesis register only | Prioritize observed blockers and early mitigation | Added five evidence-based risks and linked actions | Assign owners and validate remaining hypotheses | [planning/risks.md](planning/risks.md) |
| User consent/EULA | 👤 Manual action required | No applicability decision or draft | Prepare unapproved conditional draft | Added data/purpose/storage/third-party/responsibility/termination placeholders | Authorized applicability and legal/stakeholder review | [user-consent-eula.md](user-consent-eula.md) |
| Legal/ethical analysis | ⚠️ Partial | Checklist exists; consent/services incomplete | Tie concerns to observed services and future scope | Added GitHub/SonarCloud observation and consent link | Confirm agreements, data rights and service permissions | [legal/legal-and-ethical-issues.md](legal/legal-and-ethical-issues.md) |
| License/IP requirement | 👤 Manual action required | No approved license or IP agreement | Preserve team decision authority | Kept MIT as consideration only; no LICENSE invented | Approve ownership, agreement and license | [legal/README.md](legal/README.md) |
| Economic impact | ⚠️ Partial | Measurement method; no business measurements | Keep estimates honest | Retained baseline/comparison method | Collect actual workflow time/cost evidence | [planning/economic-impact.md](planning/economic-impact.md) |
| Budget | ⚠️ Partial | Empty resource row; no verified expenses | Use observed resources without prices | Listed GitHub, local equipment and observed SonarCloud integration | Confirm plan/cost/credit and restricted receipts | [planning/budget.md](planning/budget.md) |
| Personas | ⚠️ Partial | Five brief-based hypotheses | Link relevant features/accessibility questions | Added feature and accessibility mapping | Validate with stakeholder; do not infer demographics | [planning/personas.md](planning/personas.md) |
| Diversity statement | ✅ Complete | Keyboard/visual commitments present | Address device/language/bias constraints honestly | Added validation questions; no usability achievement claimed | Validate/test actual interfaces later | [planning/diversity.md](planning/diversity.md) |
| Architecture | ✅ Complete | Proposed ETL diagrams and open decisions | Add actual tooling boundaries | Documented modules and implemented tooling diagram | Select product architecture through reviewed ADRs | [architecture/README.md](architecture/README.md) |
| Class/domain diagrams | ⚠️ Partial | No product classes or domain model exist | Avoid fake diagrams | Marked product class/domain diagram not yet applicable | Create when real domain design exists | [architecture/README.md](architecture/README.md) |
| Infrastructure/tools | ✅ Complete | Table lacked rationale/observed service state | Show what/why/where/version | Updated real tools and unknown product stack | Owner verifies third-party configuration | [planning/infrastructure-and-tools.md](planning/infrastructure-and-tools.md) |
| Naming conventions | ✅ Complete | Branches/docs covered; Python naming implicit | Document actual ecosystem conventions | Added files/classes/functions/variables/constants/tests conventions | Choose product-specific conventions later | [planning/naming-conventions.md](planning/naming-conventions.md) |
| Testing plan | ✅ Complete | Layered strategy already present | Keep ownership and merge/release gates visible | Retained real plan; linked current audit | Add executable product tests with implementation | [testing/testing-plan.md](testing/testing-plan.md) |
| GitHub Actions CI | ✅ Complete | Two workflows pass on baseline | Preserve valid checks and add needed regressions | Existing CI retained; tool suite expanded; checks required on main | Application gates await real stack | [../.github/workflows/ci.yml](../.github/workflows/ci.yml) |
| Code review process | ✅ Complete | Policy only; main unprotected | Enforce independent approval and checks | Configured one reviewer, up-to-date checks, conversation resolution, admins included | Teammate must approve this PR before merge | [../scripts/github-setup/branch-protection.md](../scripts/github-setup/branch-protection.md) |
| Security plan | ✅ Complete | Plan/ignore rules exist; no root reporting policy | Add reporting and actual control status | Added SECURITY.md; verified live controls; limited scan passed | Confirm private contact and future product threats | [../SECURITY.md](../SECURITY.md) |
| Performance plan | ✅ Complete | Metrics/method already documented | Distinguish likely bottlenecks from measurements | Added proposed bottlenecks and applicability boundaries | Measure product workloads when implemented | [performance/performance-plan.md](performance/performance-plan.md) |
| Deployment plan | ✅ Complete | Planned environments/rollback; no operational record | Add monitoring and course stage interpretation | Added deployment record and synthetic-only trusted-test stage | Implement/test packaging and recovery before release | [deployment/deployment-plan.md](deployment/deployment-plan.md) |
| Deployment diagram | ✅ Complete | Proposed local topology exists | Keep status explicit | Retained linked Mermaid diagram | Update after implementation | [architecture/deployment-architecture.md](architecture/deployment-architecture.md) |
| Independent learning | ⚠️ Partial | Template; no real records | Require individual issue/PR/commit evidence | Clarified sources and personal design effects | Contributors document real learning | [planning/independent-learning.md](planning/independent-learning.md) |
| Iteration notes | ⚠️ Partial | Template; no completed iteration | Add missing summary/early-work/risk/learning prompts | Expanded existing iteration template | Complete from actual work | [iterations/ITERATION_TEMPLATE.md](iterations/ITERATION_TEMPLATE.md) |
| Release notes | ⚠️ Partial | Template; no actual release | Capture slipped/early work and engineering choices | Expanded existing release template | Complete and publish after actual release | [releases/RELEASE_TEMPLATE.md](releases/RELEASE_TEMPLATE.md) |
| <=4 sentence iteration summary | ✅ Complete | Iteration template lacked summary cap | Require concise actual achievements | Added capped Overall Summary prompt | Write when work exists | [iterations/ITERATION_TEMPLATE.md](iterations/ITERATION_TEMPLATE.md) |
| Velocity | ⚠️ Partial | Template only | Use actual planned/completed points | Explicit fields preserved/added | Record real estimates and outcomes | [releases/RELEASE_TEMPLATE.md](releases/RELEASE_TEMPLATE.md) |
| Contractor estimate | ⚠️ Partial | Generic prompt; no values | Separate hours/rate/value/assumptions | Added fields without fabricated amounts | Provide supported rate and scope assumptions | [releases/RELEASE_TEMPLATE.md](releases/RELEASE_TEMPLATE.md) |
| Retrospective | ⚠️ Partial | Templates only | Capture actual outcomes/improvements | Release and iteration subsections aligned | Record real retrospective and owners | [releases/RELEASE_TEMPLATE.md](releases/RELEASE_TEMPLATE.md) |
| Individual contribution breakdown | ⚠️ Partial | Team tables; no personal record system | Require per-person evidence every iteration/release | Created policy/template and links | Every student writes/verifies own actual record | [individual-contributions/README.md](individual-contributions/README.md) |
| Release demos | ❌ Missing | No videos/releases | Keep authoritative registry | Expanded dates/release/signoff columns and README table | Record real demos and verify access | [demos/README.md](demos/README.md) |
| Iteration tags | ⚠️ Partial | Convention only; no completed iteration | Do not tag unfinished work | Retained exact IterationN/ReleaseN conventions | Tag reviewed completion states only | [iterations/README.md](iterations/README.md) |
| Privacy audit | ⚠️ Partial | File scan clean; non-noreply commit metadata exists | Report paths/scope without copying values | Reviewed files/metadata; no secret printed; no history rewrite | Confirm intended public identity and data policy | [SOEN490_COMPLIANCE_AUDIT.md#privacy-review](SOEN490_COMPLIANCE_AUDIT.md#privacy-review) |
| Traceability | ⚠️ Partial | Policy but weak real chain | Use real issue rather than fabricated examples | Created guide and issue-linked review workflow | Maintain chain for every product story/contributor | [traceability.md](traceability.md) |
| Dependency automation | ✅ Complete | Dependabot active; actual PR #1 exists | Avoid unrelated unreviewed upgrades | Preserved Actions updater and existing PR | Team reviews dependency PR independently | [../.github/dependabot.yml](../.github/dependabot.yml) |
| No fabricated work or evidence | ✅ Complete | Templates explicitly pending | Preserve honest status throughout | No product code, tags, approvals, meetings or metrics invented | Record actual evidence as work occurs | [../SOEN490_HUMAN_ACTIONS.md](../SOEN490_HUMAN_ACTIONS.md) |

## GitHub actions performed and verified

- Created 17 labels: one implemented feature (`feature:infrastructure`), five types, three risks, four priorities, three stakeholder states and `ai-assisted`. Existing generic labels were preserved; speculative product feature labels were not created.
- Created all 13 [iteration milestones](milestones.md), with exact course calendar dates and the original compatible titles. GitHub normalizes timestamp times; the helper now compares dates and has regression coverage for this behavior.
- Created [technical issue #2](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/2) for the actual compliance follow-up, assigned to Iteration 1 without inventing story points or individual ownership.
- Protected main: one approving review, stale-review dismissal, resolved conversations, up-to-date `Repository checks` and `Documentation checks` from GitHub Actions, administrator enforcement, no force pushes/deletion. Existing collaborators provide a review path.
- Both baseline workflows passed: [CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/36611149320) and [Documentation](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/36611149226).
- Projects: API rejected the request for missing Projects scope. No board or invitation is claimed. Wiki: enabled but its Git repository is not reachable; no Wiki publication is claimed.
- Existing Dependabot PR #1 was preserved. A neutral SonarCloud check was observed; it is not a passed security audit or proof of product analysis.
- GitHub secret scanning and push protection were already enabled and preserved. Private vulnerability reporting was enabled and verified through the API; [SECURITY.md](../SECURITY.md) directs reports to that private route.

## Verification results

| Operation | Result | Evidence / limitation |
|---|---|---|
| Dependency installation | NOT AVAILABLE | No application/dependency manifest; standard-library tooling needs no install |
| Product lint / formatter / typecheck | NOT AVAILABLE | No configured product tools; syntax/whitespace checks below have narrower scope |
| Repository checks | PASS | `python3 scripts/check_repository.py`; syntax, configuration, whitespace and limited secret patterns |
| Documentation checks | PASS | `python3 scripts/check_docs.py`; includes maintained absolute Wiki/source links |
| Tool tests | PASS | `python3 -m unittest discover -s scripts/tests -v`; 12 tests, including real date-normalization regression |
| Patch whitespace | PASS | `git diff --check` |
| Live setup reconciliation | PASS | Read-only comparison of 17 desired labels and 13 milestones; no duplicate writes |
| Main protection verification | PASS | Read-back API confirmed required reviews/checks and restrictions |
| Product build / development / deployment | NOT AVAILABLE | No runnable application exists |
| Follow-up PR CI | PASS | Implementation commit `9c41b3b`: [CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/36613576426), [Documentation](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/runs/36613576444); latest results remain visible in [PR #3](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/3) |
| Independent review | MANUAL ACTION REQUIRED | An authorized teammate must review; no approval fabricated |
| Stakeholder acceptance / product benchmarks | NOT AVAILABLE | No demonstrated product release or measurements |

## Remaining decisions and highest risks

See [human actions](../SOEN490_HUMAN_ACTIONS.md) for exact next steps and [five observed risks](planning/risks.md#observed-priorities-before-the-next-iteration) for evidence and mitigation. The team must provide approved product scope, a stack decision, stakeholder/data contracts, per-person work allocation, actual estimates, legal/license decisions, costs and real review/demo evidence. These cannot be supplied honestly by repository scaffolding.

## Files created and modified

Compared with baseline `609b617`; application code was not present or rewritten.

| Change | File |
|---|---|
| Modified | [.github/AI_USAGE.md](../.github/AI_USAGE.md) |
| Modified | [.github/CONTRIBUTING.md](../.github/CONTRIBUTING.md) |
| Modified | [.github/ISSUE_TEMPLATE/user_story.yml](../.github/ISSUE_TEMPLATE/user_story.yml) |
| Modified | [.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md) |
| Created | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| Modified | [README.md](../README.md) |
| Created | [SECURITY.md](../SECURITY.md) |
| Modified | [SOEN490_HUMAN_ACTIONS.md](../SOEN490_HUMAN_ACTIONS.md) |
| Created | [docs/GITHUB_PROJECT_SETUP.md](GITHUB_PROJECT_SETUP.md) |
| Modified | [docs/README.md](README.md) |
| Created | [docs/SOEN490_COMPLIANCE_AUDIT.md](SOEN490_COMPLIANCE_AUDIT.md) |
| Modified | [docs/SOEN490_REQUIREMENTS_MATRIX.md](SOEN490_REQUIREMENTS_MATRIX.md) |
| Created | [docs/ai-usage.md](ai-usage.md) |
| Modified | [docs/architecture/README.md](architecture/README.md) |
| Modified | [docs/demos/README.md](demos/README.md) |
| Modified | [docs/deployment/deployment-plan.md](deployment/deployment-plan.md) |
| Created | [docs/getting-started.md](getting-started.md) |
| Created | [docs/github-labels.md](github-labels.md) |
| Created | [docs/individual-contributions/README.md](individual-contributions/README.md) |
| Created | [docs/individual-contributions/TEMPLATE.md](individual-contributions/TEMPLATE.md) |
| Modified | [docs/iterations/ITERATION_TEMPLATE.md](iterations/ITERATION_TEMPLATE.md) |
| Modified | [docs/iterations/README.md](iterations/README.md) |
| Modified | [docs/legal/legal-and-ethical-issues.md](legal/legal-and-ethical-issues.md) |
| Modified | [docs/meetings/README.md](meetings/README.md) |
| Created | [docs/milestones.md](milestones.md) |
| Modified | [docs/performance/performance-plan.md](performance/performance-plan.md) |
| Modified | [docs/planning/budget.md](planning/budget.md) |
| Modified | [docs/planning/diversity.md](planning/diversity.md) |
| Modified | [docs/planning/github-project-setup.md](planning/github-project-setup.md) |
| Modified | [docs/planning/independent-learning.md](planning/independent-learning.md) |
| Modified | [docs/planning/infrastructure-and-tools.md](planning/infrastructure-and-tools.md) |
| Modified | [docs/planning/naming-conventions.md](planning/naming-conventions.md) |
| Modified | [docs/planning/personas.md](planning/personas.md) |
| Modified | [docs/planning/risks.md](planning/risks.md) |
| Modified | [docs/releases/RELEASE_TEMPLATE.md](releases/RELEASE_TEMPLATE.md) |
| Modified | [docs/security/security-plan.md](security/security-plan.md) |
| Modified | [docs/testing/repository-validation.md](testing/repository-validation.md) |
| Created | [docs/traceability.md](traceability.md) |
| Created | [docs/user-consent-eula.md](user-consent-eula.md) |
| Modified | [docs/wiki/Getting-Started.md](wiki/Getting-Started.md) |
| Modified | [docs/wiki/SOEN-490-Evaluation.md](wiki/SOEN-490-Evaluation.md) |
| Modified | [scripts/check_docs.py](../scripts/check_docs.py) |
| Modified | [scripts/github-setup/README.md](../scripts/github-setup/README.md) |
| Modified | [scripts/github-setup/branch-protection.md](../scripts/github-setup/branch-protection.md) |
| Modified | [scripts/github-setup/labels.json](../scripts/github-setup/labels.json) |
| Modified | [scripts/github-setup/setup.py](../scripts/github-setup/setup.py) |
| Modified | [scripts/tests/test_repository_tools.py](../scripts/tests/test_repository_tools.py) |
