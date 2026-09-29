# Traceability and evidence

Keep the chain visible in GitHub and in iteration/release records:

**Requirement → feature → story/technical issue → design → tasks → branch → commits → PR → tests/CI → review → stakeholder status → iteration → release → contributor.**

| Step | Evidence to maintain |
|---|---|
| Requirement / feature | Brief or approved requirement identifier; implemented feature label or clearly proposed scope |
| Issue / design / tasks | Acceptance criteria, estimates, risk, diagrams/ADR, dependencies and task checklist |
| Branch / commits | Issue number in branch and commit message; accurate author and AI disclosure |
| PR / tests / CI | Closing/reference link, tested revision, commands, actual results and workflow run links |
| Review / stakeholder | Independent approval and resolved feedback; authorized signoff or explicit pending/not-applicable rationale |
| Iteration / release | Exact milestone, completed scope, tag only on real completion and release evidence |
| Contributor | Personal design/implementation record with direct links; do not claim another person’s work |

## Real infrastructure example

[Issue #2](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/2) tracks this requested compliance follow-up under `feature:infrastructure` and Iteration 1. Its design is to preserve the existing documentation hierarchy, use real configuration evidence, and close the identified gaps without choosing an application stack. Implementation is reviewed on `docs/2-soen490-compliance`; follow the issue’s linked PR and commits for the actual revision and CI results. Independent review remains required. No stakeholder approval, completed iteration or personal student contribution is asserted by this administrative example.

The earlier commits `65786e0` and `609b617` have real changes but no issue references. Do not rewrite them or claim that this issue existed when they were made. Link them as historical context and follow the convention going forward.

## Future product example — placeholders only

```text
Requirement: <approved-requirement-id>
Feature label: feature:<approved-feature>
Story: #ISSUE
Design: <diagram/ADR link>
Branch: feature/<ISSUE>-short-description
Commit: <actual commit URL>
PR: <actual PR URL>
Tests / CI: <test cases and run URL>
Review / stakeholder: <approval or pending status>
Iteration: <exact milestone URL>
Release: <tag/release URL after completion>
Contributor: <personal contribution record>
```

Do not replace placeholders until the corresponding evidence exists. Keep the Project and issue milestone aligned during planning; prepare approximately the next two iterations, without populating future work for appearances.
