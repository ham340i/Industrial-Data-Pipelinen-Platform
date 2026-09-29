# GitHub setup helpers

GitHub CLI remains unavailable locally. An authorized API follow-up created the active labels and all 13 milestones and protected main; see the [current audit](../../docs/SOEN490_COMPLIANCE_AUDIT.md). These CLI helpers remain available for later reconciliation. Install [GitHub CLI](https://cli.github.com/), authenticate with repository administration rights, then inspect the intended repository:

```sh
gh auth login
gh auth status
gh repo view ham340i/Industrial-Data-Pipelinen-Platform --json nameWithOwner,url,defaultBranchRef,viewerPermission
bash scripts/github-setup/create-labels.sh
bash scripts/github-setup/create-milestones.sh
```

The last two commands default to a read-only preview. To create missing entries:

```sh
bash scripts/github-setup/create-labels.sh --apply
bash scripts/github-setup/create-milestones.sh --apply
```

Use `--repo OWNER/REPO` for an intentionally different target. Scripts page through all existing entries (including closed milestones), create only missing names, leave existing entries unchanged and report drift. Exit 2 means drift requires review; exit 1 means a command/configuration failure. They do not delete or overwrite anything. Do not run concurrent setup writers. After a partial API failure, rerun to reconcile existing entries. The catalog uses supplied dates at 23:59:59 UTC; GitHub normalizes the returned timestamp to midnight. Reconciliation compares calendar dates. Confirm course submission time separately.

- [Label catalog](labels.json): only implemented infrastructure is an active feature area; proposed product labels are listed separately in [label guidance](../../docs/github-labels.md). `stakeholder:approved` requires real evidence.
- [Milestone catalog](milestones.json): exact 13 titles/dates from the brief.
- [Project setup](setup-project.md): create/reuse board, fields, views and access.
- [Branch protection](branch-protection.md): configure only after check names exist and a reviewer is available.
- [Wiki setup](wiki-setup.md): initialize the first page, then publish maintained navigation pages.

Issue forms live under `.github/ISSUE_TEMPLATE/`; they become available after merging to the default branch. Do not create fake issues just to fill the board.
