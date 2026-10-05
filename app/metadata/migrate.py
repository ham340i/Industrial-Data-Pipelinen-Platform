"""Explicit schema operations shared by API startup, developers and tests."""

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import settings
from app.metadata.database import Database

ROOT = Path(__file__).resolve().parents[2]


def migration_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    # ConfigParser treats percent signs specially; Windows paths may contain %.
    config.set_main_option(
        "script_location", str(ROOT / "migrations").replace("%", "%%")
    )
    return config


def upgrade(database: Database) -> None:
    config = migration_config()
    with database.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def downgrade(database: Database) -> None:
    """Destructive development reset; callers must use a disposable database."""
    config = migration_config()
    with database.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")


def check(database: Database) -> None:
    config = migration_config()
    with database.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.check(config)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("upgrade", "check", "downgrade"))
    parser.add_argument("--confirm-data-loss", action="store_true")
    args = parser.parse_args()
    if args.operation == "downgrade" and not args.confirm_data_loss:
        parser.error(
            "downgrade deletes metadata; use --confirm-data-loss on disposable data"
        )
    database = Database(settings.metadata_path)
    try:
        {"upgrade": upgrade, "check": check, "downgrade": downgrade}[args.operation](
            database
        )
    finally:
        database.close()


if __name__ == "__main__":
    main()
