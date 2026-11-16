# AI contribution: 50% or more AI-generated
"""Log redaction for persisted run evidence (#27)."""

import pytest

from app.runs.redaction import MAX_LENGTH, redact, redact_optional


@pytest.mark.parametrize(
    "raw,leak,expected",
    [
        ("password=hunter2 failed", "hunter2", "password=[REDACTED] failed"),
        ("API_KEY: abc123", "abc123", "API_KEY: [REDACTED]"),
        ("token=xyz;", "xyz", "token=[REDACTED]"),
        (
            "connect postgres://admin:pw@db:5432/x",
            "admin:pw",
            "connect postgres://[REDACTED]@db:5432/x",
        ),
        (
            "Authorization Bearer eyJabc.def",
            "eyJabc",
            "Authorization Bearer [REDACTED]",
        ),
        ("read /home/alice/data.csv now", "/home/alice", "read [PATH] now"),
        ("read C:\\Users\\bob\\in.csv", "bob", "read [PATH]"),
        ("read C:/Users/Alice/private.csv", "Alice", "read [PATH]"),
        (
            '{"password": "synthetic-secret"}',
            "synthetic-secret",
            '{"password": "[REDACTED]"}',
        ),
        (
            "password='synthetic secret'",
            "synthetic secret",
            "password=[REDACTED]",
        ),
    ],
)
def test_secrets_and_machine_paths_are_masked(raw: str, leak: str, expected: str):
    result = redact(raw)
    assert leak not in result
    assert result == expected


@pytest.mark.parametrize(
    "raw,leaks",
    [
        # The opposite quote type inside the quoted value (#27 follow-up).
        ('{"password": "synthetic\'secret"}', ["synthetic'secret", "secret"]),
        ('password="synthetic\' secret"', ["synthetic' secret", "secret"]),
        ("{'password': 'synthetic\" secret'}", ['synthetic" secret', "secret"]),
        # An escaped matching quote inside the quoted value.
        ('{"password": "synthetic\\" secret"}', ["synthetic", "secret"]),
        ("password='synthetic\\' secret'", ["synthetic", "secret"]),
        # Whitespace alone, inside matching quotes, must not short-circuit.
        ('token="a b c"', ["a b c"]),
        # Key and value use different quote styles (#27 second follow-up).
        ("{\"password\": 'synthetic-secret'}", ["synthetic-secret"]),
        ("{'password': \"synthetic-secret\"}", ["synthetic-secret"]),
    ],
)
def test_quoted_values_with_embedded_or_escaped_quotes_are_fully_masked(
    raw: str, leaks: list[str]
):
    result = redact(raw)
    for leak in leaks:
        assert leak not in result
    assert "[REDACTED]" in result


@pytest.mark.parametrize(
    "raw,leak,expected",
    [
        # Compound keys ending with a credential word (#32).
        ("client_secret=abc123", "abc123", "client_secret=[REDACTED]"),
        ("db_password=hunter2 rejected", "hunter2", "db_password=[REDACTED] rejected"),
        ("access_token=xyz", "xyz", "access_token=[REDACTED]"),
        ("refresh_token: xyz", "xyz", "refresh_token: [REDACTED]"),
        ("aws_secret_access_key=AKIA0", "AKIA0", "aws_secret_access_key=[REDACTED]"),
        ("ssh_passphrase=open sesame", "open", "ssh_passphrase=[REDACTED] sesame"),
        ("private_key=BEGIN0", "BEGIN0", "private_key=[REDACTED]"),
        (
            '{"db_password": "synthetic-secret"}',
            "synthetic-secret",
            '{"db_password": "[REDACTED]"}',
        ),
        (
            "{'client_secret': 'synthetic-secret'}",
            "synthetic-secret",
            "{'client_secret': \"[REDACTED]\"}",
        ),
        # Non-Bearer Authorization schemes; Basic is reversible user:password.
        (
            "Authorization: Basic dXNlcjpwYXNz",
            "dXNlcjpwYXNz",
            "Authorization: Basic [REDACTED]",
        ),
        (
            "proxy-authorization=Digest abc123",
            "abc123",
            "proxy-authorization=Digest [REDACTED]",
        ),
        (
            "Authorization: Token t0k3n",
            "t0k3n",
            "Authorization: Token [REDACTED]",
        ),
    ],
)
def test_compound_keys_and_auth_schemes_are_masked(raw: str, leak: str, expected: str):
    result = redact(raw)
    assert leak not in result
    assert result == expected
    assert redact(result) == result


@pytest.mark.parametrize(
    "text",
    [
        "tokenizer=word split failed",
        "secret_name: plant-a",
        "basic validation failed for column token_count",
        "Authorization header missing",
    ],
)
def test_lookalike_words_are_not_redacted(text: str):
    assert redact(text) == text


def test_relative_names_and_ordinary_text_are_kept():
    text = "Node join: column value missing in data/input.csv"
    assert redact(text) == text


def test_redaction_is_idempotent():
    once = redact("password=a at /tmp/x/y")
    assert redact(once) == once


def test_output_is_bounded_single_line_and_never_empty():
    long = redact("x" * (MAX_LENGTH * 2))
    assert len(long) == MAX_LENGTH and long.endswith("…")
    assert redact("line one\n\tline two") == "line one line two"
    assert redact("   ") == "No details recorded."
    assert redact_optional(None) is None
