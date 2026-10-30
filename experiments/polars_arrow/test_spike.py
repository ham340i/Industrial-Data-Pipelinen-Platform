"""Experiment correctness tests; no production dependency changes."""

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

import polars as pl
from polars.testing import assert_frame_equal

import spike
from spike import fixture, preview, verify_roundtrip


class InterchangeTests(unittest.TestCase):
    def test_cli_emits_complete_report_on_stdout(self):
        completed = subprocess.run(
            [sys.executable, str(Path(spike.__file__).resolve()), "--repeats", "1"],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        report = json.loads(completed.stdout)
        self.assertEqual(report["repeats"], 1)
        self.assertEqual(len(report["runs"]), 3)
        self.assertEqual(set(report["summary"]), {"small", "wide", "nulls"})
        self.assertTrue(all(run["correctness"] == "passed" for run in report["runs"]))

    def test_cli_rejects_output_paths_without_changing_existing_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            working = root / "working"
            working.mkdir()
            target = root / "existing.json"
            target.write_text("keep-existing-content", encoding="utf-8")
            for arguments in [
                ["--output", str(target)],
                ["--output", "../existing.json"],
                [f"--output={target}"],
            ]:
                with self.subTest(arguments=arguments):
                    completed = subprocess.run(
                        [
                            sys.executable,
                            str(Path(spike.__file__).resolve()),
                            *arguments,
                        ],
                        cwd=working,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                    self.assertEqual(completed.returncode, 2, completed.stderr)
                    self.assertIn("unrecognized arguments", completed.stderr)
                    self.assertEqual(
                        target.read_text(encoding="utf-8"), "keep-existing-content"
                    )

    def test_deterministic_and_empty_fixtures(self):
        for rows, width in [(0, 10), (1, 10), (32, 128)]:
            with self.subTest(rows=rows, width=width):
                left, right = fixture(rows, width), fixture(rows, width)
                self.assertEqual(left.shape, (rows, width))
                assert_frame_equal(left, right, check_exact=True)
                with tempfile.TemporaryDirectory() as path:
                    verify_roundtrip(left, Path(path))

    def test_known_reference_values(self):
        frame = fixture(12)
        self.assertEqual(frame["large_integer"][0], 2**53 + 1)
        self.assertEqual(frame["unsigned"][0], 2**63)
        self.assertEqual(frame["value"].null_count(), 2)
        self.assertEqual(frame["nullable_integer"].null_count(), 2)
        self.assertEqual(frame["all_null"].null_count(), 12)
        self.assertEqual(frame.schema["date"], pl.Date)
        self.assertEqual(frame.schema["observed_at"], pl.Datetime("us", "UTC"))

    def test_preview_budget_and_values(self):
        frame = fixture(100, 128)
        sample = preview(frame)
        self.assertEqual(sample.height, 15)
        assert_frame_equal(sample, frame.head(15), check_exact=True)
        self.assertEqual(preview(frame, max_cells=1).height, 0)
        for rows, cells in [(0, 10), (10, 0)]:
            with self.assertRaises(ValueError):
                preview(frame, rows, cells)

    def test_lossy_float_conversion_is_detected(self):
        frame = fixture(10)
        lossy = frame.with_columns(
            pl.col("large_integer").cast(pl.Float64).cast(pl.Int64)
        )
        with self.assertRaises(AssertionError):
            assert_frame_equal(frame, lossy, check_exact=True)


if __name__ == "__main__":
    unittest.main()
