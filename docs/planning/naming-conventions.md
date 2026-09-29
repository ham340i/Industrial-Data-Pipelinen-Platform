# Naming and traceability

- Product display name: **Local Pipeline Studio**. Repository slug remains `Industrial-Data-Pipelinen-Platform`; do not assume it has been renamed.
- Branches: `feature/<issue>-short-description`, `bugfix/<issue>-short-description`, `spike/<issue>-short-description`, `docs/<issue>-short-description`.
- Commits: `type(scope): concrete change (#issue)`; see [contribution guide](../../.github/CONTRIBUTING.md).
- Features: one primary `feature:*` label from [label catalog](../../scripts/github-setup/labels.json). Optional product capabilities are planned categories, not implemented features.
- ADRs: `ADR-0001-short-title.md`; meeting records: `YYYY-MM-DD-short-topic.md`; iteration records: `iteration-N.md`; release records: `release-N.md`.
- Tags: exactly `Iteration1` … `Iteration13`, and `Release1`, `Release2`, `Release3`, created only upon completion.
- Requirements: use a stable team-assigned identifier in the issue’s source-requirement field; do not renumber accepted requirements silently.

Carry the requirement and feature into an issue, link design and discussion, use the issue number in branch/commits/PR, link tests, assign the exact milestone, and summarize the chain in iteration/release contribution tables. Use real GitHub links when records exist; TODO text is not evidence.
