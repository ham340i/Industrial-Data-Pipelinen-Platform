# Protect main

Historical status: the earlier administration audit configured one approval, the then-existing repository/documentation checks, up-to-date branches and resolved conversations, including admins and stale-approval dismissal. October 4, 2026: GitHub confirms main is protected, but current WRITE credentials cannot read classic protection settings; exact current enforcement is unverified. Backend, frontend and Compose checks now exist and have passed. An administrator must inspect and maintain the actual rule, preserving any stricter existing settings. See the [current audit](../../docs/team-readiness-2026-10-04.md).

1. Merge/push the workflow files through the team’s authorized review process and let both Actions workflows run successfully at least once.
2. Confirm another teammate can review PRs. In repository Settings → Branches → Add branch protection rule (or edit the existing main rule), use branch pattern `main`.
3. Enable **Require a pull request before merging**, with **1 approval**. Enable **Require conversation resolution before merging**.
4. Enable **Require status checks to pass before merging**, preserving existing required contexts and including `Repository checks`, `Documentation checks`, `Backend checks`, `Frontend checks` and `Compose workspace smoke`. These contexts exist and passed on the latest main CI and the #49 fix PR. Require branches to be up to date when practical for team throughput.
5. Disallow force pushes and deletion. Apply protections to administrators / disable bypass where the team’s access and recovery arrangements permit. Do not add broad push restrictions that prevent normal reviewed PR merges.
6. Save, then verify a real PR is blocked before approval/checks and mergeable once requirements are satisfied. Record the resulting settings and any permitted bypass in an issue.

Do not add application check names until those checks exist. If plan/permissions prevent protection, record the limitation and follow the same PR/review policy manually until enabled; do not claim enforcement. No API PUT is provided because replacing a full protection document could overwrite unseen existing settings.

[GitHub protection guidance](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule).
