from __future__ import annotations

import sqlite3
from pathlib import Path

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class SqlSourceConfig(BaseModel):
    """Credential-free configuration for the local SQL source proof."""

    model_config = ConfigDict(extra="forbid")

    dialect: Literal["sqlite"] = "sqlite"
    database_path: str = Field(min_length=1)
    read_only: Literal[True] = True
    query: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("database_path")
    @classmethod
    def validate_database_path(cls, value: str) -> str:
        path = value.strip()

        if not path:
            raise ValueError("database_path must not be empty")

        if path in {".", ".."}:
            raise ValueError("database_path must identify a database file")

        return path

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        return _validate_read_query(value)

    @model_validator(mode="after")
    def reject_credential_parameters(self) -> SqlSourceConfig:
        for key in self.parameters:
            if key.lower() in _CREDENTIAL_KEYS:
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


def execute_read_only_sqlite(
    connection: sqlite3.Connection,
    query: str,
    parameters: dict[str, Any] | None = None,
) -> SqlQueryResult:
    """Execute a constrained read query using SQLite-bound parameters."""
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
        rows = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

        return SqlQueryResult(
            columns=columns,
            rows=rows,
        )
    except sqlite3.DatabaseError as exc:
        raise SqlSourceError("SQLite rejected the read-only query") from exc
    finally:
        connection.set_authorizer(None)


def read_sqlite_source(config: SqlSourceConfig) -> SqlQueryResult:
    """Open a SQLite database read-only and execute the configured query."""
    database_path = Path(config.database_path).expanduser()

    if not database_path.is_file():
        raise SqlSourceError(f"SQLite database does not exist: {database_path}")

    connection_uri = database_path.resolve().as_uri() + "?mode=ro"

    connection = sqlite3.connect(
        connection_uri,
        uri=True,
    )
    connection.row_factory = sqlite3.Row

    try:
        return execute_read_only_sqlite(
            connection,
            config.query,
            config.parameters,
        )
    finally:
        connection.close()
