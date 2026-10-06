# SQLite metadata foundation (#7)

The API persists project, pipeline revision, run, block registry and output endpoint metadata with SQLAlchemy 2. Alembic revision `0001` owns schema creation; application startup upgrades before serving requests. HTTP metadata CRUD and pipeline execution are subsequent stories. See [ADR-0002](architecture/decisions/ADR-0002-sqlite-metadata.md) and [verification](testing/issue-7-sqlite-metadata.md).

## Start and configure

Install the hash-pinned `requirements.lock` with Python 3.12 as described in the [developer guide](getting-started.md#backend-validation). Start the API from the repository root:

```sh
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Host default: `local-data/metadata.sqlite3`, relative to the process working directory. Override with `LPS_METADATA_PATH` before starting Python:

```sh
# POSIX example, using a private writable workspace:
export LPS_METADATA_PATH="$PWD/local-data/metadata.sqlite3"
```

```powershell
# Windows PowerShell example:
$env:LPS_METADATA_PATH = Join-Path (Get-Location) 'local-data\metadata.sqlite3'
```

Missing parent directories are created when opening a `Database`; importing application modules creates no files. Absolute paths avoid working-directory ambiguity. The configured location must be writable; permissions or migration failures stop startup. Settings are captured when the application imports. Use one startup process for this local SQLite foundation; coordinate migrations separately before introducing multiple workers. Sessions and connections must not be shared across concurrent requests.

Compose sets `LPS_METADATA_PATH=/var/lib/lps/metadata.sqlite3`. Its named `metadata` volume is writable by the non-root API user and persists across ordinary `docker compose down` and rebuilds. See the [workspace guide](local-workspace.md).

## Schema and integration boundary

| Entity | Identity and relationships |
|---|---|
| `Project` | UUID string; owns pipelines and workspace bindings |
| `Pipeline` | UUID string; unique name within a project |
| `PipelineRevision` | UUID string; unique positive revision within a pipeline; immutable portable JSON |
| `WorkspaceBinding` | UUID string; unique logical resource ID within a project; private local path and/or secret-provider reference |
| `Run` | UUID string; references one exact revision; state, UTC timestamps and optional row count |
| `BlockRegistryEntry` | Composite block ID/version; category index and public registry metadata |
| `OutputEndpoint` | UUID string; unique node/name within a run; CSV/Parquet format, logical artifact reference and optional row count |

Relationships restrict deletion of referenced history. Foreign keys are enabled for every connection; parent lookup indexes support joins. Timestamps are naive UTC because SQLite does not preserve timezone offsets. Unknown row counts are `None`; zero means a known empty result. Future registry/graph contracts belong to #8/#9; this foundation does not prescribe block ports, validate DAG topology or execute blocks.

Use `Database.transaction()` for a short unit of work. It commits on success, rolls back on any exception and always closes the session. SQLite has a five-second lock timeout; busy errors are surfaced, without silently retrying a partially executed unit of work. Explicit `BEGIN` makes schema and data changes transactional under Python 3.12's SQLite driver. Alembic and application operations use that same connection policy.

```python
from app.config import settings
from app.metadata.database import Database
from app.metadata.migrate import upgrade
from app.metadata.models import Pipeline, PipelineRevision, Project, Run

database = Database(settings.metadata_path)
try:
    upgrade(database)  # Only standalone tools need this; API startup already does it.
    with database.transaction() as session:
        project = Project(name="Synthetic demo")
        pipeline = Pipeline(project=project, name="Example pipeline")
        revision = PipelineRevision(
            pipeline=pipeline,
            revision=1,
            definition={"schema_version": 1, "nodes": [], "edges": []},
        )
        run = Run(pipeline_revision=revision)
        session.add(run)
        session.flush()
        print(run.id)
finally:
    database.close()
```

`revision.definition` returns a detached JSON copy. To change a persisted definition, create a new revision; existing runs keep their original revision. Scalar changes through the ORM are rejected. Trusted raw SQL/Core updates can bypass ORM immutability, so they are not a public revision editing interface.

Definitions use logical `resource_id` values. Resolve those IDs through project-scoped `WorkspaceBinding` rows at runtime. Do not serialize ORM relationships or bindings into an exported definition. Never store secret values in SQLite: `secret_reference` identifies a future external secret provider. This column is not an encrypted vault, and provider implementation is outside #7. The local database can contain sensitive paths/references and must remain private.

The recursive definition guard rejects known runtime keys (including `path`, `local_path`, `password`, `secret_reference`, `api_key`, `token`, credentials and connection strings), absolute POSIX/Windows/UNC paths and file URIs. JSON must have string keys, finite numbers and ordinary JSON values. This guard applies to ORM and typed Core inserts. It is not a general secret detector; arbitrary secret values under unknown keys cannot be identified. Use synthetic definitions and the later typed graph contract for field-level validation. `BlockRegistryEntry.public_metadata` must contain public descriptors only; output `artifact_ref` values are logical resource IDs, not machine paths or downloadable URLs.

## Migrations, backup and rollback

Explicit development commands, using the same path configuration as the API:

```sh
python -m app.metadata.migrate upgrade
python -m app.metadata.migrate check
# Future schema changes, after editing models:
python -m alembic revision --autogenerate -m "describe the metadata change"
```

Review generated migrations; replace application custom JSON types with stable `sqlalchemy.JSON()` so historical migrations do not import mutable application types. Ruff, mypy and pytest also check migration sources. Commit each migration with its model change. Do not use `Base.metadata.create_all()` to bypass version history.

Before upgrading valuable data, stop all writers and preserve a private copy of the SQLite file. No backup is sent to GitHub. Restoring the pre-upgrade database is the rollback path for valuable data. Tests exercise destructive down/up only against disposable files:

```sh
python -m app.metadata.migrate downgrade --confirm-data-loss
python -m app.metadata.migrate upgrade
```

Downgrading `0001` removes all seven metadata tables and their contents. The confirmation flag acknowledges deletion; it does not make downgrade safe for valuable data. Unrelated tables are retained. SQLite database files, local data and credentials stay ignored by Git and excluded from Docker build contexts. A complete Compose volume reset also deletes this metadata.

## Verification and review

Run `python -m ruff check`, `python -m ruff format --check`, `python -m mypy` and `python -m pytest`. With Docker and browser dependencies installed, `python scripts/smoke_workspace.py --browser` additionally verifies migrations and a real persisted project across container recreation. The smoke test only removes its own uniquely named synthetic stack.

Yousef led and delivered the metadata persistence, migrations, tests and documentation, with AI assistance. Executed checks are linked above; independent teammate review is tracked in PR #48.
