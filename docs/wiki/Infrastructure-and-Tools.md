# Infrastructure and tools

Each entry says what the tool does here and why it was chosen over the obvious alternative.

## Backend

| Tool | Use | Why this one |
|---|---|---|
| Python 3.12 | Language | Typed generics syntax used by the block SDK; Polars and Arrow have first-class wheels |
| FastAPI | HTTP API | Request and response validation from type hints and generated OpenAPI; chosen over Flask, which needs separate validation |
| Pydantic v2 | Contracts for API, pipeline definitions and block configuration | One schema drives validation, error messages and the generated configuration forms |
| Uvicorn | ASGI server | Reference server for FastAPI |
| Polars | Tabular transforms in the executor | Strict types and explicit nulls; measured against Arrow in [#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13); chosen over pandas for memory behaviour and type strictness |
| PyArrow and Parquet | File format for governed outputs and bounded previews | Columnar, typed, readable by analytics tools |
| DuckDB | Bounded queries over registered Parquet artifacts | Reads Parquet in place with a memory ceiling, no server to run |
| SQLite | Metadata store | Local-first product: no database server to install; see [ADR-0002](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/architecture/decisions/ADR-0002-sqlite-metadata.md) |
| SQLAlchemy 2 and Alembic | Typed models and schema migrations | Migrations preserve existing run history on upgrade |

## Frontend

| Tool | Use | Why this one |
|---|---|---|
| React 19, TypeScript, Vite | Workbench | Typed components and fast local builds; see [ADR-0001](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/architecture/decisions/ADR-0001-workbench-shell.md) |
| @xyflow/react (React Flow) | Graph canvas | Nodes, typed ports and connections without writing a canvas engine |
| MUI | Components | Accessible form controls out of the box |
| TanStack Query and Axios | Server state and HTTP | Caching, polling of run status, cancellation of stale requests |
| Zustand | Unsaved editor state | Small store without reducer boilerplate; server data stays in TanStack Query |
| React Router | Navigation | Hash routing works when the build is served as static files |

## Quality and delivery

| Tool | Use |
|---|---|
| pytest, httpx | Backend unit, API and integration tests |
| Vitest, React Testing Library, MSW | Frontend unit tests and HTTP-mock integration tests |
| Playwright | Chromium smoke tests of the built workbench, the Compose stack and the standalone stack |
| Ruff | Python lint and format |
| mypy (strict) | Python type checking |
| ESLint, Prettier, tsc | TypeScript lint, format and type checking |
| GitHub Actions | CI on every pull request and push to main |
| Dependabot | Weekly update pull requests for Actions, the Python lock and the npm lock |
| SonarCloud | External analysis check on pull requests |
| Docker and Compose | Reproducible local deployment of API and workbench |
| uv | Regenerates the hash-pinned `requirements.lock` |

## Dependency discipline

- Python: version ranges in [requirements.txt](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/requirements.txt) and [requirements-dev.txt](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/requirements-dev.txt); exact versions and hashes in [requirements.lock](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/requirements.lock), installed with `--require-hashes`.
- Frontend: [package.json](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/package.json) and `package-lock.json`, installed with `npm ci --ignore-scripts`.
- GitHub Actions are pinned to commit SHAs.

## Development tools

Git and GitHub (issues, milestones, labels, pull requests, Wiki), any editor with Ruff, mypy and ESLint integration, and the FastAPI-generated API explorer at `/docs`.
