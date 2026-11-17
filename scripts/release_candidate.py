#!/usr/bin/env python3
# AI contribution: 50% or more AI-generated
"""Build, run, back up, restore, reset and smoke-test the Release 1 candidate (#36).

Every command drives the repository's compose.yml under one Compose project
name (default ``lps-release``), so it never touches another stack or volume.
Host settings come from ``.env`` (see ``.env.example``) and are validated
before Docker runs. See docs/release-1/candidate.md for the operator guide.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.request import urlopen
from uuid import uuid4

import release_acceptance as acceptance

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = "lps-release"
PROJECT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")
LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
PORT_KEYS = ("API_PORT", "FRONTEND_PORT")
SETTING_KEYS = {*PORT_KEYS, "LPS_LOG_LEVEL"}
DATA_ROOT = "/var/lib/lps"
METADATA = DATA_ROOT + "/metadata.sqlite3"
BACKUP_FORMAT = 1

# Small programs run inside the API image; arguments are passed separately.
READ_SCHEMA = (
    "import sqlite3,sys\n"
    "c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)\n"
    "print(c.execute('SELECT version_num FROM alembic_version').fetchone()[0])"
)
KNOWN_SCHEMAS = (
    "import json\nfrom alembic.script import ScriptDirectory\n"
    "from app.metadata.migrate import migration_config\n"
    "s=ScriptDirectory.from_config(migration_config())\n"
    "print(json.dumps(sorted(r.revision for r in s.walk_revisions())))"
)
WRITE_INPUT = (
    "import pathlib,sys\n"
    "project=(pathlib.Path(sys.argv[1])/sys.argv[2]).resolve()\n"
    "target=(project/sys.argv[3]).resolve()\n"
    "if not target.is_relative_to(project):\n"
    "    raise SystemExit('input path leaves the project folder')\n"
    "target.parent.mkdir(parents=True,exist_ok=True)\n"
    "target.write_bytes(sys.stdin.buffer.read())"
)
RESTORE = f"find {DATA_ROOT} -mindepth 1 -delete && tar -C {DATA_ROOT} -xzf -"

Runner = Callable[[Sequence[str], bytes | None, Mapping[str, str]], bytes]


class CandidateError(RuntimeError):
    """A candidate command could not complete safely."""


@dataclass(frozen=True)
class Config:
    project: str
    settings: dict[str, str]


def parse_env(text: str) -> dict[str, str]:
    settings: dict[str, str] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key.strip():
            raise CandidateError(f"Line {number}: use KEY=VALUE")
        if key.strip() in settings:
            raise CandidateError(f"Line {number}: {key.strip()} is set twice")
        settings[key.strip()] = value.strip()
    return settings


def validate_settings(settings: Mapping[str, str]) -> None:
    unknown = sorted(set(settings) - SETTING_KEYS)
    if unknown:
        raise CandidateError(
            f"Unsupported setting(s) {', '.join(unknown)}. Only "
            f"{', '.join(sorted(SETTING_KEYS))} are candidate settings; "
            "secrets and data paths never belong in .env."
        )
    ports = [settings[key] for key in PORT_KEYS if key in settings]
    for value in ports:
        if not value.isdigit() or not 1 <= int(value) <= 65535:
            raise CandidateError(f"Port {value!r} must be a number from 1 to 65535")
    if len(ports) == 2 and int(ports[0]) == int(ports[1]):
        raise CandidateError("API_PORT and FRONTEND_PORT must differ")
    level = settings.get("LPS_LOG_LEVEL", "INFO")
    if level.upper() not in LOG_LEVELS:
        raise CandidateError(f"LPS_LOG_LEVEL must be one of {sorted(LOG_LEVELS)}")


def load_config(project: str, env_file: Path | None = None) -> Config:
    if not PROJECT_PATTERN.fullmatch(project):
        raise CandidateError("Project names use lowercase letters, digits, - and _")
    path = env_file or ROOT / ".env"
    if env_file is not None and not path.is_file():
        raise CandidateError(f"Settings file {path} does not exist")
    settings = parse_env(path.read_text(encoding="utf-8")) if path.is_file() else {}
    validate_settings(settings)
    return Config(project, settings)


def subprocess_runner(
    args: Sequence[str], data: bytes | None, env: Mapping[str, str]
) -> bytes:
    completed = subprocess.run(
        list(args), input=data, capture_output=True, cwd=ROOT, env=dict(env)
    )
    if completed.returncode:
        detail = completed.stderr.decode(errors="replace")[-2000:]
        raise CandidateError(f"{' '.join(args[2:6])} failed: {detail}")
    return completed.stdout


class Compose:
    """``docker compose`` scoped to one project name and the repo's compose.yml."""

    def __init__(self, config: Config, runner: Runner = subprocess_runner) -> None:
        self.config = config
        self.runner = runner
        self.base = ["docker", "compose", "--project-name", config.project]
        self.base += ["--file", str(ROOT / "compose.yml")]
        self.env = {**os.environ, **config.settings}

    def __call__(self, *args: str, data: bytes | None = None) -> bytes:
        return self.runner([*self.base, *args], data, self.env)

    def text(self, *args: str) -> str:
        return self(*args).decode().strip()

    def up(self, build: bool = False) -> None:
        self(
            "up",
            "--detach",
            "--wait",
            "--wait-timeout",
            "180",
            *(["--build"] if build else []),
        )

    def running(self) -> bool:
        return bool(self.text("ps", "--status", "running", "--quiet", "api"))

    def address(self, service: str, port: int) -> str:
        binding = self.text("port", service, str(port))
        host, _, published = binding.rpartition(":")
        if host != "127.0.0.1" or not published.isdigit():
            raise CandidateError(f"{service} is not published on loopback: {binding}")
        return f"http://127.0.0.1:{published}"

    def api_python(self, code: str, *argv: str, data: bytes | None = None) -> bytes:
        """Run Python in a one-off API container that shares the data volume."""
        one_off = ["run", "--rm", "--no-deps", "-T", "--entrypoint", "python", "api"]
        return self(*one_off, "-c", code, *argv, data=data)

    def volume(self, program: str, *argv: str, data: bytes | None = None) -> bytes:
        one_off = ["run", "--rm", "--no-deps", "-T", "--entrypoint", program, "api"]
        return self(*one_off, *argv, data=data)


def git_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def check_manifest(
    manifest: Mapping[str, object], archive: bytes, known: Sequence[str]
) -> None:
    """Refuse a backup this candidate cannot restore, before any data changes."""
    if manifest.get("format") != BACKUP_FORMAT:
        raise CandidateError("Unsupported backup manifest format")
    if hashlib.sha256(archive).hexdigest() != manifest.get("sha256"):
        raise CandidateError("Backup archive does not match its manifest checksum")
    schema = manifest.get("schema_revision")
    if schema not in known:
        raise CandidateError(
            f"Backup schema {schema} is newer than or unknown to this candidate. "
            "Restore it with the release that created it "
            f"({manifest.get('source_revision')})."
        )


def backup(compose: Compose, output: Path) -> Path:
    """Stop briefly, archive the data volume, write a manifest, restart if needed."""
    was_running = compose.running()
    compose("stop")
    try:
        schema = compose.api_python(READ_SCHEMA, METADATA).decode().strip()
        archive = compose.volume("tar", "-C", DATA_ROOT, "-czf", "-", ".")
    finally:
        if was_running:
            compose.up()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / f"lps-backup-{stamp}.tar.gz"
    manifest_path = archive_path.with_suffix("").with_suffix(".json")
    if archive_path.exists() or manifest_path.exists():
        raise CandidateError(
            f"{archive_path.name} already exists; choose another folder"
        )
    archive_path.write_bytes(archive)
    manifest = {
        "format": BACKUP_FORMAT,
        "created_at": stamp,
        "project": compose.config.project,
        "source_revision": git_revision(),
        "schema_revision": schema,
        "archive": archive_path.name,
        "sha256": hashlib.sha256(archive).hexdigest(),
        "bytes": len(archive),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def restore(compose: Compose, manifest_path: Path, confirmed: bool) -> None:
    """Replace the candidate's data with a verified backup."""
    if not confirmed:
        raise CandidateError("Restore replaces all candidate data; rerun with --yes")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive = (manifest_path.parent / str(manifest.get("archive", ""))).read_bytes()
    known = json.loads(compose.api_python(KNOWN_SCHEMAS))
    check_manifest(manifest, archive, known)
    was_running = compose.running()
    compose("stop")
    compose.volume("sh", "-c", RESTORE, data=archive)
    if was_running:
        compose.up()


def reset(compose: Compose, confirmed: bool) -> None:
    if not confirmed:
        raise CandidateError("Reset deletes all candidate data; rerun with --yes")
    compose("down", "--volumes", "--remove-orphans", "--timeout", "10")


def input_writer(compose: Compose) -> acceptance.WriteInput:
    def write(project_id: str, relative: str, data: bytes) -> None:
        compose(
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            WRITE_INPUT,
            DATA_ROOT + "/workspace",
            project_id,
            relative,
            data=data,
        )

    return write


def verify_health(compose: Compose) -> str:
    """Check the API directly and through the frontend proxy; return the UI URL."""
    frontend = compose.address("frontend", 8080)
    for base in (compose.address("api", 8000), frontend):
        with urlopen(base + "/api/v1/health", timeout=10) as response:  # loopback
            health = json.loads(response.read())
        if health.get("status") != "ok":
            raise CandidateError(f"Unhealthy candidate at {base}: {health}")
    return frontend


def start(compose: Compose) -> dict[str, str]:
    """Build if needed, start, wait for health checks and return the UI URL."""
    compose.up(build=True)
    return {"open": verify_health(compose)}


def demo(compose: Compose) -> dict[str, object]:
    """Load the synthetic Release 1 project into the running candidate."""
    if not compose.running():
        raise CandidateError("Start the candidate first: release_candidate.py start")
    frontend = verify_health(compose)
    send = acceptance.http_sender(frontend)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
    evidence = acceptance.run_acceptance(
        send, input_writer(compose), f"Release 1 demo {stamp}"
    )
    return {"open": f"{frontend}/#/projects", **evidence}


def smoke_steps(
    compose: Compose, scratch: Path, log: Callable[[str], None]
) -> dict[str, object]:
    """Clean install, acceptance, restart, backup, reset and restore, in order."""
    compose.up(build=True)
    send = acceptance.http_sender(verify_health(compose))
    log("clean install: API and frontend proxy healthy")
    evidence = acceptance.run_acceptance(send, input_writer(compose))
    log("acceptance: two runs succeeded and Parquet rows match the oracle")
    compose("down", "--timeout", "10")
    compose.up()
    acceptance.verify_evidence(acceptance.http_sender(verify_health(compose)), evidence)
    log("persistence: project, pipeline, runs and artifact survived recreation")
    manifest = backup(compose, scratch)
    log(f"backup: {manifest.name} written while the stack was running")
    reset(compose, confirmed=True)
    compose.up()
    acceptance.verify_absent(acceptance.http_sender(verify_health(compose)), evidence)
    log("reset: the candidate started empty")
    restore(compose, manifest, confirmed=True)
    acceptance.verify_evidence(acceptance.http_sender(verify_health(compose)), evidence)
    log("restore: the backup brought back every run and output row")
    return evidence


def smoke(report: Path | None, runner: Runner = subprocess_runner) -> dict[str, object]:
    """Rehearse the whole candidate lifecycle in a throwaway, isolated project."""
    project = "lps-rc-smoke-" + uuid4().hex[:12]
    compose = Compose(Config(project, {"API_PORT": "0", "FRONTEND_PORT": "0"}), runner)
    steps: list[str] = []

    def log(step: str) -> None:
        steps.append(step)
        print("PASS " + step, flush=True)

    result: dict[str, object] = {
        "project": project,
        "revision": git_revision(),
        "steps": steps,
    }
    try:
        with tempfile.TemporaryDirectory() as scratch:
            result["evidence"] = smoke_steps(compose, Path(scratch), log)
        result["outcome"] = "passed"
    except Exception as error:
        result["outcome"] = f"failed: {error}"
        raise
    finally:
        compose("down", "--volumes", "--remove-orphans", "--timeout", "10")
        if compose.text("ps", "--all", "--quiet"):
            raise CandidateError("Smoke containers remain after teardown")
        if report is not None:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--project", default=DEFAULT_PROJECT, help="Compose project name")
    cli.add_argument("--env-file", type=Path, help="Settings file (default: .env)")
    commands = cli.add_subparsers(dest="command", required=True)
    for name in ("config", "build", "start", "stop", "status", "demo"):
        commands.add_parser(name)
    commands.add_parser("backup").add_argument(
        "--output", type=Path, default=ROOT / "backups"
    )
    restore_cli = commands.add_parser("restore")
    restore_cli.add_argument("manifest", type=Path)
    restore_cli.add_argument("--yes", action="store_true")
    commands.add_parser("reset").add_argument("--yes", action="store_true")
    commands.add_parser("smoke").add_argument("--report", type=Path)
    return cli


def dispatch(args: argparse.Namespace, compose: Compose) -> object:
    actions: dict[str, Callable[[], object]] = {
        "config": lambda: {
            "project": compose.config.project,
            **compose.config.settings,
        },
        "build": lambda: compose("build"),
        "start": lambda: start(compose),
        "stop": lambda: compose("stop"),
        "status": lambda: compose.text("ps"),
        "demo": lambda: demo(compose),
        "backup": lambda: {"manifest": str(backup(compose, args.output))},
        "restore": lambda: restore(compose, args.manifest, args.yes),
        "reset": lambda: reset(compose, args.yes),
    }
    return actions[args.command]()


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "smoke":
            smoke(args.report)
            print("Smoke stack and its synthetic volume were removed.")
            return 0
        result = dispatch(args, Compose(load_config(args.project, args.env_file)))
    except (CandidateError, acceptance.AcceptanceError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if isinstance(result, (dict, str)):
        print(result if isinstance(result, str) else json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
