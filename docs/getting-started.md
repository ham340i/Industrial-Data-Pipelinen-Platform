# Developer getting started

## Current capability

You can run repository validation and administration tooling. **The ETL application does not exist yet.** There is no frontend/backend framework, database, development server or product build command to run.

## Prerequisites

Git, Python 3.11+ and Bash. Tests use the Python standard library only. Optional GitHub administration requires authenticated GitHub CLI; Wiki publication uses authorized SSH access. Repository checks require no network access or credentials.

## Clone

```sh
git clone https://github.com/ham340i/Industrial-Data-Pipelinen-Platform.git
cd Industrial-Data-Pipelinen-Platform
python3 --version
```

## Install and environment setup

No dependency installation, package manager, virtual environment or environment variables are required for current tooling. There is no `.env.example` because no application variables have been defined. Do not create dummy credentials. Future implementation must add safe variable examples, a lockfile and verified installation instructions.

## Database setup

Not available: no database/schema/migration tooling exists.

## Development server and build

Not available: no application server or build system exists. Do not assume `npm`, Docker or framework-specific commands. Develop repository tooling on an [issue-linked branch](../.github/CONTRIBUTING.md).

## Tests

```sh
python3 -m unittest discover -s scripts/tests -v
```

These test the repository tools, including failure detection and safe GitHub reconciliation. They do not test ETL behavior.

## Lint, formatting and type checks

```sh
python3 scripts/check_repository.py
python3 scripts/check_docs.py
git diff --check
```

The first command checks Python/Bash syntax, selected configuration rules, trailing whitespace and limited secret patterns. The second checks local Markdown links/headings and whitespace. No general Python linter, automatic formatter or static type checker is configured. Avoid claiming these commands provide those broader checks. `.yml` configuration currently uses JSON-compatible YAML, deliberately parsed with the standard library.

## Deployment / local production

No product artifact or production mode exists. See the [deployment plan](deployment/deployment-plan.md). Wiki publishing is documentation administration, described in [Wiki setup](../scripts/github-setup/wiki-setup.md).

## Troubleshooting

| Symptom | Resolution |
|---|---|
| Python command unavailable or older than 3.11 | Install an approved Python 3.11+ interpreter and confirm `python3 --version` |
| Script cannot find Git files | Use a Git clone; run the commands from its root |
| Broken document link/heading | Correct the relative target or heading; rerun `check_docs.py` |
| Configuration parse failure | Keep JSON-compatible YAML or introduce a reviewed parser change; do not bypass CI |
| Potential secret detected | Inspect the reported path privately; rotate any exposed credential and coordinate cleanup |
| `gh` unavailable | Install/authenticate CLI for administration, or use GitHub UI instructions; no token is needed for local checks |
| Project API scope error | Current credential lacks Projects scope; use [Project setup](GITHUB_PROJECT_SETUP.md) |
| Wiki clone says repository not found | Save the first Home page in GitHub; see [Wiki setup](../scripts/github-setup/wiki-setup.md) |
| Main rejects a push/merge | Use a PR, resolve conversations, get one teammate approval and pass both required checks |

Report genuine tooling defects as issues with sanitized output, environment and revision. Do not copy private tokens or personal machine details into public logs.
