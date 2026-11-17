# Code quality practices

## Directory structure and how it maps to the architecture

The backend is grouped by feature, and each feature keeps the same internal split: `api.py` for routes, a service or domain module for logic, and `models.py` for contracts. See the layer table on the [Architecture](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Architecture) page.

## Style

- Python: PEP 8 through Ruff (rules E, F, W, B, UP) and Ruff format; mypy in strict mode. Configuration: [pyproject.toml](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/pyproject.toml).
- TypeScript: typescript-eslint, React Hooks rules and Prettier, with zero warnings allowed. Configuration: [eslint.config.js](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/eslint.config.js).
- All of it is enforced in CI; see [Testing plan and CI](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Testing-Plan-and-Continuous-Integration).

## Framework best practices we follow

| Practice | Where |
|---|---|
| FastAPI dependency injection for the database handle, not a global | [projects.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/projects.py) |
| FastAPI lifespan for start-up migration, recovery of interrupted runs and timer shutdown | [main.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/main.py) |
| One exception handler per domain error, all returning the same error envelope | [main.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/main.py), [schemas/errors.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/schemas/errors.py) |
| Pydantic models as the single source of validation for requests, definitions and block configuration | [pipelines/models.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/pipelines/models.py), [blocks/contracts.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/contracts.py) |
| ASGI middleware for cross-cutting concerns (correlation ID, request log, preview limits) | [main.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/main.py), [preview/api.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/preview/api.py) |
| SQLAlchemy 2 typed models with Alembic migrations instead of manual SQL | [metadata/models.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/metadata/models.py), [migrations](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/migrations/versions) |
| TanStack Query for server state and polling; Zustand only for unsaved editor state | [RunMonitor.tsx](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/RunMonitor.tsx), [state/editor.ts](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/state/editor.ts) |
| Typed API client whose parsers reject unexpected payloads | [api/guards.ts](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/api/guards.ts), [api/runs.ts](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/api/runs.ts) |

## Implementation beyond CRUD

| Flow | Code |
|---|---|
| Static validation of a pipeline graph: duplicates, dangling edges, cycles by strongly connected component, port and schema compatibility, input cardinality | [pipelines/validation.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/pipelines/validation.py) |
| Topological DAG execution with failure propagation, cancellation and a retained-data budget | [execution/runtime.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/execution/runtime.py) |
| Bounded streaming previews of CSV, JSON and Parquet | [csv_preview.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/csv_preview.py), [json_preview.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/json_preview.py), [file_preview.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/file_preview.py), [parquet_decode.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/parquet_decode.py) |
| Join with cardinality checks, aggregate with overflow detection, lossless casts | [relational.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/relational.py), [tabular.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/tabular.py) |
| Data-quality gates that pass, warn or stop a run | [quality.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/quality.py) |
| Durable run telemetry with recovery of interrupted runs and log redaction | [runs/recorder.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/runs/recorder.py), [runs/redaction.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/runs/redaction.py) |
| In-process interval timer with safe stop and shutdown | [runs/scheduler.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/runs/scheduler.py) |
| Atomic, no-clobber publication of outputs and governed artifact queries | [file_sinks.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/file_sinks.py), [artifacts/query.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/artifacts/query.py) |

## Logging

- **Backend:** Python's `logging`, configured once in [app/logging_config.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/logging_config.py). Every module uses `logging.getLogger(__name__)`. The level comes from `LPS_LOG_LEVEL`.
- **What is logged:** start-up and shutdown, every request (method, path, status, duration, correlation ID), refused requests by error code, run start and outcome, block failures by error code, preview outcome, and unhandled errors with a stack trace.
- **Levels:** INFO for normal operations, WARNING for refused work and failed blocks, ERROR for unexpected failures.
- **What is never logged:** request bodies, query strings, data values, credentials or machine paths. Run log text shown to users is passed through [redaction](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/runs/redaction.py).
- **Frontend:** there is no logging library. Errors are shown to the user in the interface, and each API error carries the correlation ID that identifies the matching server log line.

## Error handling

- Every API error has the same shape: a stable code, a message written for the user, the correlation ID, and the node or field concerned when there is one.
- Blocks raise `BlockError` with a code; unknown exceptions inside a block become `execution_failed` without leaking their text.
- The workbench maps codes to guidance and offers a retry that keeps unsaved edits ([#33](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/33)).
- No exception is swallowed silently: the few places that must continue after a failure log it.

## Size and complexity limits

Backend source files are at most 500 lines, functions at most 50 lines and cyclomatic complexity at most 15. Two exceptions are recorded with their reasons:

- [Frontend components](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/refactoring/exceptions/frontend-components.md): React components over the limits, with the plan to reduce them. The API response parsers are within the limits.
- [Test modules and migrations](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/refactoring/exceptions/tests-and-migrations.md).

Guidelines: [refactoring guidelines](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/refactoring/refactoring-guidelines.md).

## AI-generated code

Each source file declares its AI contribution level on its first line, each pull request declares it in its description, and the [AI usage record](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/.github/AI_USAGE.md) lists the tools, the AI-assisted features, how each was verified and problems found. At Release 1, 179 of 214 files carry one; the rest need their authors and are listed in [remaining actions](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/SOEN490_HUMAN_ACTIONS.md).
