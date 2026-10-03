"""Controlled tests of the harness: a broken fixture must fail each backend check.

Each test writes a synthetic fixture to a temporary directory, runs the real tool
in a subprocess and asserts that it reports the failure with a non-zero exit
code. A passing control proves the tool was able to run at all.
"""

import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def run_tool(*arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_pytest_fails_on_failing_test(tmp_path: Path):
    (tmp_path / "test_passing.py").write_text(
        "def test_control():\n    assert 1 + 1 == 2\n", encoding="utf-8"
    )
    (tmp_path / "test_failing.py").write_text(
        "def test_broken():\n    assert 1 + 1 == 3\n", encoding="utf-8"
    )
    isolated = ("pytest", "-q", "-c", "/dev/null", "-p", "no:cacheprovider")

    control = run_tool(*isolated, "test_passing.py", cwd=tmp_path)
    broken = run_tool(*isolated, "test_failing.py", cwd=tmp_path)

    assert control.returncode == 0, control.stdout
    assert broken.returncode == 1, broken.stdout
    assert "1 failed" in broken.stdout


def test_pytest_fails_when_no_tests_are_collected(tmp_path: Path):
    result = run_tool(
        "pytest", "-q", "-c", "/dev/null", "-p", "no:cacheprovider", cwd=tmp_path
    )

    assert result.returncode == 5, result.stdout


def test_ruff_fails_on_lint_violation(tmp_path: Path):
    config = str(REPOSITORY_ROOT / "pyproject.toml")
    clean = tmp_path / "clean.py"
    clean.write_text("VALUE = 1\n", encoding="utf-8")
    violating = tmp_path / "violating.py"
    violating.write_text("import os\n", encoding="utf-8")
    command = ("ruff", "check", "--config", config, "--no-cache")

    control = run_tool(*command, str(clean), cwd=tmp_path)
    broken = run_tool(*command, str(violating), cwd=tmp_path)

    assert control.returncode == 0, control.stdout
    assert broken.returncode == 1, broken.stdout
    assert "F401" in broken.stdout


def test_ruff_format_check_fails_on_unformatted_source(tmp_path: Path):
    config = str(REPOSITORY_ROOT / "pyproject.toml")
    unformatted = tmp_path / "unformatted.py"
    unformatted.write_text("value   =  {'key':1}\n", encoding="utf-8")

    result = run_tool(
        "ruff",
        "format",
        "--check",
        "--config",
        config,
        "--no-cache",
        str(unformatted),
        cwd=tmp_path,
    )

    assert result.returncode == 1, result.stdout
    assert "would be reformatted" in result.stdout


def test_mypy_fails_on_type_error(tmp_path: Path):
    config = str(REPOSITORY_ROOT / "pyproject.toml")
    typed = tmp_path / "typed.py"
    typed.write_text(
        "def double(value: int) -> int:\n    return value * 2\n", encoding="utf-8"
    )
    mistyped = tmp_path / "mistyped.py"
    mistyped.write_text(
        'def double(value: int) -> int:\n    return "not a number"\n',
        encoding="utf-8",
    )
    command = ("mypy", "--config-file", config, "--no-incremental")

    control = run_tool(*command, str(typed), cwd=tmp_path)
    broken = run_tool(*command, str(mistyped), cwd=tmp_path)

    assert control.returncode == 0, control.stdout
    assert broken.returncode == 1, broken.stdout
    assert "return-value" in broken.stdout
