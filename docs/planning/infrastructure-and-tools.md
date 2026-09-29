# Infrastructure and tools

| Tool | Why used / where | Version or observed state | Remaining decision |
|---|---|---|---|
| Python | Standard-library repository checks, GitHub reconciliation and unittest suite in `scripts/` | Minimum 3.11; local 3.13.0 observed | Product language not selected |
| Bash | Thin GitHub setup wrappers | Local interpreter available; CI uses runner Bash | No product shell/runtime choice implied |
| Git | Source history and Wiki transport | Installed; no history rewritten | Confirm public contributor identity |
| GitHub repository / Issues | Collaboration, feature labels, 13 iteration milestones and issue #2 | Live repository-admin access verified | Create/assign real product stories |
| GitHub Projects | Required planning board | API blocked by missing Projects scope | Create/reuse board, configure views and share with moar82 |
| GitHub Actions | PR/main checks in `.github/workflows/` | Both baseline workflows passed; checkout pinned at v4.2.2 SHA | Review existing Dependabot PR #1 independently |
| Dependabot | GitHub Actions dependency update PRs | Weekly schedule; actual PR #1 observed | Review upgrades and test them |
| SonarCloud | External code-analysis check observed on baseline | Neutral result; no local configuration found | Owner confirms integration, data access and plan |
| GitHub CLI | Optional administration helpers | Not installed locally; follow-up used authenticated API | Install only if team wants CLI workflow |
| Product framework/library/database/deployment platform | None | Not selected or installed | Record ADRs and verified commands with implementation |

No application package manager, lockfile or external runtime dependency exists. Use a locked install and caching when actual dependencies are introduced; do not add unused ecosystems for appearance. Costs/credits are tracked as unknown in the [budget](budget.md).
