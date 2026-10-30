# AI contribution: 50% or more AI-generated
"""Mask credentials and machine paths before text reaches durable run logs (#27)."""

import re

MAX_LENGTH = 512
REDACTED = "[REDACTED]"

# Order matters: URL credentials before key=value pairs, both before paths.
_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s@]+@"), rf"\1{REDACTED}@"),
    (
        re.compile(
            r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)"
            r"(\s*[=:]\s*)\S+"
        ),
        rf"\1\2{REDACTED}",
    ),
    (re.compile(r"(?i)\bbearer\s+\S+"), f"Bearer {REDACTED}"),
    (re.compile(r"\b[A-Za-z]:\\\S*"), "[PATH]"),
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
