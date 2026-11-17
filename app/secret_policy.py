# AI contribution: 50% or more AI-generated
"""One credential-key policy for every portable configuration boundary (#32).

Block configuration, saved pipeline definitions and the standalone SQL source
each used to keep their own exact-match list, so compound names such as
``client_secret``, ``db_password`` or ``github_token`` passed all three.
Keys are normalized (lowercase, alphanumerics only) and rejected when they
equal a known credential name or end with a strong credential word.

This is a key-name policy, not a detector for secret *values* stored under
otherwise public names; see docs/security/security-plan.md.
"""

from __future__ import annotations

import re

# Names that are credentials only as a whole word ("user" alone is not here:
# it is too common in public configuration; the SQL source adds it locally).
_EXACT = frozenset({"dsn", "username", "pwd", "authorization", "cookie"})

# Any key ending with one of these is treated as carrying a credential.
_SUFFIXES = (
    "password",
    "passwd",
    "passphrase",
    "secret",
    "secrets",
    "token",
    "apikey",
    "accesskey",
    "privatekey",
    "credential",
    "credentials",
    "connectionstring",
)

# scheme://user[:password]@host — userinfo in any configured string value.
URL_USERINFO = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^/\s?#@]+@")
# ~/..., ~user/... or a bare ~: home-relative machine paths.
HOME_PATH = re.compile(r"^~[\w.-]*(?:[/\\]|$)")


def normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def is_credential_key(key: str) -> bool:
    """Whether a configuration key names a credential under the shared policy."""
    normalized = normalize_key(key)
    return normalized in _EXACT or normalized.endswith(_SUFFIXES)
