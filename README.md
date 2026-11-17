# Local Pipeline Studio

[![CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/workflows/ci.yml)
[![Documentation checks](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/workflows/documentation-check.yml/badge.svg?branch=main)](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/actions/workflows/documentation-check.yml)

Industrial Data Pipeline Engineering Platform: a SOEN 490 capstone project at Concordia University with industry partner Pratt & Whitney Canada.

CI runs on every pull request and push to `main`: repository and documentation checks, backend lint, format, strict type check and tests, frontend lint, format, type check, tests, build and browser smoke, and a Docker Compose smoke test. See [Testing plan and continuous integration](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Testing-Plan-and-Continuous-Integration).

## Release demos

| Release | Demo video | Release notes | Tag |
|---|---|---|---|
| Release 1 | Not recorded yet | [Release 1 notes](docs/releases/iteration-4-release-1.md) | Not tagged yet |
| Release 2 | Planned for February 2027 | | |
| Release 3 | Planned for April 2027 | | |

## Project summary

Local Pipeline Studio is a local-first visual ETL workbench for manufacturing data. A process specialist draws a pipeline as a graph of blocks (file and SQL sources, column and row transforms, joins and aggregates, data-quality checks, CSV and Parquet sinks), validates it, previews any step on a bounded sample, runs it on their own workstation manually or on a timer, follows block-by-block run evidence, and publishes governed Parquet outputs that analysts can query. Nothing leaves the machine: there is no cloud service, no account and no telemetry, and pipeline definitions are portable files that never contain credentials.

## Developer getting started guide

Prerequisites: Git, Docker with Compose v2, and for development Python 3.12 and Node.js 24 with npm 11. No credentials or datasets are needed.

Run the whole application:

```sh
git clone https://github.com/ham340i/Industrial-Data-Pipelinen-Platform.git
cd Industrial-Data-Pipelinen-Platform
cp .env.example .env
docker compose up --build --detach --wait
```

Open http://127.0.0.1:3000. Stop with `docker compose down`.

Backend development and checks:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --only-binary :all: --require-hashes -r requirements.lock
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
python -m ruff check && python -m ruff format --check && python -m mypy && python -m pytest
```

On Windows PowerShell use `py -3.12 -m venv .venv` and `.\.venv\Scripts\python.exe` in place of `python`.

Frontend development and checks:

```sh
cd frontend
npm ci --ignore-scripts
npm run dev
npm run check
```

API documentation is served at http://127.0.0.1:8000/docs. Configuration variables, the directory layout and troubleshooting are in [Getting started](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Getting-Started), the [developer guide](docs/getting-started.md) and the [local workspace guide](docs/local-workspace.md). Read the [contribution guide](.github/CONTRIBUTING.md) before opening a pull request.

### Repository layout

| Path | Contents |
|---|---|
| `app/` | FastAPI application: routes, block SDK and blocks, DAG executor, preview, run telemetry, artifacts, metadata |
| `frontend/` | React workbench and its tests |
| `tests/` | Backend unit, API and integration tests with synthetic fixtures |
| `migrations/` | Alembic migrations for the SQLite metadata database |
| `docker/`, `compose.yml` | Container images and the local multi-service workspace |
| `experiments/` | Recorded spikes |
| `scripts/` | Repository checks and GitHub administration helpers |
| `docs/` | Design notes, testing evidence, iteration and release records, Wiki source |

### Project board

Not linked yet. The repository owner must create the GitHub Project, share it with **moar82** and put its URL here; see [board setup](docs/GITHUB_PROJECT_SETUP.md). Until then, planning is visible in [milestones](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/milestones) and [issues](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues).

## Wiki table of contents

- [Home](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Home)
- [Meeting minutes](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Meeting-Minutes)
- [Risks](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Risks)
- [User consent and end-user license agreement](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/User-Consent-and-EULA)
- [Legal and ethical issues](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Legal-and-Ethical-Issues)
- [Economic](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Economic)
- [Budget](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Budget)
- [Personas](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Personas)
- [Diversity statement](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Diversity-Statement)
- [Overall architecture and class diagrams](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Architecture)
- [Infrastructure and tools](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Infrastructure-and-Tools)
- [Name conventions](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Naming-Conventions)
- [Testing plan and continuous integration](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Testing-Plan-and-Continuous-Integration)
- [Security](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Security)
- [Performance](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Performance)
- [Deployment plan and infrastructure](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Deployment-Plan-and-Infrastructure)
- [Missing knowledge and independent learning](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Missing-Knowledge-and-Independent-Learning)
- [Code quality practices](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Code-Quality)
- [Iteration and release notes](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Iteration-and-Release-Notes)

The Wiki is published from [docs/wiki](docs/wiki/Home.md).

## AI usage

AI coding tools were used on this project. Each source file declares its AI contribution level on its first line, each pull request declares it in its description, and [AI_USAGE.md](.github/AI_USAGE.md) records the tools, the AI-assisted features, how they were verified and the problems found.

## License

No license has been selected yet, so no rights are granted. See [Legal and ethical issues](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Legal-and-Ethical-Issues).

## What is still open

See [remaining actions](SOEN490_HUMAN_ACTIONS.md).
