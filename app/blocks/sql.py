# AI contribution: 50% or more AI-generated
"""Workspace-bound read-only SQLite source (#23)."""

import json
import sqlite3
from typing import Any

from pydantic import Field, field_validator

from app.blocks.base import Block
from app.blocks.context import BlockContext
from app.blocks.contracts import BlockDescriptor, PortValues, Table, require_public_json
from app.blocks.errors import BlockError
from app.blocks.files import SourceConfig, resource_path, unique_object
from app.blocks.tabular import TABLE_PORT, descriptor_values, to_frame
from app.sources.sql import (
    _validate_read_query,
    execute_read_only_sqlite,
    SqlSourceError,
)


class SqlConfig(SourceConfig):
    columns: list[str] = Field(min_length=1, max_length=1000)
    query: str = Field(min_length=1, max_length=20000)
    parameters_json: str = Field(default="{}", max_length=20000)
    max_steps: int = Field(default=1000000, ge=1000, le=10000000)

    @field_validator("query")
    @classmethod
    def read_query(cls, value: str) -> str:
        return _validate_read_query(value)

    @field_validator("parameters_json")
    @classmethod
    def named_values(cls, value: str) -> str:
        parameters = json.loads(value, object_pairs_hook=unique_object)
        if not isinstance(parameters, dict) or any(
            not isinstance(key, str)
            or not key.isidentifier()
            or (item is not None and type(item) not in (str, int, float, bool))
            for key, item in parameters.items()
        ):
            raise ValueError("Parameters require named scalar values")
        require_public_json(parameters)
        return value


class SqlSource(Block[SqlConfig]):
    config_model = SqlConfig
    descriptor = BlockDescriptor(
        **descriptor_values("source.sql", "SQL Source", "source"),
        outputs=(TABLE_PORT,),
    )

    def _execute(
        self, config: SqlConfig, inputs: PortValues, context: BlockContext
    ) -> PortValues:
        path = resource_path(context, config.resource_ref, ".sqlite3")
        connection: sqlite3.Connection | None = None
        try:
            if not path.is_file() or path.stat().st_size > config.max_bytes:
                raise BlockError(
                    "sql_connection_failed", "Database unavailable or too large."
                )
            connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
            connection.execute("PRAGMA query_only = ON")
            connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, config.max_bytes)
            connection.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, config.max_columns)
            steps = 0

            def progress() -> int:
                nonlocal steps
                steps += 1000
                context.check_cancelled()
                return int(steps > config.max_steps)

            connection.set_progress_handler(progress, 1000)
            parameters: dict[str, Any] = json.loads(config.parameters_json)
            result = execute_read_only_sqlite(
                connection,
                config.query,
                parameters,
                max_rows=min(
                    config.max_rows, config.max_cells // max(1, len(config.columns))
                ),
                max_bytes=config.max_bytes,
            )
            if result.columns != config.columns or not config.columns:
                raise BlockError(
                    "schema_mismatch", "Declare SQL columns in result order."
                )
            if len(result.columns) > config.max_columns:
                raise BlockError("table_limit", "SQL result exceeds the column limit.")
            try:
                table = Table(
                    data_schema=config.declared_schema(), rows=tuple(result.rows)
                )
                to_frame(table)
            except Exception:
                raise BlockError(
                    "schema_mismatch", "SQL values violate the declared scalar schema."
                ) from None
            return {"table": (table,)}
        except BlockError:
            raise
        except SqlSourceError:
            context.check_cancelled()
            raise BlockError(
                "sql_query_failed", "Read query failed or exceeded its budget."
            ) from None
        except (OSError, sqlite3.Error):
            raise BlockError(
                "sql_connection_failed", "Database connection failed."
            ) from None
        finally:
            if connection is not None:
                connection.close()
