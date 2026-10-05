from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.sources.sql import (
    SqlSourceConfig,
    SqlSourceError,
    execute_read_only_sqlite,
    read_sqlite_source,
)


@pytest.fixture
def synthetic_sqlite_db(tmp_path: Path) -> Path:
    fixture_path = Path(__file__).parent / "fixtures" / "sql" / "measurements.sql"
    database_path = tmp_path / "synthetic_measurements.sqlite3"

    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(fixture_path.read_text(encoding="utf-8"))
        connection.commit()
    finally:
        connection.close()

    return database_path


def make_config(
    database_path: Path,
    query: str,
    parameters: dict[str, object] | None = None,
) -> SqlSourceConfig:
    return SqlSourceConfig.model_validate(
        {
            "dialect": "sqlite",
            "database_path": str(database_path),
            "read_only": True,
            "query": query,
            "parameters": parameters or {},
        }
    )


def test_read_sqlite_source_returns_deterministic_result(
    synthetic_sqlite_db: Path,
) -> None:
    config = make_config(
        synthetic_sqlite_db,
        (
            "SELECT asset_id, measurement_name, measurement_value, "
            "observed_at, quality_status "
            "FROM measurements "
            "WHERE asset_id = :asset_id "
            "ORDER BY observed_at"
        ),
        {"asset_id": 1001},
    )

    result = read_sqlite_source(config)

    assert result.columns == [
        "asset_id",
        "measurement_name",
        "measurement_value",
        "observed_at",
        "quality_status",
    ]
    assert result.rows == [
        {
            "asset_id": 1001,
            "measurement_name": "temperature",
            "measurement_value": 72.5,
            "observed_at": "2026-10-05T08:00:00Z",
            "quality_status": "valid",
        },
        {
            "asset_id": 1001,
            "measurement_name": "temperature",
            "measurement_value": 73.1,
            "observed_at": "2026-10-05T08:10:00Z",
            "quality_status": "valid",
        },
    ]


def test_parameter_binding_does_not_interpolate_sql(
    synthetic_sqlite_db: Path,
) -> None:
    config = make_config(
        synthetic_sqlite_db,
        "SELECT asset_id FROM measurements WHERE asset_id = :asset_id",
        {"asset_id": "1001 OR 1=1"},
    )

    result = read_sqlite_source(config)

    assert result.rows == []


@pytest.mark.parametrize(
    "query",
    [
        "INSERT INTO measurements VALUES "
        "(9999, 'temperature', 55.1, "
        "'2026-10-05T09:00:00Z', 'valid')",
        "UPDATE measurements SET quality_status = 'review'",
        "DELETE FROM measurements",
        "DROP TABLE measurements",
        "ALTER TABLE measurements ADD COLUMN extra TEXT",
    ],
)
def test_runtime_boundary_rejects_write_queries(
    synthetic_sqlite_db: Path,
    query: str,
) -> None:
    connection = sqlite3.connect(synthetic_sqlite_db)
    connection.row_factory = sqlite3.Row

    try:
        with pytest.raises(SqlSourceError):
            execute_read_only_sqlite(connection, query)
    finally:
        connection.close()


def test_read_only_connection_rejects_write_even_if_boundary_is_bypassed(
    synthetic_sqlite_db: Path,
) -> None:
    connection_uri = f"file:{synthetic_sqlite_db.resolve()}?mode=ro"
    connection = sqlite3.connect(connection_uri, uri=True)

    try:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute(
                "UPDATE measurements "
                "SET quality_status = 'review' "
                "WHERE asset_id = 1001"
            )
    finally:
        connection.close()
