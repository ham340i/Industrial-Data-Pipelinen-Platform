# Contributing

The canonical [contribution guide](.github/CONTRIBUTING.md) covers issue requirements, branching, commit attribution, AI acknowledgement, tests, independent review and iteration updates.

Before starting, read the [developer guide](docs/getting-started.md), [Definition of Done](docs/planning/definition-of-done.md), [traceability guide](docs/traceability.md) and [personal contribution requirements](docs/individual-contributions/README.md). Keep one source of policy; update the linked guide rather than duplicating it here.

## Iteration workflow

Start from current `main` and use `feature/<issue-number>-short-description`, `fix/<issue-number>-short-description` or `docs/<issue-number>-short-description`. Examples: `feature/8-block-sdk`, `feature/9-pipeline-model`, `feature/10-headless-etl` (naming examples, not claims that these branches exist).

Feature branch → implementation, tests and documentation → PR → CI → assigned independent student review → merge to `main`. Do not develop directly on `main`. All accepted engineering work eventually integrates into the one application on `main`; preserve contribution authorship and history.

Update [iteration documentation](docs/iterations/README.md) and actual personal contribution evidence. Use the [planned tag strategy](docs/iterations/README.md#completion-tags) only after completion and explicit owner instruction. Professor `moar82` is an academic reviewer and receives no engineering issues, story points or routine PR review assignments.
