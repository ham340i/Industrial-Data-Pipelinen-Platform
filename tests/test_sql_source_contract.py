from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.sources.sql import SqlSourceConfig


def test_valid_sqlite_source_config_is_accepted() -> None:
    config = SqlSourceConfig.model_validate(
        {
            "dialect": "sqlite",
            "database_path": "tests/fixtures/sql/synthetic.sqlite3",
            "read_only": True,
            "query": ("SELECT asset_id FROM measurements WHERE asset_id = :asset_id"),
            "parameters": {"asset_id": 1001},
        }
    )

    assert config.dialect == "sqlite"
    assert config.read_only is True
    assert config.parameters == {"asset_id": 1001}


@pytest.mark.parametrize(
    "credential_key",
    ["username", "password", "secret", "token", "api_key"],
)
def test_credentials_are_rejected_from_portable_config(
    credential_key: str,
) -> None:
    with pytest.raises(
        ValidationError,
        match="credential-like parameters are not allowed",
    ):
        SqlSourceConfig.model_validate(
            {
                "database_path": "synthetic.sqlite3",
                "query": "SELECT asset_id FROM measurements",
                "parameters": {credential_key: "not-permitted"},
            }
        )


@pytest.mark.parametrize(
    "query",
    [
        "INSERT INTO measurements VALUES (1, 'x')",
        "UPDATE measurements SET asset_id = 2",
        "DELETE FROM measurements",
        "DROP TABLE measurements",
        "ALTER TABLE measurements ADD COLUMN extra TEXT",
        "SELECT asset_id FROM measurements; DELETE FROM measurements",
    ],
)
def test_write_and_multiple_statement_queries_are_rejected(
    query: str,
) -> None:
    with pytest.raises(ValidationError):
        SqlSourceConfig.model_validate(
            {
                "database_path": "synthetic.sqlite3",
                "query": query,
            }
        )


def test_non_sqlite_dialect_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SqlSourceConfig.model_validate(
            {
                "dialect": "postgresql",
                "database_path": "synthetic.sqlite3",
                "query": "SELECT asset_id FROM measurements",
            }
        )


def test_extra_configuration_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        SqlSourceConfig.model_validate(
            {
                "database_path": "synthetic.sqlite3",
                "query": "SELECT asset_id FROM measurements",
                "username": "unexpected",
            }
        )


def test_read_only_must_be_true() -> None:
    with pytest.raises(ValidationError):
        SqlSourceConfig.model_validate(
            {
                "database_path": "synthetic.sqlite3",
                "read_only": False,
                "query": "SELECT asset_id FROM measurements",
            }
        )
