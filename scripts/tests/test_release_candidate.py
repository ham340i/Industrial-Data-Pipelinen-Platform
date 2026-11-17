# AI contribution: 50% or more AI-generated
"""Release candidate configuration, data safety and failure handling (#36).

A fake Docker runner records every Compose command, so these checks prove
what each command would run (and, as important, what it refuses to run)
without Docker. The real lifecycle runs in CI through ``smoke``.
"""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import release_candidate as rc  # noqa: E402

ARCHIVE = b"synthetic archive bytes"


class FakeDocker:
    """Answers Compose commands from a table and records them in order."""

    def __init__(self, running=True, schema=b"0004\n", known=("0001", "0004")):
        self.calls = []
        self.answers = {
            ("ps", "--status"): b"api-container\n" if running else b"",
            ("ps", "--all"): b"",
            ("tar",): ARCHIVE,
            (rc.READ_SCHEMA,): schema,
            (rc.KNOWN_SCHEMAS,): json.dumps(list(known)).encode(),
        }

    def __call__(self, args, data, env):
        command = list(args[6:])  # drop: docker compose --project-name X --file Y
        self.calls.append(command)
        for key, answer in self.answers.items():
            if all(part in command for part in key):
                return answer
        return b""

    def ran(self, *parts):
        return any(all(part in call for part in parts) for call in self.calls)


def compose(docker, project="lps-release"):
    return rc.Compose(rc.Config(project, {}), docker)


class ConfigurationTests(unittest.TestCase):
    def load(self, text, project="lps-release"):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "candidate.env"
            path.write_text(text, encoding="utf-8")
            return rc.load_config(project, path)

    def test_documented_example_is_a_valid_candidate_configuration(self):
        config = rc.load_config("lps-release", rc.ROOT / ".env.example")
        self.assertEqual(config.settings["API_PORT"], "8000")
        self.assertEqual(config.settings["FRONTEND_PORT"], "3000")

    def test_every_accepted_setting_is_consumed_by_compose(self):
        compose_file = (rc.ROOT / "compose.yml").read_text(encoding="utf-8")
        for key in sorted(rc.SETTING_KEYS):
            with self.subTest(key=key):
                self.assertIn("${" + key, compose_file)
        api_env = json.loads(compose_file)["services"]["api"]["environment"]
        self.assertEqual(api_env["LPS_LOG_LEVEL"], "${LPS_LOG_LEVEL:-INFO}")

    def test_log_level_setting_is_accepted(self):
        config = self.load("API_PORT=8100\nFRONTEND_PORT=3100\nLPS_LOG_LEVEL=debug\n")
        self.assertEqual(config.settings["LPS_LOG_LEVEL"], "debug")

    def test_unknown_settings_are_refused_so_secrets_stay_out(self):
        with self.assertRaisesRegex(rc.CandidateError, "DB_PASSWORD"):
            self.load("API_PORT=8000\nDB_PASSWORD=hunter2\n")

    def test_invalid_ports_are_refused(self):
        for text in ("API_PORT=0", "API_PORT=65536", "API_PORT=80a", "FRONTEND_PORT="):
            with self.subTest(text=text), self.assertRaisesRegex(rc.CandidateError, "Port"):
                self.load(text)

    def test_the_two_services_cannot_share_a_port(self):
        with self.assertRaisesRegex(rc.CandidateError, "must differ"):
            self.load("API_PORT=8000\nFRONTEND_PORT=8000\n")

    def test_malformed_and_duplicate_lines_name_their_line(self):
        with self.assertRaisesRegex(rc.CandidateError, "Line 2: use KEY=VALUE"):
            self.load("# comment\nAPI_PORT\n")
        with self.assertRaisesRegex(rc.CandidateError, "Line 2: API_PORT is set twice"):
            self.load("API_PORT=8000\nAPI_PORT=8001\n")

    def test_unknown_log_level_is_refused(self):
        with self.assertRaisesRegex(rc.CandidateError, "LPS_LOG_LEVEL"):
            self.load("LPS_LOG_LEVEL=LOUD\n")

    def test_project_names_cannot_escape_the_compose_namespace(self):
        for name in ("", "Release", "-x", "a/b", "x" * 64):
            with self.subTest(name=name), self.assertRaises(rc.CandidateError):
                rc.load_config(name, rc.ROOT / ".env.example")

    def test_a_named_settings_file_must_exist(self):
        with self.assertRaisesRegex(rc.CandidateError, "does not exist"):
            rc.load_config("lps-release", rc.ROOT / "missing.env")

    def test_cli_reports_configuration_errors_without_a_traceback(self):
        with patch("sys.stderr") as stderr:
            code = rc.main(["--project", "Bad Name", "config"])
        self.assertEqual(code, 1)
        self.assertIn("lowercase", "".join(c.args[0] for c in stderr.write.call_args_list))


class ManifestTests(unittest.TestCase):
    def manifest(self, **changes):
        base = {
            "format": 1,
            "sha256": hashlib.sha256(ARCHIVE).hexdigest(),
            "schema_revision": "0004",
            "source_revision": "abc123",
        }
        return {**base, **changes}

    def test_matching_backup_is_accepted(self):
        rc.check_manifest(self.manifest(), ARCHIVE, ["0001", "0004"])

    def test_tampered_archive_is_refused(self):
        manifest = self.manifest()
        with self.assertRaisesRegex(rc.CandidateError, "checksum"):
            rc.check_manifest(manifest, ARCHIVE + b"!", ["0004"])

    def test_backup_from_a_newer_schema_points_to_its_release(self):
        manifest = self.manifest(schema_revision="0009")
        with self.assertRaisesRegex(rc.CandidateError, "newer than or unknown.*abc123"):
            rc.check_manifest(manifest, ARCHIVE, ["0004"])

    def test_unknown_manifest_format_is_refused(self):
        manifest = self.manifest(format=2)
        with self.assertRaisesRegex(rc.CandidateError, "format"):
            rc.check_manifest(manifest, ARCHIVE, ["0004"])


class DataSafetyTests(unittest.TestCase):
    def test_reset_requires_confirmation_and_runs_nothing_without_it(self):
        docker = FakeDocker()
        candidate = compose(docker)
        with self.assertRaisesRegex(rc.CandidateError, "--yes"):
            rc.reset(candidate, confirmed=False)
        self.assertEqual(docker.calls, [])

    def test_confirmed_reset_removes_only_this_projects_volumes(self):
        docker = FakeDocker()
        rc.reset(compose(docker), confirmed=True)
        self.assertEqual(docker.calls, [["down", "--volumes", "--remove-orphans", "--timeout", "10"]])

    def test_backup_writes_a_verifiable_manifest_and_restarts_a_running_stack(self):
        docker = FakeDocker(running=True)
        with tempfile.TemporaryDirectory() as folder:
            manifest_path = rc.backup(compose(docker), Path(folder))
            manifest = json.loads(manifest_path.read_text())
            archive = (manifest_path.parent / manifest["archive"]).read_bytes()
        self.assertEqual(archive, ARCHIVE)
        self.assertEqual(manifest["schema_revision"], "0004")
        rc.check_manifest(manifest, archive, ["0004"])
        self.assertLess(docker.calls.index(["stop"]), next(i for i, c in enumerate(docker.calls) if "tar" in c))
        self.assertEqual(docker.calls[-1][0], "up")

    def test_backup_leaves_a_stopped_stack_stopped(self):
        docker = FakeDocker(running=False)
        with tempfile.TemporaryDirectory() as folder:
            rc.backup(compose(docker), Path(folder))
        self.assertFalse(docker.ran("up"))

    def write_backup(self, folder, **changes):
        manifest = {
            "format": 1,
            "archive": "b.tar.gz",
            "sha256": hashlib.sha256(ARCHIVE).hexdigest(),
            "schema_revision": "0004",
            **changes,
        }
        (folder / "b.tar.gz").write_bytes(ARCHIVE)
        (folder / "b.json").write_text(json.dumps(manifest))
        return folder / "b.json"

    def test_restore_refuses_a_bad_backup_before_stopping_or_deleting(self):
        docker = FakeDocker()
        with tempfile.TemporaryDirectory() as folder:
            path = self.write_backup(Path(folder), sha256="0" * 64)
            candidate = compose(docker)
            with self.assertRaisesRegex(rc.CandidateError, "checksum"):
                rc.restore(candidate, path, confirmed=True)
        self.assertFalse(docker.ran("stop"))
        self.assertFalse(docker.ran(rc.RESTORE))

    def test_restore_requires_confirmation(self):
        docker = FakeDocker()
        with tempfile.TemporaryDirectory() as folder:
            path = self.write_backup(Path(folder))
            candidate = compose(docker)
            with self.assertRaisesRegex(rc.CandidateError, "--yes"):
                rc.restore(candidate, path, confirmed=False)
        self.assertEqual(docker.calls, [])

    def test_restore_streams_the_verified_archive_into_the_stopped_volume(self):
        docker = FakeDocker(running=True)
        streamed = []
        original = docker.__call__

        def record(args, data, env):
            if rc.RESTORE in args:
                streamed.append(data)
            return original(args, data, env)

        with tempfile.TemporaryDirectory() as folder:
            path = self.write_backup(Path(folder))
            rc.restore(compose(record), path, confirmed=True)
        self.assertEqual(streamed, [ARCHIVE])
        stop = docker.calls.index(["stop"])
        self.assertLess(stop, next(i for i, c in enumerate(docker.calls) if rc.RESTORE in c))


class RollbackTests(unittest.TestCase):
    """Ahmad's review of PR #106: restore must use the checked-out revision."""

    write_backup = DataSafetyTests.write_backup

    def position(self, docker, *parts):
        return next(i for i, call in enumerate(docker.calls) if all(p in call for p in parts))

    def test_restore_builds_before_checking_schemas_and_recreates_on_restart(self):
        docker = FakeDocker(running=True)
        with tempfile.TemporaryDirectory() as folder:
            path = self.write_backup(Path(folder))
            rc.restore(compose(docker), path, confirmed=True)
        build = docker.calls.index(["build"])
        self.assertLess(build, self.position(docker, rc.KNOWN_SCHEMAS))
        self.assertLess(build, docker.calls.index(["stop"]))
        self.assertIn("--force-recreate", docker.calls[-1])

    def test_schema_unknown_to_the_rebuilt_image_is_refused_before_stopping(self):
        docker = FakeDocker(known=("0001", "0002", "0003"))
        with tempfile.TemporaryDirectory() as folder:
            path = self.write_backup(Path(folder))
            candidate = compose(docker)
            with self.assertRaisesRegex(rc.CandidateError, "newer than or unknown"):
                rc.restore(candidate, path, confirmed=True)
        self.assertTrue(docker.ran("build"))
        self.assertFalse(docker.ran("stop"))

    def rehearse(self, docker):
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(rc, "verify_health", return_value="http://127.0.0.1:3000"), \
                patch.object(rc.acceptance, "verify_evidence") as verify:
            older = self.write_backup(Path(folder))
            rc.rehearse_rollback(compose(docker), Path(folder), older, {})
        return verify

    def test_rollback_rehearsal_refuses_newer_data_then_restores_the_older_backup(self):
        docker = FakeDocker(running=False, schema=b"9999_newer_release\n")
        verify = self.rehearse(docker)
        stamp = self.position(docker, rc.STAMP_SCHEMA)
        self.assertEqual(docker.calls[stamp][-2:], [rc.METADATA, "9999_newer_release"])
        restores = [i for i, call in enumerate(docker.calls) if rc.RESTORE in call]
        self.assertEqual(len(restores), 1)
        self.assertGreater(restores[0], stamp)
        self.assertEqual(docker.calls[-1][0], "up")
        verify.assert_called_once()

    def test_rollback_rehearsal_fails_if_newer_data_is_accepted(self):
        docker = FakeDocker(running=False, schema=b"9999_newer_release\n",
                            known=("0004", "9999_newer_release"))
        with self.assertRaisesRegex(rc.CandidateError, "newer schema was restored"):
            self.rehearse(docker)


class SmokeTests(unittest.TestCase):
    def test_smoke_tears_down_and_reports_even_when_acceptance_fails(self):
        docker = FakeDocker()
        failure = rc.acceptance.AcceptanceError("Run ended failed")
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(rc, "verify_health", return_value="http://127.0.0.1:3000"), \
                patch.object(rc.acceptance, "run_acceptance", side_effect=failure), \
                patch("builtins.print"):
            report = Path(folder) / "report.json"
            with self.assertRaises(rc.acceptance.AcceptanceError):
                rc.smoke(report, docker)
            result = json.loads(report.read_text())
        self.assertEqual(result["outcome"], "failed: Run ended failed")
        self.assertTrue(result["project"].startswith("lps-rc-smoke-"))
        self.assertEqual(docker.calls[-2], ["down", "--volumes", "--remove-orphans", "--timeout", "10"])

    def test_cli_report_flag_writes_only_to_the_fixed_evidence_path(self):
        with patch.object(rc, "smoke") as smoke, patch("builtins.print"):
            self.assertEqual(rc.main(["smoke", "--report"]), 0)
            self.assertEqual(rc.main(["smoke"]), 0)
        self.assertEqual([c.args[0] for c in smoke.call_args_list], [rc.REPORT_PATH, None])
        with patch("sys.stderr"), self.assertRaises(SystemExit):
            rc.parser().parse_args(["smoke", "--report", "/etc/passwd"])

    def test_smoke_fails_if_containers_survive_teardown(self):
        docker = FakeDocker()
        docker.answers[("ps", "--all")] = b"leftover\n"
        with patch.object(rc, "smoke_steps", return_value={}), patch("builtins.print"):
            with self.assertRaisesRegex(rc.CandidateError, "remain after teardown"):
                rc.smoke(None, docker)


if __name__ == "__main__":
    unittest.main()
