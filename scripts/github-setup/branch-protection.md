# Protect main

Status: not configured or remotely inspected. Requires repository administration access and a GitHub plan supporting protection for this repository. Preserve existing rules; inspect before editing.

1. Merge/push the workflow files through the team’s authorized review process and let both Actions workflows run successfully at least once.
2. Confirm another teammate can review PRs. In repository Settings → Branches → Add branch protection rule (or edit the existing main rule), use branch pattern `main`.
3. Enable **Require a pull request before merging**, with **1 approval**. Enable **Require conversation resolution before merging**.
4. Enable **Require status checks to pass before merging**, selecting the actual GitHub Actions check contexts for `Repository checks` and `Documentation checks` after they appear. Require branches to be up to date when practical for team throughput.
5. Disallow force pushes and deletion. Apply protections to administrators / disable bypass where the team’s access and recovery arrangements permit. Do not add broad push restrictions that prevent normal reviewed PR merges.
6. Save, then verify a real PR is blocked before approval/checks and mergeable once requirements are satisfied. Record the resulting settings and any permitted bypass in an issue.

Do not add application check names until those checks exist. If plan/permissions prevent protection, record the limitation and follow the same PR/review policy manually until enabled; do not claim enforcement. No API PUT is provided because replacing a full protection document could overwrite unseen existing settings.

[GitHub protection guidance](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule).
