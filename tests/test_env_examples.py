# AI contribution: 50% or more AI-generated
"""Example environment files stay separate from real secrets (#32)."""

import fnmatch
import re
from pathlib import Path

import pytest

from app.config import settings
from app.secret_policy import URL_USERINFO, is_credential_key

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [ROOT / ".env.example", ROOT / "frontend" / ".env.example"]
ASSIGNMENT = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")


def assignments(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = ASSIGNMENT.match(line)
        assert match, f"{path.name}: not a NAME=value line: {line!r}"
        values[match[1]] = match[2]
    return values


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: str(p.relative_to(ROOT)))
def test_examples_hold_only_public_placeholders(path: Path):
    values = assignments(path)
    assert values, "an example file must document at least one variable"
    for name, value in values.items():
        assert not is_credential_key(name), f"{name} names a credential"
        assert not URL_USERINFO.search(value), f"{name} embeds URL credentials"


def test_real_env_files_are_ignored_but_examples_are_tracked():
    rules = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in rules and ".env.*" in rules and "!.env.example" in rules


@pytest.mark.parametrize("folder", [ROOT, ROOT / "frontend"])
def test_docker_build_contexts_exclude_env_files(folder: Path):
    """Both contexts are allowlists: '**' first, then explicit inclusions."""
    lines = [
        line.strip()
        for line in (folder / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert lines[0] == "**"
    included = [line[1:] for line in lines if line.startswith("!")]
    for name in (".env", ".env.local", ".env.example"):
        assert not any(fnmatch.fnmatch(name, pattern) for pattern in included)


def test_settings_read_no_credentials_from_the_environment():
    assert not any(is_credential_key(name) for name in type(settings).model_fields)
