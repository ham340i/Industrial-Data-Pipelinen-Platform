# GitHub Project configuration

Required name: **SOEN 490 - Industrial Data Pipeline Platform**.
Status: **MANUAL ACTION REQUIRED**. The authenticated GraphQL query still returned `INSUFFICIENT_SCOPES` for Projects. Repository administration works, but the credential lacks `read:project` / `project`. No Project creation, field/view setup or professor sharing is claimed.

## 1. Create or reuse in the browser

1. Sign in as the authorized owner and open the owner’s **Projects** page. Inspect existing projects first; reuse the correct board if it exists.
2. Otherwise choose **New project → Table**, name it exactly **SOEN 490 - Industrial Data Pipeline Platform**, and create it under the appropriate authorized owner (currently repository owner `ham340i`).
3. Open Project **Settings**, link `ham340i/Industrial-Data-Pipelinen-Platform`, and add a description linking the [Release 1 plan](../release-1-plan.md).
4. Record its actual URL in README and this guide. Do not claim it exists until saved and accessible.

## 2. Fields

Use table **+ → New field** and **Settings → Fields**. Reuse built-in fields and existing equivalent custom fields rather than creating duplicates.

| Field | Type / values | Source |
|---|---|---|
| Title | Built-in | Issue title |
| Assignees | Built-in | Exactly one primary student per work item; acceptance tracker unassigned |
| Status | Built-in single select | Backlog, Ready, In Progress, In Review, Testing, Stakeholder Review, Done |
| Milestone | Built-in | Exact existing Iteration 1–4 milestones |
| Feature | Single select | Primary `feature:*` label from the backlog; include infrastructure and the 15 planned product feature values |
| Story Points | Number | Initial estimate in issue/backlog |
| Priority | Single select | Critical, High, Medium, Low |
| Risk | Single select | High, Medium, Low |
| Ideal Time | Number, hours | Primary engineering hours; excludes separate reviewer reserve |
| Start Date | Date | Leave empty until a real start is agreed |
| Target Date | Date | Milestone due date unless team sets an earlier delivery date |
| Reviewer | Text (optional) | Planned student reviewer; never moar82 |

Do not use Story Points as individual performance scores. All newly planned cards start **Backlog**, not In Progress. Move to Ready after refinement/contracts/capacity are confirmed. The acceptance tracker has zero points/hours to avoid double-counting. `Feature` mirrors the primary feature label; keep both aligned at triage.

## 3. Add the actual Release 1 issues

Open [Release 1 issues](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues?q=is%3Aissue%20label%3Arelease%3A1), select the planned issues and choose **Projects → this Project**. Repeat across pages if needed. Alternatively use Project **Add item** and paste each actual URL from the [backlog](release-1-backlog.json) or [metadata CSV](release-1-project-items.csv). The CSV is a field-entry reference, not a claim of built-in GitHub CSV import support.

Set each card’s custom fields from its issue metadata. Assignments and milestones already exist on issues; adding cards must not change them. Do not add arbitrary collaborators as students. The professor receives access only.

## 4. Saved views

Create each with **New view**, apply filters/grouping, and **Save changes**. The base filter is `label:"release:1"`; use field/filter menus if text syntax differs in your UI.

| View | Layout | Filter / grouping |
|---|---|---|
| Release 1 | Table | Base filter; group by Milestone |
| Iteration 1 | Table | Base + `milestone:"Iteration 1"` |
| Iteration 2 | Table | Base + `milestone:"Iteration 2"` |
| Iteration 3 | Table | Base + `milestone:"Iteration 3"` |
| Iteration 4 - Release 1 | Table | Base + `milestone:"Iteration 4 (Release 1)"` |
| Current Iteration | Table | Base + current milestone (initially Iteration 1); update at planning |
| Next Iteration | Table | Base + next milestone (initially Iteration 2); update at planning |
| By Feature | Table | Base; group by custom Feature |
| By Assignee | Table | Base; group by Assignees |
| High Risk | Table | Base + `risk:High`; sort by Target Date |
| Testing | Table | Base + `status:Testing` |
| Stakeholder Review | Table | Base + `status:"Stakeholder Review"` |
| Board | Board | Base; columns by Status |

Show points, ideal time, risk, priority, reviewer and target date in tables. Do not mark Done automatically from assignment or elapsed time; require the issue’s Definition of Done and required acceptance status.

## 5. Professor visibility

**Professor Rodrigo Morales Alvarado (moar82) — academic reviewer, not engineering contributor.**

Project **Settings → Manage access → Invite collaborators**: grant `moar82` appropriate read/review visibility and verify acceptance. A repository invitation for `moar82` is already **pending** and was preserved without modification/cancellation. The public repository is readable; pending membership and Project access are distinct. Do not assign issues, points, documentation, tests or ordinary engineering PR reviews to the professor. Confirm access to private Project items and demo links separately.

## Optional CLI route after authorization

Install GitHub CLI if desired, authenticate locally, and authorize Project access without posting a token in chat or Git:

```sh
gh auth status
gh auth refresh -s project
gh project list --owner ham340i --format json
```

If no equivalent exists:

```sh
gh project create --owner ham340i --title 'SOEN 490 - Industrial Data Pipeline Platform' --format json
```

Replace `123` with its actual number before continuing:

```sh
PROJECT_NUMBER=123
gh project link "$PROJECT_NUMBER" --owner ham340i --repo ham340i/Industrial-Data-Pipelinen-Platform
gh project field-list "$PROJECT_NUMBER" --owner ham340i --format json
```

For a missing numeric field, for example:

```sh
gh project field-create "$PROJECT_NUMBER" --owner ham340i --name 'Story Points' --data-type NUMBER
```

Create/edit dates, Status and views in the UI as above. To add a specific real issue, run `gh project item-add "$PROJECT_NUMBER" --owner ham340i --url <actual-issue-url>` after replacing the placeholder. Check existing items first.

Sources: [GitHub Projects API permissions](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects), [field creation](https://cli.github.com/manual/gh_project_field-create), [Project access](https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-your-project/managing-access-to-your-projects).
