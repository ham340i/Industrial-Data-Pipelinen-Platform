from __future__ import annotations

import sqlite3
import shutil
from pathlib import Path

import pytest

from app.sources.sql import (
    SqlSourceConfig,
    SqlSourceError,
    execute_read_only_sqlite,
    read_sqlite_source,
    SqlQueryResult,
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


@pytest.mark.parametrize(
    "filename",
    [
        "measurements#revision.sqlite3",
        "measurements%23revision.sqlite3",
        "measurements 100%.sqlite3",
        "mésures.sqlite3",
    ],
)
def test_special_filename_reads_the_intended_database(
    synthetic_sqlite_db: Path, filename: str
) -> None:
    target = synthetic_sqlite_db.parent / filename
    shutil.copyfile(synthetic_sqlite_db, target)
    # Give plausible incorrectly decoded/truncated paths different data.
    for decoy in (
        target.parent / "measurements",
        target.parent / "measurements#revision.sqlite3",
    ):
        if decoy == target:
            continue
        shutil.copyfile(synthetic_sqlite_db, decoy)
        connection = sqlite3.connect(decoy)
        try:
            connection.execute("DELETE FROM measurements")
            connection.commit()
        finally:
            connection.close()

    config = make_config(target, "SELECT COUNT(*) AS row_count FROM measurements")
    assert read_sqlite_source(config).rows == [{"row_count": 3}]


def test_special_filename_keeps_real_connection_read_only(
    synthetic_sqlite_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = synthetic_sqlite_db.parent / "measurements#revision.sqlite3"
    shutil.copyfile(synthetic_sqlite_db, target)
    decoy = target.parent / "measurements"
    shutil.copyfile(synthetic_sqlite_db, decoy)

    def unchecked_write(
        connection: sqlite3.Connection,
        query: str,
        parameters: dict[str, object] | None = None,
    ) -> SqlQueryResult:
        connection.execute("UPDATE measurements SET asset_id = 9999")
        return SqlQueryResult(columns=[], rows=[])

    # Bypass query policy entirely: mode=ro must still protect the actual file.
    monkeypatch.setattr("app.sources.sql.execute_read_only_sqlite", unchecked_write)
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        read_sqlite_source(make_config(target, "SELECT asset_id FROM measurements"))


@pytest.mark.parametrize(
    "value",
    [
        "sensor/*A*/B",
        "sensor--A",
        "DROP UPDATE; PRAGMA",
        "O'Brien/*A*/B",
        "sensor/*unterminated",
    ],
)
def test_quoted_sql_value_is_preserved(synthetic_sqlite_db: Path, value: str) -> None:
    quoted = value.replace("'", "''")
    query = f"SELECT '{quoted}' AS marker"
    config = make_config(synthetic_sqlite_db, query)
    assert config.query == query
    assert read_sqlite_source(config).rows == [{"marker": value}]


@pytest.mark.parametrize(
    ("query", "name"),
    [
        ('SELECT 1 AS "value/*A*/B"', "value/*A*/B"),
        ("SELECT 1 AS `value--A`", "value--A"),
        ("SELECT 1 AS [DROP;UPDATE]", "DROP;UPDATE"),
        ('SELECT 1 AS "value""--A"', 'value"--A'),
    ],
)
def test_quoted_result_name_is_preserved(
    synthetic_sqlite_db: Path, query: str, name: str
) -> None:
    result = read_sqlite_source(make_config(synthetic_sqlite_db, query))
    assert result.columns == [name]
    assert result.rows == [{name: 1}]


def test_comments_and_read_only_cte_remain_supported(
    synthetic_sqlite_db: Path,
) -> None:
    query = (
        "/* DROP is a comment */ WITH sample(marker) AS "
        "(SELECT 'sensor/*A*/B') -- UPDATE is a comment\n"
        "SELECT marker FROM sample"
    )
    result = read_sqlite_source(make_config(synthetic_sqlite_db, query))
    assert result.rows == [{"marker": "sensor/*A*/B"}]


@pytest.mark.parametrize("empty", [False, True])
def test_duplicate_result_names_are_rejected(
    synthetic_sqlite_db: Path, empty: bool
) -> None:
    query = "SELECT asset_id AS value, measurement_value AS value FROM measurements"
    if empty:
        query += " WHERE 0"
    with pytest.raises(SqlSourceError, match="unique.*aliases"):
        read_sqlite_source(make_config(synthetic_sqlite_db, query))


def test_distinct_case_aliases_keep_their_positional_values(
    synthetic_sqlite_db: Path,
) -> None:
    result = read_sqlite_source(
        make_config(synthetic_sqlite_db, "SELECT 1 AS value, 2 AS VALUE")
    )
    assert result.columns == ["value", "VALUE"]
    assert result.rows == [{"value": 1, "VALUE": 2}]


def test_authorizer_rejects_a_write_inside_a_read_query(
    synthetic_sqlite_db: Path,
) -> None:
    connection = sqlite3.connect(synthetic_sqlite_db)
    try:

        def mutate() -> int:
            connection.execute("DELETE FROM measurements")
            return 1

        connection.create_function("mutate", 0, mutate)
        with pytest.raises(SqlSourceError, match="SQLite rejected"):
            execute_read_only_sqlite(connection, "SELECT mutate()")
        assert connection.execute("SELECT COUNT(*) FROM measurements").fetchone() == (
            3,
        )
    finally:
        connection.close()


@pytest.mark.parametrize(
    "query",
    [
        "/* read-looking comment */ WITH sample AS (SELECT 1) DELETE FROM measurements",
        "SELECT 'safe;literal'; DELETE FROM measurements",
        "SELECT 'safe/*literal*/'; SELECT 2",
    ],
)
def test_quoted_contents_do_not_hide_real_unsafe_statements(
    synthetic_sqlite_db: Path, query: str
) -> None:
    connection = sqlite3.connect(synthetic_sqlite_db)
    try:
        with pytest.raises(SqlSourceError):
            execute_read_only_sqlite(connection, query)
        assert connection.execute("SELECT COUNT(*) FROM measurements").fetchone() == (
            3,
        )
    finally:
        connection.close()


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
