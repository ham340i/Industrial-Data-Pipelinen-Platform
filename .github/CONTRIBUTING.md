# Contributing

Every student must progressively demonstrate substantial engineering design and implementation on complex open-ended problems, with visible engineering contributions in **every iteration**. Link real work; commit counts alone do not establish engineering contribution.

## From issue to merge

1. Select a story, bug, engineering task or bounded spike. Record the originating requirement and apply one primary `feature:*` label plus the appropriate `type:*` label.
2. Confirm its iteration milestone and Project fields. Plan approximately two iterations ahead; leave future scope unassigned until agreed.
3. Assign yourself and record estimates, priority, risk and dependencies. Use GitHub identities, never student IDs or private contact details.
4. Branch from current `main`: `feature/<issue-number>-short-description`, `bugfix/<issue-number>-short-description`, `spike/<issue-number>-short-description` or `docs/<issue-number>-short-description`.
5. Document design before substantial implementation: boundaries, diagrams, alternatives and an ADR when needed. Link discussion summaries on the issue.
6. Implement the acceptance criteria in a reviewable change. Record unsuccessful experiments in the spike; preserve learning and code references.
7. Write tests appropriate to the change. Use synthetic data. Capture actual commands and results; explain any test category that does not apply.
8. Commit with issue references and meaningful AI disclosure. Use a GitHub-registered email or GitHub-provided noreply address for attribution; do not publish personal contact details in documents.
9. Push your branch to the repository.
10. Open a PR with the provided template; use `Closes #<number>` for completed scope and link design/test evidence.
11. Complete [AI disclosure](AI_USAGE.md), including your own contribution and verification.
12. Obtain at least one independent teammate review. Review correctness, design, acceptance criteria, data handling, tests and documentation. The author cannot supply their own independent approval.
13. Resolve feedback and CI failures. Re-request review after material changes.
14. Merge only after the [Definition of Done](../docs/planning/definition-of-done.md) and required checks are satisfied.
15. Confirm issue closure and Project status. Record required stakeholder review honestly; pending acceptance must remain visible.
16. Update iteration records, architecture, release notes and individual contribution links as applicable.

## Commit convention

```text
feat(builder): add draggable transform node (#42)
fix(engine): preserve schema metadata during joins (#57)
test(validation): add null-handling edge cases (#63)
docs(architecture): document local execution model (#71)
```

These are illustrative formats, not existing issues or work. Replace example numbers with a real issue; new meaningful commits must reference it. The earlier setup commits lacked issue links and will not be rewritten. A useful body explains the change:

```text
Implements the initial transformation-node configuration flow.

Related to #42

AI-Assisted: Codex used to scaffold tests; tests reviewed and extended manually.
```

Use that footer only when true. Never manufacture commits or attribution. When squash merging, preserve issue references, accurate co-authorship and AI disclosure.

## Main and quality gates

Main should require PRs, one reviewer, resolved conversations and passing checks. Follow [protection setup](../scripts/github-setup/branch-protection.md) after the checks have run. Current gates validate repository tooling and documentation; application install/lint/type/test/build gates must be added with the selected stack.

Run the [README checks](../README.md#running-tests) locally. Do not commit secrets or stakeholder datasets. Report suspected exposure privately to the repository owner; rotate exposed credentials before removing them. Do not include secret values in issues.

## Personal evidence and milestone planning

Maintain a [personal contribution record](../docs/individual-contributions/README.md) every iteration/release and link the [traceability chain](../docs/traceability.md). Record who actually designed, implemented and verified each part; disclose AI-generated work. Plan roughly the next two milestones with the team and record estimates before execution where possible. Never invent retrospective estimates.

Main now requires one approving teammate review, both named repository checks, an up-to-date branch and resolved conversations, including for administrators. Stale approvals are dismissed after new commits. Do not bypass the rule to mark a task complete.
