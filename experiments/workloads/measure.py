# AI contribution: 50% or more AI-generated
"""Host-side Docker runner; emits a verified-constraint JSON report on stdout."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, choices=range(1, 6), default=3)
    args = parser.parse_args()
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    command = [
        "docker",
        "create",
        "--network",
        "none",
        "--cpus=2",
        "--memory=1g",
        "-e",
        "POLARS_MAX_THREADS=2",
        "-e",
        f"BENCHMARK_REVISION={revision}",
        "--mount",
        f"type=bind,source={ROOT},target=/review,readonly",
        "--workdir",
        "/review",
        "lps-workload-benchmark",
        "python",
        "-m",
        "experiments.workloads.benchmark",
        "--repeats",
        str(args.repeats),
    ]
    container = subprocess.check_output(command, text=True).strip()
    try:
        inspected = json.loads(
            subprocess.check_output(
                ["docker", "inspect", container],
                text=True,
            )
        )[0]
        completed = subprocess.run(
            ["docker", "start", "--attach", container],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if completed.returncode:
            raise RuntimeError(f"Measurement failed: {completed.stderr[-4000:]}")
        report = json.loads(completed.stdout)
        report["docker_constraints"] = {
            key: inspected["HostConfig"][key]
            for key in ("NanoCpus", "Memory", "MemorySwap", "NetworkMode")
        }
        report["container_image_id"] = inspected["Image"]
        report["runner_sha256"] = hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest()
        sys.stdout.write(json.dumps(report, indent=2) + "\n")
    finally:
        # This ID is returned by our own docker create, never an existing stack.
        subprocess.run(
            ["docker", "rm", "--force", container], capture_output=True, check=True
        )


if __name__ == "__main__":
    main()
