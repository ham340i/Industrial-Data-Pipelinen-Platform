# karimikhaeil — Iteration 2 issue #19

Status: implemented locally on October 14, 2026; independent review pending.

Karim requested the assigned project create/list/open story. Codex implemented
the API and UI, runtime response validation, browser selection restoration,
project-scoped draft behavior and feature/integration tests. The design reuses
SQLite and TanStack Query and adds no production dependencies or migrations.

- Branch: `feature/19-local-projects`.
- Issue: #19; planned reviewer: `menaboulus`.
- [Design](../architecture/decisions/ADR-0005-local-projects.md).
- [Backend](../../app/projects.py) and [UI](../../frontend/src/Projects.tsx).
- [Guide](../projects.md).
- [Observed tests and limitations](../testing/issue-19-local-projects.md).

AI Assistance: Karim supplied direction and authorized implementation. Codex
generated and verified the changes. No separate manual implementation or checks
by Karim, hosted CI, completed independent approval, merge or stakeholder
acceptance is claimed. Actual refinement/review contributions can be added when
they occur. Iteration 1 carryover #9/#13 remains in separate PRs.
