# SOEN 490 requirements matrix

Scope: the user-supplied course/project brief, not an independently verified official rubric. **COMPLETE** means the stated repository artifact/policy is supplied; it never asserts that planned product work, remote enforcement or human evidence exists. **PARTIAL** means scaffolding exists but execution/evidence remains. **REQUIRES HUMAN ACTION** means authorized access, a decision or real human evidence is needed. **NOT YET APPLICABLE** means the required application component/stack does not exist yet.

| SOEN 490 Requirement | Implementation | Location | Status |
|---|---|---|---|
| Repository audit before edits | Initial tree, history, stack absence and CLI limitation documented | [../SOEN490_REPO_AUDIT.md](../SOEN490_REPO_AUDIT.md) | COMPLETE |
| Preserve existing code / inspect stack | README-only baseline; no application moved or rewritten | [../SOEN490_REPO_AUDIT.md](../SOEN490_REPO_AUDIT.md) | COMPLETE |
| Clear project README and evaluation navigation | Required sections and evidence links | [../README.md](../README.md) | COMPLETE |
| New developer application install/run guide | Repository checks run; application and commands do not exist | [../README.md](../README.md) | PARTIAL |
| Implemented vs planned architecture | Explicit status, boundaries, local-first constraints and open decisions | [architecture/system-architecture.md](architecture/system-architecture.md) | COMPLETE |
| Data sources, pipeline definition, ETL and governed consumers | Proposed data flow; no implementation claimed | [architecture/data-flow.md](architecture/data-flow.md) | PARTIAL |
| Configuration, secrets, persistence, versioning, APIs, extensions | Open decisions and proposed boundaries documented | [architecture/system-architecture.md](architecture/system-architecture.md) | PARTIAL |
| Architecture decision records | Process and ADR template; accepted decisions still needed | [architecture/decisions/README.md](architecture/decisions/README.md) | PARTIAL |
| Feature labels | Catalog and idempotent helper; live labels unverified | [../scripts/github-setup/labels.json](../scripts/github-setup/labels.json) | PARTIAL |
| Type, priority, risk and stakeholder labels | Catalog provided; live setup pending | [../scripts/github-setup/README.md](../scripts/github-setup/README.md) | PARTIAL |
| GitHub Project required | Exact setup instructions; live board/URL pending | [planning/github-project-setup.md](planning/github-project-setup.md) | REQUIRES HUMAN ACTION |
| Project views: Backlog, Current Iteration, Board, Roadmap, By Feature, By Assignee, Releases | Configuration instructions | [planning/github-project-setup.md](planning/github-project-setup.md) | REQUIRES HUMAN ACTION |
| Project fields: Status, Priority, Risk, Points, Hours, Iteration, Feature, Stakeholder Status | Types, options and built-in field choices documented | [planning/github-project-setup.md](planning/github-project-setup.md) | REQUIRES HUMAN ACTION |
| Share Project with moar82 | Access instructions; invitation/visibility not verified | [planning/github-project-setup.md](planning/github-project-setup.md) | REQUIRES HUMAN ACTION |
| 13 exact milestones and dates | Catalog and helper; remote milestones pending | [../scripts/github-setup/milestones.json](../scripts/github-setup/milestones.json) | PARTIAL |
| Final presentation, peer evaluations, stakeholder feedback date | April 13, 2027 recorded; deliverables pending | [iterations/README.md](iterations/README.md) | PARTIAL |
| Plan approximately two iterations ahead | Policy; actual scope needs team planning | [../.github/CONTRIBUTING.md](../.github/CONTRIBUTING.md) | PARTIAL |
| User stories with short name, persona/value and acceptance criteria | Required form prompts | [../.github/ISSUE_TEMPLATE/user_story.yml](../.github/ISSUE_TEMPLATE/user_story.yml) | COMPLETE |
| Story points, priority/value, risk, feature, iteration, ideal hours | Required form prompts; issue labels/milestone set after creation | [../.github/ISSUE_TEMPLATE/user_story.yml](../.github/ISSUE_TEMPLATE/user_story.yml) | COMPLETE |
| Story commits, architecture diagrams, discussion, unit tests and customer signoff | Required prompts allow honest Pending; evidence added during work | [../.github/ISSUE_TEMPLATE/user_story.yml](../.github/ISSUE_TEMPLATE/user_story.yml) | COMPLETE |
| Engineering task template | Problem/objective, approach, alternatives, risks, tests, estimates, links and AI | [../.github/ISSUE_TEMPLATE/engineering_task.yml](../.github/ISSUE_TEMPLATE/engineering_task.yml) | COMPLETE |
| Spike and failed experiment evidence | Question, hypothesis, code, failure, learning, decision and time prompts | [../.github/ISSUE_TEMPLATE/spike.yml](../.github/ISSUE_TEMPLATE/spike.yml) | COMPLETE |
| Bug report template | Reproduction, environment, severity/risk and regression prompts | [../.github/ISSUE_TEMPLATE/bug_report.yml](../.github/ISSUE_TEMPLATE/bug_report.yml) | COMPLETE |
| PR template | Design, alternatives, impacts, evidence, review checklist and AI | [../.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md) | COMPLETE |
| Branch strategy and commit standard | Issue references, attribution, examples and branch names | [../.github/CONTRIBUTING.md](../.github/CONTRIBUTING.md) | COMPLETE |
| Protected main and required review/checks | Exact safe setup instructions; enforcement not verified | [../scripts/github-setup/branch-protection.md](../scripts/github-setup/branch-protection.md) | REQUIRES HUMAN ACTION |
| Contribution workflow and every-student engineering work each iteration | Workflow and contribution tables; actual work pending | [../.github/CONTRIBUTING.md](../.github/CONTRIBUTING.md) | PARTIAL |
| Requirement-to-release traceability | Templates/policy present; actual linked issues and PRs pending | [planning/naming-conventions.md](planning/naming-conventions.md) | PARTIAL |
| GitHub Actions on PR and main push | Repository CI authored and locally checked; remote run pending | [../.github/workflows/ci.yml](../.github/workflows/ci.yml) | PARTIAL |
| Documentation CI | Local links, heading anchors and whitespace checks | [../.github/workflows/documentation-check.yml](../.github/workflows/documentation-check.yml) | COMPLETE |
| Application install/lint/format/type/unit/integration/build gates | No application stack; required in first implementation PR | [testing/testing-plan.md](testing/testing-plan.md) | NOT YET APPLICABLE |
| Dependency locks and caching | No third-party tooling/application dependencies to install/cache | [testing/testing-plan.md](testing/testing-plan.md) | NOT YET APPLICABLE |
| Security/dependency quality gates | Limited secret check and pinned action; broader product checks pending | [security/security-plan.md](security/security-plan.md) | PARTIAL |
| Dependabot for actual ecosystem | GitHub Actions only; product ecosystems not invented | [../.github/dependabot.yml](../.github/dependabot.yml) | COMPLETE |
| Testing strategy, ownership, review and Definition of Done | Unit, integration, E2E, ETL, validation, regression, performance, security, manual and acceptance | [testing/testing-plan.md](testing/testing-plan.md) | COMPLETE |
| Real validation evidence | Local commands/results and limits; no product or remote CI claims | [testing/repository-validation.md](testing/repository-validation.md) | COMPLETE |
| Meeting minutes matching course fields | Template ready; real meetings pending | [meetings/TEMPLATE.md](meetings/TEMPLATE.md) | PARTIAL |
| Project-killing risk register | Specific hypotheses and all requested fields; validation/owners pending | [planning/risks.md](planning/risks.md) | PARTIAL |
| Legal/ethical IP, license, agreements, NDA and data ownership | Questions and restricted-document references; approvals pending | [legal/README.md](legal/README.md) | REQUIRES HUMAN ACTION |
| Privacy, security, ethics, environment, accessibility and job disruption | Review checklist and planned controls | [legal/legal-and-ethical-issues.md](legal/legal-and-ethical-issues.md) | PARTIAL |
| License preservation and approval | No license existed; none selected without authorization | [legal/README.md](legal/README.md) | REQUIRES HUMAN ACTION |
| Economic impact | Measurement method; no invented savings | [planning/economic-impact.md](planning/economic-impact.md) | COMPLETE |
| Budget with estimates, credits, actuals and receipts | Table ready; real values require confirmation | [planning/budget.md](planning/budget.md) | PARTIAL |
| Five starter personas | Explicit stakeholder-validation hypotheses | [planning/personas.md](planning/personas.md) | PARTIAL |
| Diversity and accessibility statement | Concrete keyboard, visual and error-message commitments | [planning/diversity.md](planning/diversity.md) | COMPLETE |
| Infrastructure and tools | Current tooling distinguished from pending product stack | [planning/infrastructure-and-tools.md](planning/infrastructure-and-tools.md) | COMPLETE |
| Naming conventions | Branches, commits, labels, records and tags | [planning/naming-conventions.md](planning/naming-conventions.md) | COMPLETE |
| Independent learning evidence | Template ready; individual records pending | [planning/independent-learning.md](planning/independent-learning.md) | PARTIAL |
| Security plan and secure configuration | Threats, credential boundary, least privilege, validation, redaction and response | [security/security-plan.md](security/security-plan.md) | COMPLETE |
| Ignore credentials and local/generated manufacturing data | Rules added; manual review still required for arbitrary paths | [../.gitignore](../.gitignore) | COMPLETE |
| Environment example | No application variables exist; defer until defined | [../README.md](../README.md) | NOT YET APPLICABLE |
| Obvious secret review without disclosure | Baseline reviewed; limited scanner reports paths only | [../SOEN490_REPO_AUDIT.md](../SOEN490_REPO_AUDIT.md) | COMPLETE |
| Performance metrics and measurements | Metrics/method ready; no benchmarks claimed | [performance/performance-plan.md](performance/performance-plan.md) | PARTIAL |
| Deployment environments, diagram and staged rollout | Planned development/test/stakeholder/production progression | [deployment/deployment-plan.md](deployment/deployment-plan.md) | COMPLETE |
| Iteration evidence and individual contributions | Full template including velocity, contractor estimate and failed approaches | [iterations/ITERATION_TEMPLATE.md](iterations/ITERATION_TEMPLATE.md) | PARTIAL |
| Release evidence and human contribution summaries | Template/process including generated-notes starting point | [releases/RELEASE_TEMPLATE.md](releases/RELEASE_TEMPLATE.md) | PARTIAL |
| IterationN and ReleaseN tags only at completion | Convention and process; no premature tags created | [iterations/README.md](iterations/README.md) | COMPLETE |
| Release 1/2/3 demo links | Registry ready; videos absent | [demos/README.md](demos/README.md) | REQUIRES HUMAN ACTION |
| Stakeholder signoff | Template ready; real approvals absent | [stakeholder/signoff-template.md](stakeholder/signoff-template.md) | REQUIRES HUMAN ACTION |
| Project-wide Definition of Done | All required engineering, review, testing, AI and merge gates | [planning/definition-of-done.md](planning/definition-of-done.md) | COMPLETE |
| AI policy, issue/PR disclosure and commit footer | Policy and this foundation disclosed; human review pending | [../.github/AI_USAGE.md](../.github/AI_USAGE.md) | COMPLETE |
| Privacy and no fabricated evidence | GitHub identities and explicit Pending/TODO records throughout | [../.github/CONTRIBUTING.md](../.github/CONTRIBUTING.md) | COMPLETE |
| Idempotent GitHub setup fallback | Create-only scripts, preview, pagination and drift preservation tests | [../scripts/github-setup/README.md](../scripts/github-setup/README.md) | COMPLETE |
| Documentation index and professor review path | README navigation and centralized index | [README.md](README.md) | COMPLETE |
| Human action checklist | Only real decisions, permissions and evidence left to humans | [../SOEN490_HUMAN_ACTIONS.md](../SOEN490_HUMAN_ACTIONS.md) | COMPLETE |

The matrix must be updated each iteration. A complete template cannot substitute for substantial engineering implementation, per-student contributions, a live shared Project or stakeholder acceptance.
