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
        query = _remove_sql_comments(value).strip()

        if not query:
            raise ValueError("query must not be empty")

        if re.match(r"^(SELECT|WITH)\b", query, flags=re.IGNORECASE) is None:
            raise ValueError("only SELECT or WITH queries are allowed")

        if ";" in query:
            raise ValueError("multiple SQL statements are not allowed")

        for word in _UNSAFE_SQL_WORDS:
            if re.search(rf"\b{word}\b", query, flags=re.IGNORECASE):
                raise ValueError(f"unsafe SQL operation is not allowed: {word}")

        return query

    @model_validator(mode="after")
    def reject_credential_parameters(self) -> SqlSourceConfig:
        for key in self.parameters:
            if key.lower() in _CREDENTIAL_KEYS:
                raise ValueError(
                    "credential-like parameters are not allowed in portable definitions"
                )

        return self


def _remove_sql_comments(query: str) -> str:
    without_line_comments = re.sub(
        r"--.*?$",
        "",
        query,
        flags=re.MULTILINE,
    )

    return re.sub(
        r"/\*.*?\*/",
        "",
        without_line_comments,
        flags=re.DOTALL,
    )


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
    cleaned_query = _remove_sql_comments(query).strip()

    if (
        re.match(
            r"^(SELECT|WITH)\b",
            cleaned_query,
            flags=re.IGNORECASE,
        )
        is None
    ):
        raise SqlSourceError("only SELECT or WITH queries are allowed")

    if ";" in cleaned_query:
        raise SqlSourceError("multiple SQL statements are not allowed")

    for word in _UNSAFE_SQL_WORDS:
        if re.search(
            rf"\b{word}\b",
            cleaned_query,
            flags=re.IGNORECASE,
        ):
            raise SqlSourceError(f"unsafe SQL operation is not allowed: {word}")

    connection.set_authorizer(_sqlite_authorizer)

    try:
        cursor = connection.execute(
            cleaned_query,
            parameters or {},
        )
        columns = [description[0] for description in (cursor.description or [])]
        rows = [dict(row) for row in cursor.fetchall()]

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

    connection_uri = f"file:{database_path.resolve()}?mode=ro"

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
