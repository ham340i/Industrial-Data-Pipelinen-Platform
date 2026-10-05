# ADR-0002: SQLite metadata and portable revision boundaries

Status: Proposed for student review; implementation for [issue #7](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/7). Reviewer: `joedaswagger`. No human agreement or stakeholder acceptance is asserted.

## Context and decision

The merged FastAPI shell needs persistent metadata for projects, portable pipeline versions, runs, registry entries and outputs. Use the specified SQLAlchemy 2 / SQLite / Alembic stack. A `Pipeline` identifies a project-owned pipeline; an immutable `PipelineRevision` holds its single authoritative JSON definition. Runs reference a revision, never a mutable latest graph. Do not duplicate graph nodes/edges in relational tables. The graph/DAG contract and execution remain issues #9 and #22.

Machine-specific `WorkspaceBinding` rows map project-scoped logical resource IDs to local paths and optional secret-provider references. They contain no credential values and are excluded from definition export. Portable definitions reject reserved runtime/credential fields and absolute paths recursively; this is a bounded portability guard, not a general secret detector. Contributors must still use non-sensitive configuration and reviewed synthetic data. The future graph contract can tighten structural validation without replacing this storage boundary.

The initial schema includes projects, pipelines, revisions, workspace bindings, runs, block registry entries and output endpoints. IDs are UUID strings except registry identity/version pairs. Foreign keys use RESTRICT to retain referenced history. Uniqueness, nonempty names, positive revision numbers, supported run states and nonnegative optional row counts are database constraints. A completed row count is unknown until recorded; null is not zero. Registry JSON is public SDK metadata, not runtime objects. Outputs use logical artifact references; artifact publication and advanced telemetry belong to later issues.

## Transactions and migration lifecycle

`Database.transaction()` creates a short-lived session, commits on success, rolls back on failure and always closes it. SQLite foreign keys are enabled on every pooled connection. SQLAlchemy emits BEGIN explicitly to include DDL in transactions; this avoids the sqlite3 legacy transaction mode's autocommitted DDL. Connections have a bounded five-second busy timeout. There is no distributed-write guarantee.

Alembic is the sole schema creation path; the application never calls `create_all()`. Startup upgrades the configured database before serving requests and disposes the engine on shutdown/failure. One local service process performs migration before traffic. Multiple workers/operators must serialize schema upgrades; production coordination, data retention and backup policy remain future decisions.

`LPS_METADATA_PATH` selects a local file, defaulting to ignored `local-data/metadata.sqlite3`. Compose selects `/var/lib/lps/metadata.sqlite3` in its existing non-root persistent volume. Paths are passed through SQLAlchemy URL objects rather than interpolated connection strings. No database or directory is created by importing application modules.

## Alternatives and consequences

Mutable graph JSON plus run copies creates competing definitions. Normalized graph tables duplicate the pending DAG contract. A file-only JSON store has no relational/transaction constraints. SQLite is sufficient for the planned single-workstation app; external databases and an async driver add scope without an existing requirement.

Read-only copies of revision definitions prevent unnoticed in-place JSON mutation. Persisted revision updates are rejected by the ORM; a new revision is required. Database foreign keys prevent deleting revisions used by runs. Direct SQL is a trusted administration interface and can bypass ORM validation, so it is not exposed through the API.

The initial downgrade removes these tables and their data. It is for disposable development databases; back up real data before any downgrade. Existing project CRUD, engine execution, block SDK, artifact writes and end-to-end ETL acceptance are not implemented by this schema foundation.

## Verification

Tests must exercise real temporary SQLite files, constraints and foreign keys, portable JSON boundaries, restart persistence, atomic rollback, initial upgrade/downgrade/re-upgrade, schema drift and API lifespan cleanup. Extend the isolated Compose smoke to persist/reload an actual project row. Record executed results in the [issue #7 verification record](../../testing/issue-7-sqlite-metadata.md).

Implementation references: [SQLAlchemy SQLite transaction control](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#transactions-with-sqlite-and-the-sqlite3-driver) and [Alembic shared connections](https://alembic.sqlalchemy.org/en/latest/cookbook.html#sharing-a-connection-with-a-series-of-migration-commands-and-environments).

AI assistance: Codex drafted this design and its implementation at Al-Yousef's request. Independent design review and student understanding/demonstration remain pending.
