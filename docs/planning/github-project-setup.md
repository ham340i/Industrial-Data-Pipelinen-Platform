# GitHub Project setup

Status: not configured by this work; GitHub CLI unavailable. Actual Project URL: **TODO**. Owner to confirm: `ham340i` (repository owner), or an approved team organization.

## Create or reuse the board

After installing/authenticating GitHub CLI, inspect existing Projects first:

```sh
gh auth refresh -s project
gh project list --owner ham340i --format json
```

Reuse the appropriate existing Project. If none exists, create one:

```sh
gh project create --owner ham340i --title 'Local Pipeline Studio — SOEN 490' --format json
```

Record its actual number below; do not rerun creation blindly. Replace `123` with that number before running subsequent commands:

```sh
PROJECT_NUMBER=123
gh project link "$PROJECT_NUMBER" --owner ham340i --repo ham340i/Industrial-Data-Pipelinen-Platform
gh project field-list "$PROJECT_NUMBER" --owner ham340i --format json
```

Use the UI to add/edit fields after inspecting existing names. The CLI supports TEXT, SINGLE_SELECT, NUMBER fields; create the iteration field and adjust the built-in Status in the UI. [CLI field documentation](https://cli.github.com/manual/gh_project_field-create).

## Fields

In the Project table, use the rightmost **+** / New field; use Settings → Fields to edit existing fields. Do not duplicate built-in fields.

| Field | Type / options |
|---|---|
| Status | Existing single select: Backlog, Ready, In Progress, In Review, Blocked, Done |
| Priority | Single select: Critical, High, Medium, Low |
| Risk | Single select: High, Medium, Low |
| Story Points | Number |
| Ideal Hours | Number |
| Iteration | Iteration field; align dates with course schedule, including winter break and irregular release dates |
| Feature | Use built-in Labels with `feature:*` values as the authoritative category |
| Stakeholder Status | Single select: Not Reviewed, Review Requested, Approved, Changes Requested |
| Milestone | Show built-in repository milestone; exact course title is authoritative |
| Release | Single select: Release 1, Release 2, Release 3; leave blank until scoped |

Set issue milestones with the [milestone helper](../../scripts/github-setup/README.md). Project iteration and issue milestone are separate fields: reconcile them during planning. Plan approximately two iterations ahead. A Project iteration field’s default repeating schedule does not replace the supplied milestone dates.

## Saved views

Use **New view**, choose a layout, set filters/grouping in view options, then **Save changes**. Display points, ideal hours, risk, assignee and milestone in table views.

| View | Layout | Filter / grouping |
|---|---|---|
| Backlog | Table | `status:Backlog` |
| Current Iteration | Table | `iteration:@current` (requires configured dates) |
| Board | Board | Columns by Status; all active work |
| Roadmap | Roadmap | Date fields from Iteration; show Milestone |
| By Feature | Table | Group by Labels; filter `label:feature:*` if supported, otherwise select actual feature labels in UI |
| By Assignee | Table | Group by Assignees |
| Releases | Table | Group by Release; show Milestone and Stakeholder Status |

## Add real work and automation

Add existing issues through **Add item** or `gh project item-add "$PROJECT_NUMBER" --owner ham340i --url <actual-issue-url>` after replacing the placeholder. Set fields deliberately. Use built-in workflows to initialize new items to Backlog if available. Before enabling closed-item → Done automation, verify it respects the Definition of Done and required stakeholder review; otherwise keep Done manual. Record automation choices in Project description.

## Share with professor and team

Project Settings → Manage access → Invite collaborators: add **moar82** with Read access for evaluation and team members with appropriate access. Confirm the invitation and actual visibility. Project access does not grant access to private repository items: the repository owner must also arrange appropriate repository access under its supported permission model. Do not make confidential material public to work around access problems. [GitHub access documentation](https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-your-project/managing-access-to-your-projects).

Update README with the real Project URL and record access verification in the human-action checklist. The supplied course brief requires the board to be shared with moar82; merely linking this guide does not satisfy that requirement.
