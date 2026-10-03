# Developer getting started

## Current capability

The React workbench shell is implemented under issue #5, alongside repository validation tools. Backend services, project persistence, the graph editor and ETL execution remain future work. See the [frontend guide](frontend/workbench.md) for configuration, architecture, usage and troubleshooting.

## Prerequisites and setup

Use Git, Python 3.11+ for repository checks, and Node.js 24 with npm 11 for the frontend. Bash is used by administration scripts. GitHub administration additionally requires authenticated tooling.

```sh
git clone https://github.com/ham340i/Industrial-Data-Pipelinen-Platform.git
cd Industrial-Data-Pipelinen-Platform
cd frontend
npm ci --ignore-scripts
npm run dev
```

The frontend runs on the loopback URL printed by Vite. The API defaults to http://127.0.0.1:8000; an offline warning is expected without a backend. Optional public configuration is documented in [the frontend guide](frontend/workbench.md) and `frontend/.env.example`. Database setup is not available yet.

## Frontend validation and build

From `frontend/`:

```sh
npm run check
npm run preview
```

`check` includes lint, formatting, types, tests and build. Preview serves the built shell locally; it is not a deployment service.

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

A frontend static build is available via `npm run build` in `frontend/`; the full ETL product is not deployable yet. See the [deployment plan](deployment/deployment-plan.md). Wiki publishing is documentation administration, described in [Wiki setup](../scripts/github-setup/wiki-setup.md).

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
