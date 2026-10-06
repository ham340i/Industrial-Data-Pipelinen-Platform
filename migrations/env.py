"""Use the application connection so SQLite DDL shares its transaction policy."""

from alembic import context
from sqlalchemy.engine import Connection

from app.config import settings
from app.metadata.database import Database
from app.metadata.models import Base

config = context.config


def run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        compare_type=True,
        render_as_batch=True,
        transactional_ddl=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Use online migrations against a configured local SQLite file")
elif "connection" in config.attributes:
    run(config.attributes["connection"])
else:
    database = Database(settings.metadata_path)
    try:
        with database.engine.begin() as connection:
            run(connection)
    finally:
        database.close()
