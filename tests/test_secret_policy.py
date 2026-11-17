# AI contribution: 50% or more AI-generated
"""Shared credential-key policy across SDK, storage and SQL boundaries (#32)."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.blocks.contracts import PublicValueError, require_public_json
from app.metadata.portable import portable_definition
from app.secret_policy import is_credential_key
from app.sources.sql import SqlSourceConfig

COMPOUND_KEYS = [
    "client_secret",
    "db_password",
    "DB-Password",
    "github_token",
    "refresh_token",
    "private_key",
    "aws_secret_access_key",
    "x-api-key",
    "ssh_passphrase",
    "service_credentials",
    "jdbc_connection_string",
]
EXACT_KEYS = ["password", "token", "secret", "dsn", "username", "pwd", "Authorization"]
PUBLIC_KEYS = [
    "resource_ref",
    "parameters_json",
    "max_bytes",
    "null_value",
    "value_text",
    "columns",
    "tokenizer",
    "secretary_name",
    "user",
]


@pytest.mark.parametrize("key", COMPOUND_KEYS + EXACT_KEYS)
def test_credential_keys_are_recognized(key: str):
    assert is_credential_key(key)


@pytest.mark.parametrize("key", PUBLIC_KEYS)
def test_public_configuration_keys_are_not_flagged(key: str):
    assert not is_credential_key(key)


@pytest.mark.parametrize("key", COMPOUND_KEYS)
def test_every_boundary_rejects_compound_credential_keys(key: str):
    nested = {"outer": [{key: "SYNTHETIC_SENTINEL"}]}
    with pytest.raises(PublicValueError):
        require_public_json(nested)
    with pytest.raises(ValueError, match="Runtime bindings"):
        portable_definition(nested)
    with pytest.raises(ValidationError, match="credential-like parameters"):
        SqlSourceConfig.model_validate(
            {
                "database_path": "synthetic.sqlite3",
                "query": "SELECT 1 AS one",
                "parameters": {key: "SYNTHETIC_SENTINEL"},
            }
        )


@pytest.mark.parametrize(
    "value",
    [
        "postgresql://operator:SYNTHETIC@db.example/plant",
        "https://token@example.invalid/data.csv",
        "mysql://user@localhost/plant",
    ],
)
def test_definitions_reject_urls_with_userinfo(value: str):
    with pytest.raises(ValueError, match="Credentials"):
        portable_definition({"source": value})


@pytest.mark.parametrize("value", ["~", "~/data.csv", "~operator/inputs", "~\\in.csv"])
def test_definitions_reject_home_relative_paths(value: str):
    with pytest.raises(ValueError, match="Absolute paths"):
        portable_definition({"source": value})


@pytest.mark.parametrize(
    "value",
    [
        "inputs/readings.csv",
        "https://example.invalid/docs",
        "operator@example.invalid",
        "~ approximately 5",
        "SELECT a FROM t WHERE b = :b",
    ],
)
def test_definitions_keep_public_strings(value: str):
    definition: dict[str, Any] = {"note": value}
    assert portable_definition(definition) == definition
