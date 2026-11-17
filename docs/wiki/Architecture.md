# Overall architecture and class diagrams

This page describes the system as implemented at Release 1.

## Guiding rule

**The UI authors definitions. The engine executes definitions.** The executor and the block SDK run without React or any UI state, so a pipeline can be validated and run headlessly from Python or through the API.

## High-level architecture

```mermaid
flowchart TD
    subgraph Browser
        UI[React workbench<br/>builder, configuration, validation,<br/>preview, run controls, run monitor]
    end
    subgraph API[FastAPI process on loopback]
        MW[Middleware<br/>correlation ID, request log,<br/>preview body and concurrency limits]
        R[Routers<br/>projects, pipelines, validate, preview,<br/>execute and timer, runs, artifacts, blocks, settings]
        V[Pipeline validation]
        P[Bounded preview service]
        S[Run service and timer scheduler]
        X[DAG executor]
        K[Block SDK and registry<br/>sources, transforms, quality, sinks, triggers]
        A[Artifact registration and query]
    end
    DB[(SQLite metadata<br/>SQLAlchemy and Alembic)]
    WS[(Project workspace folder<br/>inputs and Parquet or CSV outputs)]
    UI -->|REST and JSON| MW --> R
    R --> V
    R --> P --> K
    R --> S --> X --> K
    R --> A
    V --> K
    X -->|Polars frames| K
    K -->|read and atomic write| WS
    A -->|DuckDB bounded read| WS
    R --> DB
    S -->|run, block and event rows| DB
    A --> DB
```

## Layers and where they live

| Layer | Responsibility | Code |
|---|---|---|
| Presentation | Workbench pages and panels | [frontend/src](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/App.tsx) |
| Client state | Unsaved graph and selection (Zustand); server data (TanStack Query) | [frontend/src/state](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/state/editor.ts) |
| API client | Typed requests and response parsers that reject malformed payloads | [frontend/src/api](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/api/client.ts) |
| API | Routing, request validation, error envelope, middleware | [app/main.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/main.py), `app/*/api.py` |
| Application services | Validation, preview planning, run recording, timers, artifact governance | [validation](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/pipelines/validation.py), [preview](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/preview/service.py), [runs](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/runs/service.py), [artifacts](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/artifacts/query.py) |
| Domain | Portable pipeline definition, block contracts, executor | [pipeline model](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/pipelines/models.py), [block contracts](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/contracts.py), [executor](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/execution/runtime.py) |
| Blocks | One module per responsibility | [resources](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/resources.py), [readers](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/files.py), [sinks](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/sinks.py), [transforms](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/transforms.py), [join and aggregate](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/relational.py), [quality](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/quality.py), [SQL](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/sql.py), [triggers](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/blocks/triggers.py) |
| Persistence | Metadata models and migrations | [models](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/metadata/models.py), [migrations](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/migrations/versions) |

Dependencies point downward: API modules import services and domain; blocks never import the API, the executor or the database.

## Domain model (metadata)

```mermaid
erDiagram
    PROJECT ||--o{ PIPELINE : contains
    PROJECT ||--o{ WORKSPACE_BINDING : "maps resources to files"
    PIPELINE ||--o{ PIPELINE_REVISION : "immutable versions"
    PIPELINE_REVISION ||--o{ RUN : "executed as"
    RUN ||--o{ RUN_BLOCK : "per-block state, timing, row count"
    RUN ||--o{ RUN_EVENT : "redacted log events"
    RUN ||--o{ OUTPUT_ENDPOINT : "published artifacts"
    BLOCK_REGISTRY {
        string block_id
        string version
    }
```

A run always refers to an immutable pipeline revision, so run history stays meaningful after the pipeline is edited. An output is registered only after its file has been written successfully.

## Block SDK classes

```mermaid
classDiagram
    class Block {
        <<abstract>>
        +descriptor BlockDescriptor
        +config_model
        +run(config, inputs, context) PortValues
        +preview(config, inputs, context, limits) PortValues
        #_execute(config, inputs, context)* PortValues
    }
    class FileSource {
        <<abstract>>
        #_read(path, config)*
    }
    class FileSink {
        <<abstract>>
        #_write(path, table, config)*
    }
    Block <|-- FileSource
    Block <|-- FileSink
    Block <|-- SelectColumns
    Block <|-- RenameColumns
    Block <|-- Filter
    Block <|-- Cast
    Block <|-- Sort
    Block <|-- Join
    Block <|-- Aggregate
    Block <|-- NullHandling
    Block <|-- SchemaValidation
    Block <|-- NullCheck
    Block <|-- RowCount
    Block <|-- SqlSource
    Block <|-- ManualTrigger
    Block <|-- TimerTrigger
    FileSource <|-- CsvSource
    FileSource <|-- JsonSource
    FileSource <|-- ParquetSource
    FileSink <|-- CsvSink
    FileSink <|-- ParquetSink
    class BlockRegistry {
        +register(block)
        +resolve(block_id, version) RegisteredBlock
    }
    class Executor {
        +execute(definition) ExecutionContext
    }
    BlockRegistry o-- Block
    Executor --> BlockRegistry
```

`Block.run` is the single execution boundary: it validates configuration, checks every input and output against the declared port schemas, emits lifecycle events and converts any failure into a public `BlockError` that carries a code, never a stack trace or a data value.

## Run sequence

```mermaid
sequenceDiagram
    participant UI as Workbench
    participant API
    participant Val as Validation
    participant Run as Run service
    participant Ex as Executor
    participant DB as Metadata
    UI->>API: POST pipelines/{id}/execute
    API->>Val: diagnose(revision)
    Val-->>API: diagnostics (must be empty)
    API->>DB: create run (queued)
    API-->>UI: 201 run id
    Run->>Ex: execute(definition)
    loop each node in topological order
        Ex->>Ex: check retained-data budget
        Ex->>Run: state event
        Run->>DB: block state, timing, rows, redacted log
    end
    UI->>API: GET runs/{id} (polling)
    API-->>UI: run and block evidence
```

## Design decisions

Recorded as architecture decision records: [workbench shell](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/architecture/decisions/ADR-0001-workbench-shell.md), [SQLite metadata](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/architecture/decisions/ADR-0002-sqlite-metadata.md), [block SDK contract](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/architecture/decisions/ADR-0003-block-sdk-contract.md), [portable DAG](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/architecture/decisions/ADR-0004-portable-dag.md), [local projects](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/architecture/decisions/ADR-0005-local-projects.md).

Per-feature design notes: [local executor](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/architecture/local-executor.md), [graph validation](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/architecture/graph-validation.md), [selected-node preview](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/architecture/selected-node-preview.md), [run telemetry](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/architecture/run-telemetry.md), [triggers and execute](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/architecture/triggers-and-execute.md), [artifact governance](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/architecture/artifact-governance.md), [error recovery](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/architecture/error-recovery.md).

## Changes since the Release 1 target

- The file block module was split into resource configuration, readers, sinks and three bounded previews, and the transform module into row and column transforms and relational blocks. Behaviour is unchanged.
- Logging is configured in one place ([app/logging_config.py](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/app/logging_config.py)).
