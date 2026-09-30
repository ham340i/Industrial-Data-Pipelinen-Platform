# Project setup summary

Project: **Industrial Data Pipeline Engineering Platform**
Industry partner: **Pratt & Whitney Canada**
Status recorded: **September 30, 2026**

## Work completed in this setup session

### Repository and engineering workflow

- Prepared repository documentation, onboarding instructions, architecture plans, contribution guidance, issue/PR templates, and the Definition of Done.
- Documented testing, security, deployment, stakeholder reviews, release evidence, individual contributions, and AI disclosure requirements.
- Configured the course milestones and GitHub labels. Main-branch protection requires an independent approval, passing repository/documentation checks, an up-to-date branch, and resolved review conversations.
- Enabled private vulnerability reporting; preserved existing secret scanning and push protection.

### Release 1 planning and assignments

- Created **34 engineering issues (#4–#37)** and **one unassigned release acceptance tracker (#38)**.
- Distributed engineering ownership across eight students, with a different planned student reviewer for each item.
- Added acceptance criteria, testing requirements, initial estimates, priorities, risks, feature labels, and **98 native dependency links**.
- Added `iteration:1` through `iteration:4` tags and verified that all 35 issues match their iteration milestones.
- Kept **moar82** as the academic reviewer, with no engineering assignments or routine PR review duties.

| Iteration | Due date | Focus | Issues |
|---|---|---|---|
| 1 | October 6, 2026 | Foundation & Architecture | #4–#13 |
| 2 | October 20, 2026 | Visual Pipeline Builder | #14–#21 |
| 3 | November 3, 2026 | Execution Engine & Data Processing | #22–#29 |
| 4 / Release 1 | November 17, 2026 | Integration, Quality & Release | #30–#38, including acceptance tracker |

Initial estimates total **232 story points, 494 primary engineering hours, and 66 review hours**. These are planning estimates that need team refinement, not time worked or completed student contributions.

See the [complete Release 1 setup report](release-1-setup-report.md), [workload allocation](release-1-workload.md), [dependency graph](release-1-dependencies.md), and [traceability plan](release-1-traceability.md).

### Published Wiki

- Initialized and published the [GitHub Wiki](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki).
- Published eight content pages covering Home, onboarding, architecture, engineering workflow, iterations, testing, stakeholder/releases, and SOEN 490 evaluation, plus the sidebar and footer.
- Updated the official project name, industry partner, iteration links, and planning references.
- Verified all ten files against a fresh Wiki clone and checked all eight live content pages.
- Verified that all 48 distinct documentation targets exist at linked revision `0caf6f9`. Links remain pinned while the compliance documentation awaits merge into `main`.

Published Wiki commit: `6984b4ddd41cbc0a772376acba963630d5a5787c`.

## Validation and GitHub delivery

- The Release 1 planning revision passed 14 local tests and the GitHub Repository checks, Documentation checks, and SonarCloud checks.
- Wiki preparation and publication updates passed the local documentation and repository checks, plus whitespace checks.
- [PR #39](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/39) was merged into `docs/2-soen490-compliance`.
- [PR #3](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/3), targeting `main`, and [PR #40](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/pull/40), targeting the compliance branch, remain open at this snapshot.
- The Wiki is published separately from these repository PRs.

## Remaining work

- Review and merge the documentation PRs through the protected workflow.
- Create/configure the GitHub Project fields and views and share it with the professor; the available token lacks Projects permissions.
- Confirm student capacity, refine estimates, and confirm partner data access and acceptance criteria.
- Implement the planned application, run product tests, and collect actual iteration, release, demonstration, and stakeholder evidence.

## Contribution and AI disclosure

The user supplied requirements, directed and authorized the setup, and confirmed the browser step that initialized the Wiki. Codex drafted documentation and plans, performed the authorized GitHub configuration and publication, and ran the recorded checks. Human review remains pending where noted.

This is a summary of work completed during the setup session. It does not claim that the user personally authored every generated artifact, that planned application functionality is implemented, or that estimated engineering hours have been worked.
