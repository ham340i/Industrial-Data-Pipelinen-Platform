"""File-backed SQLite connections and short, atomic session lifetimes."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, Connection, Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry


def configure_connection(connection: object, record: ConnectionPoolEntry) -> None:
    dbapi = cast(sqlite3.Connection, connection)
    # SQLAlchemy owns BEGIN, including DDL; pysqlite legacy mode does not.
    dbapi.isolation_level = None
    with dbapi:
        cursor = dbapi.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()


def begin_transaction(connection: Connection) -> None:
    connection.exec_driver_sql("BEGIN")


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(
            URL.create("sqlite", database=str(self.path)),
            connect_args={"check_same_thread": False, "timeout": 5},
        )
        event.listen(self.engine, "connect", configure_connection)
        event.listen(self.engine, "begin", begin_transaction)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        """Commit the whole unit of work, or roll it back and close the session."""
        with self.sessions.begin() as session:
            yield session

    def close(self) -> None:
        self.engine.dispose()
