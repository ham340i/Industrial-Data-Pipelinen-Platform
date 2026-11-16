"""JSON storage validation without taking ownership of the future DAG contract."""

import json
import re
from typing import Any

from sqlalchemy import JSON
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

from app.secret_policy import HOME_PATH, URL_USERINFO, is_credential_key

# Machine-local bindings. Credential keys come from the shared policy (#32).
_RUNTIME_KEYS = {
    "path",
    "localpath",
    "absolutepath",
    "workspacepath",
    "filepath",
    "outputpath",
    "secretref",
    "secretreference",
}
_ABSOLUTE_PATH = re.compile(r"^(?:[/\\]|[A-Za-z]:|file:)", re.IGNORECASE)


def portable_definition(value: dict[str, Any]) -> dict[str, Any]:
    """Return detached JSON; reject runtime fields, credentials and machine paths.

    Rejects credential keys (shared policy), absolute and home-relative paths,
    and URLs that embed userinfo (``scheme://user:password@host``). This does
    not validate graph topology or detect arbitrary secret strings.
    Logical resource IDs belong in definitions; local bindings are separate.
    """
    if not isinstance(value, dict):
        raise ValueError("A portable definition must be a JSON object")

    def visit(item: object) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ValueError("JSON object keys must be strings")
                normalized = re.sub(r"[^a-z0-9]", "", key.lower())
                if normalized in _RUNTIME_KEYS or is_credential_key(key):
                    raise ValueError("Runtime bindings do not belong in definitions")
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, str):
            if _ABSOLUTE_PATH.match(item) or HOME_PATH.match(item):
                raise ValueError("Absolute paths do not belong in definitions")
            if URL_USERINFO.search(item):
                raise ValueError("Credentials do not belong in definitions")
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
