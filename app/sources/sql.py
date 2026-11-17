# AI contribution: 50% or more AI-generated
from __future__ import annotations

import sqlite3
from pathlib import Path, PureWindowsPath

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.secret_policy import is_credential_key


_CREDENTIAL_KEYS = {
    "username",
    "user",
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "connection_string",
    "dsn",
    "url",
}

_UNSAFE_SQL_WORDS = {
    "ALTER",
    "ATTACH",
    "BEGIN",
    "CALL",
    "COMMIT",
    "CREATE",
    "DELETE",
    "DETACH",
    "DROP",
    "EXEC",
    "INSERT",
    "PRAGMA",
    "REPLACE",
    "ROLLBACK",
    "UPDATE",
    "VACUUM",
}

# Inspect SQL syntax without treating quoted contents as comments/operators.
# The original query is always passed to SQLite, which remains the parser.
_SQL_NON_CODE = re.compile(
    r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`(?:``|[^`])*`|\[[^\]]*\]"
    r"|--[^\r\n]*|/\*.*?(?:\*/|\Z)",
    flags=re.DOTALL,
)


def _validate_read_query(value: str) -> str:
    query = value.strip()
    code = _SQL_NON_CODE.sub(" ", query).strip()

    if not code:
        raise ValueError("query must not be empty")
    if re.match(r"^(SELECT|WITH)\b", code, flags=re.IGNORECASE) is None:
        raise ValueError("only SELECT or WITH queries are allowed")
    if ";" in code:
        raise ValueError("multiple SQL statements are not allowed")
    for word in _UNSAFE_SQL_WORDS:
        if re.search(rf"\b{word}\b", code, flags=re.IGNORECASE):
            raise ValueError(f"unsafe SQL operation is not allowed: {word}")

    return query


# Work budgets for the standalone reader; the workspace block (app.blocks.sql)
# exposes the same bounds as per-node configuration.
DEFAULT_MAX_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_ROWS = 100_000
DEFAULT_MAX_STEPS = 1_000_000
_DATABASE_SUFFIXES = (".sqlite3", ".sqlite", ".db")


class SqlSourceConfig(BaseModel):
    """Credential-free configuration for the local SQL source proof.

    ``database_path`` is a workspace-relative resource, never a machine path:
    ``read_sqlite_source`` resolves it beneath the caller's workspace root.
    """

    model_config = ConfigDict(extra="forbid")

    dialect: Literal["sqlite"] = "sqlite"
    database_path: str = Field(min_length=1, max_length=1024)
    read_only: Literal[True] = True
    query: str = Field(min_length=1, max_length=20000)
    parameters: dict[str, Any] = Field(default_factory=dict, max_length=100)

    @field_validator("database_path")
    @classmethod
    def validate_database_path(cls, value: str) -> str:
        path = value.strip()

        if not path:
            raise ValueError("database_path must not be empty")

        if path in {".", ".."}:
            raise ValueError("database_path must identify a database file")

        # Lexical checks only: no filesystem access for configuration data.
        windows = PureWindowsPath(path)
        if (
            "\x00" in path
            or path.startswith(("~", "/", "\\"))
            or windows.drive
            or windows.is_absolute()
            or Path(path).is_absolute()
            or ".." in windows.parts
        ):
            raise ValueError(
                "database_path must be relative to the workspace without traversal"
            )

        if not path.lower().endswith(_DATABASE_SUFFIXES):
            raise ValueError("database_path must name a .sqlite3, .sqlite or .db file")

        return path

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        return _validate_read_query(value)

    @model_validator(mode="after")
    def reject_credential_parameters(self) -> SqlSourceConfig:
        for key in self.parameters:
            if key.lower() in _CREDENTIAL_KEYS or is_credential_key(key):
                raise ValueError(
                    "credential-like parameters are not allowed in portable definitions"
                )

        return self


class SqlSourceError(RuntimeError):
    """Raised when a SQL source violates the read-only execution contract."""


class SqlQueryResult(BaseModel):
    """Deterministic tabular result returned by a SQL source."""

    columns: list[str]
    rows: list[dict[str, Any]]


_ALLOWED_SQLITE_ACTIONS = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    sqlite3.SQLITE_FUNCTION,
    sqlite3.SQLITE_RECURSIVE,
}


def _sqlite_authorizer(
    action: int,
    _arg1: str | None,
    _arg2: str | None,
    _database: str | None,
    _source: str | None,
) -> int:
    """Allow reads only at SQLite's execution boundary."""
    if action in _ALLOWED_SQLITE_ACTIONS:
        return sqlite3.SQLITE_OK

    return sqlite3.SQLITE_DENY


def _row_bytes(row: tuple[Any, ...]) -> int:
    return sum(
        len(value.encode("utf-8"))
        if isinstance(value, str)
        else len(value)
        if isinstance(value, bytes)
        else 8
        for value in row
    )


def _fetch_rows(
    cursor: sqlite3.Cursor,
    columns: list[str],
    max_rows: int | None,
    max_bytes: int | None,
) -> list[dict[str, Any]]:
    """Stream the result while enforcing the accumulated row and byte budgets."""
    rows: list[dict[str, Any]] = []
    result_bytes = 0
    for row in cursor:
        if max_rows is not None and len(rows) >= max_rows:
            raise SqlSourceError("SQL result exceeds the row budget")
        result_bytes += _row_bytes(row)
        if max_bytes is not None and result_bytes > max_bytes:
            raise SqlSourceError("SQL result exceeds the byte budget")
        if len(row) != len(columns):
            raise SqlSourceError("SQLite returned an unexpected column count")
        rows.append(dict(zip(columns, row, strict=False)))
    return rows


def execute_read_only_sqlite(
    connection: sqlite3.Connection,
    query: str,
    parameters: dict[str, Any] | None = None,
    *,
    max_rows: int | None = None,
    max_bytes: int | None = None,
) -> SqlQueryResult:
    """Execute a constrained read query using SQLite-bound parameters.

    The workspace block in app.blocks.sql bounds the database file size,
    SQLite value length and column count (setlimit), and VM work (progress
    handler with cancellation). Here, streaming enforces aggregate result
    bytes and rows; the block derives the row cap from max_rows/max_cells.
    Both layers are needed: engine limits bound individual values/work,
    while streaming budgets bound accumulated output. Standalone callers
    must supply their own engine/work limits and optional result budgets.
    """
    try:
        original_query = _validate_read_query(query)
    except ValueError as exc:
        raise SqlSourceError(str(exc)) from exc

    connection.set_authorizer(_sqlite_authorizer)

    try:
        cursor = connection.execute(
            original_query,
            parameters or {},
        )
        columns = [description[0] for description in (cursor.description or [])]
        if len(columns) != len(set(columns)):
            raise SqlSourceError(
                "SQL result column names must be unique; use explicit aliases"
            )

        rows = _fetch_rows(cursor, columns, max_rows, max_bytes)

        return SqlQueryResult(
            columns=columns,
            rows=rows,
        )
    except sqlite3.DatabaseError as exc:
        raise SqlSourceError("SQLite rejected the read-only query") from exc
    finally:
        connection.set_authorizer(None)


def _contained_database(database: str | Path, workspace_root: Path) -> tuple[Path, int]:
    """Resolve the database (following links) inside the workspace; return its size."""
    try:
        root = workspace_root.resolve(strict=True)
        database_path = (root / database).resolve(strict=True)
        database_path.relative_to(root)
        if not database_path.is_file():
            raise ValueError("Not a file")
        size = database_path.stat().st_size
    except (OSError, ValueError, RuntimeError):
        raise SqlSourceError(
            "SQLite database is missing or outside the workspace"
        ) from None
    return database_path, size


def read_sqlite_source(
    config: SqlSourceConfig,
    *,
    workspace_root: Path,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_rows: int = DEFAULT_MAX_ROWS,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> SqlQueryResult:
    """Open a workspace SQLite database read-only and run the bounded query.

    The database must resolve, after following links, to a file inside
    ``workspace_root``. Errors never include the resolved machine path (#32).
    Engine limits mirror the workspace block: value length, VM steps, and
    streamed row/byte budgets.
    """
    database_path, size = _contained_database(config.database_path, workspace_root)
    if size > max_bytes:
        raise SqlSourceError("SQLite database exceeds the byte budget")

    connection = sqlite3.connect(database_path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row

    try:
        connection.execute("PRAGMA query_only = ON")
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, max_bytes)
        steps = 0

        def progress() -> int:
            nonlocal steps
            steps += 1000
            return int(steps > max_steps)

        connection.set_progress_handler(progress, 1000)
        return execute_read_only_sqlite(
            connection,
            config.query,
            config.parameters,
            max_rows=max_rows,
            max_bytes=max_bytes,
        )
    finally:
        connection.close()
