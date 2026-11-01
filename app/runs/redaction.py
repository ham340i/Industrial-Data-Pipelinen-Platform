# AI contribution: 50% or more AI-generated
"""Mask credentials and machine paths before text reaches durable run logs (#27)."""

import re

MAX_LENGTH = 512
REDACTED = "[REDACTED]"


def _quoted(delimiter: str) -> str:
    """A <delimiter>-quoted string: escaped chars and the *other* quote are
    content, not terminators - only an unescaped matching delimiter closes it.
    """
    return rf"{delimiter}(?:\\.|[^{delimiter}\\])*{delimiter}"


_DQ = _quoted('"')
_SQ = _quoted("'")

# Order matters: URL credentials before key=value pairs, both before paths.
_KEY = r"password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key"
_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s@]+@"), rf"\1{REDACTED}@"),
    # JSON/dict-style quoted keys, e.g. {"password": "secret"} or 'token': 'x'.
    # Kept delimiter-specific (not a shared [\"'] class) so quotes of the
    # *other* kind, and escaped quotes, stay inside the matched value.
    (re.compile(rf'(?i)"({_KEY})"(\s*:\s*){_DQ}'), rf'"\1"\2"{REDACTED}"'),
    (re.compile(rf"(?i)'({_KEY})'(\s*:\s*){_SQ}"), rf"'\1'\2'{REDACTED}'"),
    # Bare key=value / key: value, where the value may be quoted (so it can
    # contain whitespace, the other quote type, or escaped quotes) or a
    # plain unquoted token.
    (
        re.compile(rf"(?i)\b({_KEY})(\s*[=:]\s*)(?:{_DQ}|{_SQ}|\S+)"),
        rf"\1\2{REDACTED}",
    ),
    (re.compile(r"(?i)\bbearer\s+\S+"), f"Bearer {REDACTED}"),
    (re.compile(r"\b[A-Za-z]:[\\/]\S*"), "[PATH]"),
    (re.compile(r"(?<![\w:/.])/(?:[^\s/]+/)*[^\s/]+"), "[PATH]"),
)


def redact(text: str) -> str:
    """Return text that is safe to persist and show to operators."""
    for pattern, replacement in _RULES:
        text = pattern.sub(replacement, text)
    text = " ".join(text.split())
    if len(text) > MAX_LENGTH:
        text = text[: MAX_LENGTH - 1] + "…"
    return text or "No details recorded."


def redact_optional(text: str | None) -> str | None:
    return None if text is None else redact(text)
