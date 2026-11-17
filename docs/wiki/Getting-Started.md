# Getting started

What a new developer needs to run and change the system.

## Prerequisites

- Git
- Docker with Compose v2, for the packaged workspace
- Python 3.12, for backend development
- Node.js 24 and npm 11, for frontend development

No account, credential or dataset is required. Tests use synthetic fixtures in `tests/fixtures/`.

## Run the whole application

```sh
git clone https://github.com/ham340i/Industrial-Data-Pipelinen-Platform.git
cd Industrial-Data-Pipelinen-Platform
cp .env.example .env
docker compose up --build --detach --wait
```

Open http://127.0.0.1:3000. Stop with `docker compose down`; project metadata is kept in the `metadata` volume. Both services are published on loopback only.

## Develop the backend

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --only-binary :all: --require-hashes -r requirements.lock
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API documentation is served at http://127.0.0.1:8000/docs. Run the same checks as CI:

```sh
python -m ruff check
python -m ruff format --check
python -m mypy
python -m pytest
```

## Develop the frontend

```sh
cd frontend
npm ci --ignore-scripts
npm run dev
npm run check
```

`npm run check` runs ESLint, Prettier, the TypeScript compiler, Vitest and a production build.

## Configuration

| Variable | Used by | Default | Meaning |
|---|---|---|---|
| `FRONTEND_PORT`, `API_PORT` | Compose | 3000, 8000 | Loopback host ports |
| `LPS_METADATA_PATH` | API | `local-data/metadata.sqlite3` | SQLite metadata file |
| `LPS_WORKSPACE_ROOT` | API | unset | Folder that holds each project's data folder |
| `LPS_ALLOWED_WORKSPACE_ROOTS` | API | `[]` | JSON list of folders a user may pick as workspace |
| `LPS_LOG_LEVEL` | API | `INFO` | Log level for all `app.*` loggers |
| `VITE_API_BASE_URL` | Standalone frontend | `http://127.0.0.1:8000/api/v1` | API address; never put credentials here |

## Where things are

| Path | Contents |
|---|---|
| `app/` | FastAPI application: API routes, block SDK and blocks, executor, preview, run telemetry, artifacts, metadata |
| `frontend/src/` | React workbench: builder canvas, configuration, validation, preview, run controls and monitor, typed API client |
| `tests/` | Backend unit, API and integration tests with synthetic fixtures |
| `migrations/` | Alembic migrations for the SQLite metadata database |
| `docker/`, `compose.yml`, `frontend/Dockerfile` | Container images and the local multi-service workspace |
| `experiments/` | Recorded spikes (headless ETL proof, Polars and Arrow measurements) |
| `scripts/` | Repository checks and GitHub administration helpers |
| `docs/` | Architecture, testing evidence, iteration and release records, and the source of this Wiki |

More detail: [developer guide](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/getting-started.md), [local workspace](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/local-workspace.md), [contribution guide](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/.github/CONTRIBUTING.md).
