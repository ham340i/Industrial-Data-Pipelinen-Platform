"""JSON storage validation without taking ownership of the future DAG contract."""

import json
import re
from typing import Any

from sqlalchemy import JSON
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

_RUNTIME_KEYS = {
    "path",
    "localpath",
    "absolutepath",
    "workspacepath",
    "filepath",
    "outputpath",
    "secret",
    "secrets",
    "secretref",
    "secretreference",
    "password",
    "credentials",
    "credential",
    "apikey",
    "token",
    "accesstoken",
    "connectionstring",
    "dsn",
}
_ABSOLUTE_PATH = re.compile(r"^(?:[/\\]|[A-Z]:|file:)", re.IGNORECASE)


def portable_definition_validator(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("A portable definition must be a JSON object")


def check_key_is_string(key: Any) -> None:
    if not isinstance(key, str):
        raise ValueError("JSON object keys must be strings")


def check_runtime_location(keys: str) -> None:
    if keys in _RUNTIME_KEYS:
        raise ValueError("Runtime bindings do not belong in definitions")


def check_absolute_path_in_path(item: str) -> None:
    if _ABSOLUTE_PATH.match(item):
        raise ValueError("Absolute paths do not belong in definitions")


def portable_definition(value: dict[str, Any]) -> dict[str, Any]:
    """Return detached JSON; reject known runtime fields and absolute paths.

    This does not validate graph topology or detect arbitrary secret strings.
    Logical resource IDs belong in definitions; local bindings are separate.
    """
    portable_definition_validator(value)

    def visit(item: object) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                check_key_is_string(key)
                normalized = re.sub(r"[^a-z0-9]", "", key.lower())
                check_runtime_location(normalized)
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, str):
            check_absolute_path_in_path(item)
        elif item is not None and not isinstance(item, (bool, int, float)):
            raise ValueError("Definitions accept only JSON values")

    # Serialize first to reject cycles and non-finite numbers. Visit the original
    # too: json.dumps otherwise silently converts tuples and integer keys.
    serialized = json.dumps(value, allow_nan=False)
    visit(value)
    detached: dict[str, Any] = json.loads(serialized)
    return detached


class PortableJSON(TypeDecorator[dict[str, Any]]):
    """Apply the same portability boundary to ORM and Core SQL writes."""

    impl = JSON
    cache_ok = True

    def process_bind_param(
        self, value: dict[str, Any] | None, dialect: Dialect
    ) -> dict[str, Any] | None:
        if value is None:
            raise ValueError("A portable definition must be a JSON object")
        return portable_definition(value)
