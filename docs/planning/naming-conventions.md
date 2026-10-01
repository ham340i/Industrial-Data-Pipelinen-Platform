# Naming and traceability

- Product display name: **Local Pipeline Studio**. Repository slug remains `Industrial-Data-Pipelinen-Platform`; do not assume it has been renamed.
- Branches: `feature/<issue>-short-description`, `bugfix/<issue>-short-description`, `spike/<issue>-short-description`, `docs/<issue>-short-description`.
- Commits: `type(scope): concrete change (#issue)`; see [contribution guide](../../.github/CONTRIBUTING.md).
- Features: one primary `feature:*` label from [label catalog](../../scripts/github-setup/labels.json). Only implemented infrastructure is active; [proposed product categories](../github-labels.md) require team-approved scope before creation.
- ADRs: `ADR-0001-short-title.md`; meeting records: `YYYY-MM-DD-short-topic.md`; iteration evidence: `docs/iterations/iteration-N/` (Iteration 4 uses `iteration-4-release-1/`); Release 1 evidence: `docs/release-1/`. Existing planning record paths remain valid.
- Tags: follow the [versioned strategy for Iterations 1–4 / Release 1](../iterations/README.md#completion-tags). Later iteration/release names remain planned; create no tag before completion and explicit owner instruction.
- Requirements: use a stable team-assigned identifier in the issue’s source-requirement field; do not renumber accepted requirements silently.

Carry the requirement and feature into an issue, link design and discussion, use the issue number in branch/commits/PR, link tests, assign the exact milestone, and summarize the chain in iteration/release contribution tables. Use real GitHub links when records exist; TODO text is not evidence.

## Implemented tooling conventions

The repository scripts use Python and Bash; no product framework conventions can be selected yet.

| Item | Current convention / example |
|---|---|
| Python files, functions and variables | `snake_case`, e.g. `check_docs.py`, `existing_records`, `script_dir` |
| Python classes | `PascalCase`, e.g. `DocumentationTests` in the test suite |
| Constants | `UPPER_SNAKE_CASE`, e.g. `ROOT`, `CATALOG`, `REMOTE` |
| Tests | `test_*.py`, `unittest.TestCase` classes and `test_*` methods |
| Bash scripts | Existing hyphenated names such as `create-labels.sh`; quote variable expansions |
| Documents | Descriptive hyphenated names; keep existing uppercase index/template conventions |

Do not rename stable files solely for style. Select product conventions with the eventual ecosystem and document departures in the relevant design review.
