#!/usr/bin/env python3
# AI contribution: 50% or more AI-generated
"""Release 1 acceptance scenario over the public HTTP API only (#36).

Builds the target graph from synthetic data, runs it and checks every block
count and the published Parquet rows:

    CSV -> Validate Schema -> Filter --+
                                       +-> Join -> Aggregate -> Parquet
    SQL Source ------------------------+

The scenario needs only a base URL and a way to place two input files in the
project's data folder, so the same checks run against a local API, a running
Compose candidate (``release_candidate.py demo``) or a throwaway one
(``release_candidate.py smoke``). Standard library only.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import json
from pathlib import Path
import sqlite3
import tempfile
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BLOCK_VERSION = "1.0.0"
PROJECT_NAME = "Release 1 demo"
PIPELINE_NAME = "Release CSV SQL aggregate"
READINGS_CSV = "asset_id,reading\n1,5\n1,12\n1,18\n2,20\n2,30\n3,40\n"
ASSETS = ((1, "A"), (2, "B"), (3, None))
# Oracle: readings > 10 joined to labelled assets, summed per label.
EXPECTED_ROWS = [["A", 30], ["B", 50]]
EXPECTED_BLOCK_ROWS = {
    "csv": (0, 6),
    "validate": (6, 6),
    "filter": (6, 5),
    "assets": (0, 2),
    "join": (7, 4),
    "aggregate": (4, 2),
    "sink": (2, 1),
}

Json = dict[str, Any]
Send = Callable[[str, str, Json | None], tuple[int, Any]]
WriteInput = Callable[[str, str, bytes], None]


class AcceptanceError(RuntimeError):
    """The candidate did not behave as Release 1 requires."""


def sqlite_bytes() -> bytes:
    """A tiny synthetic SQLite database, built in a private temp folder."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "assets.sqlite3"
        connection = sqlite3.connect(path)
        try:
            connection.execute("CREATE TABLE assets(asset_id INTEGER, label TEXT)")
            connection.executemany("INSERT INTO assets VALUES (?, ?)", ASSETS)
            connection.commit()
        finally:
            connection.close()
        return path.read_bytes()


def _node(key: str, block: str, config: Json) -> Json:
    return {
        "id": key,
        "block_id": block,
        "block_version": BLOCK_VERSION,
        "config": config,
    }


def _edge(source: str, target: str, port: str = "table") -> Json:
    return {
        "id": f"{source}-{target}",
        "source": {"node_id": source, "port": "table"},
        "target": {"node_id": target, "port": port},
    }


def _source_nodes() -> list[Json]:
    """The CSV branch's source and gates, and the SQL lookup source."""
    readings = {
        "resource_ref": "inputs/readings.csv",
        "columns": ["asset_id", "reading"],
        "types": ["integer", "integer"],
        "nullable": [False, False],
    }
    schema = [
        {"name": "asset_id", "dtype": "integer"},
        {"name": "reading", "dtype": "integer"},
    ]
    assets = {
        "resource_ref": "inputs/assets.sqlite3",
        "columns": ["asset_id", "label"],
        "types": ["integer", "string"],
        "nullable": [False, True],
        "query": "SELECT asset_id, label FROM assets "
        "WHERE label IS NOT NULL ORDER BY asset_id",
    }
    return [
        _node("csv", "source.csv", readings),
        _node("validate", "quality.schema_validation", {"columns": schema}),
        _node(
            "filter",
            "transform.filter",
            {"column": "reading", "operator": "gt", "value_text": "10"},
        ),
        _node("assets", "source.sql", assets),
    ]


def _output_nodes() -> list[Json]:
    """Join the two branches, total per label and publish Parquet."""
    total = {"column": "reading", "function": "sum", "output_name": "total"}
    return [
        _node(
            "join",
            "transform.join",
            {"left_on": ["asset_id"], "right_on": ["asset_id"]},
        ),
        _node(
            "aggregate",
            "transform.aggregate",
            {"group_by": ["label"], "operations": [total]},
        ),
        _node(
            "sink",
            "sink.parquet",
            {"resource_ref": "outputs/result.parquet", "overwrite": "replace"},
        ),
    ]


def release_graph() -> Json:
    """The Release 1 target graph, configured for the synthetic inputs."""
    edges = [
        _edge("csv", "validate"),
        _edge("validate", "filter"),
        _edge("filter", "join", "left"),
        _edge("assets", "join", "right"),
        _edge("join", "aggregate"),
        _edge("aggregate", "sink"),
    ]
    nodes = _source_nodes() + _output_nodes()
    return {"schema_version": 1, "nodes": nodes, "edges": edges}


def http_sender(base_url: str, timeout: float = 300.0) -> Send:
    """Send JSON to ``base_url`` (``http://host:port``) and decode the reply."""
    root = base_url.rstrip("/") + "/api/v1"
    if not root.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise AcceptanceError("The acceptance scenario only targets a loopback API")

    def send(method: str, path: str, body: Json | None) -> tuple[int, Any]:
        data = None if body is None else json.dumps(body).encode()
        request = Request(root + path, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urlopen(request, timeout=timeout) as response:  # loopback only
                return response.status, json.loads(response.read() or b"null")
        except HTTPError as error:
            return error.code, json.loads(error.read() or b"null")

    return send


def expect(
    send: Send, method: str, path: str, status: int, body: Json | None = None
) -> Any:
    actual, payload = send(method, path, body)
    if actual != status:
        raise AcceptanceError(
            f"{method} {path}: expected HTTP {status}, got {actual}: {payload}"
        )
    return payload


def check_run(send: Send, run_id: str) -> str:
    """Assert a succeeded run with the oracle's block counts; return the artifact id."""
    run = expect(send, "GET", f"/runs/{run_id}", 200)
    if run["state"] != "succeeded":
        raise AcceptanceError(f"Run {run_id} ended {run['state']}: {run.get('error')}")
    counts = {b["node_id"]: (b["rows_in"], b["rows_out"]) for b in run["blocks"]}
    if counts != EXPECTED_BLOCK_ROWS:
        raise AcceptanceError(f"Block row counts differ from the oracle: {counts}")
    if len(run["outputs"]) != 1:
        raise AcceptanceError("The run did not register exactly one output artifact")
    return str(run["outputs"][0]["id"])


def check_rows(send: Send, artifact_id: str) -> list[list[Any]]:
    payload = {"columns": [], "offset": 0, "limit": 50}
    page = expect(send, "POST", f"/artifacts/{artifact_id}/query", 200, payload)
    rows = sorted(page["rows"])
    if page["columns"] != ["label", "total"] or rows != EXPECTED_ROWS:
        raise AcceptanceError(f"Output rows differ from the oracle: {page}")
    return rows


def run_acceptance(
    send: Send, write_input: WriteInput, project_name: str = PROJECT_NAME
) -> Json:
    """Create, seed, validate, save, execute, inspect and rerun; return evidence."""
    project = expect(send, "POST", "/projects", 201, {"name": project_name})
    project_id = str(project["id"])
    write_input(project_id, "inputs/readings.csv", READINGS_CSV.encode())
    write_input(project_id, "inputs/assets.sqlite3", sqlite_bytes())
    definition = release_graph()
    report = expect(
        send, "POST", "/pipelines/validate", 200, {"definition": definition}
    )
    if not report["valid"]:
        raise AcceptanceError(f"Release graph is invalid: {report['diagnostics']}")
    pipelines = f"/projects/{project_id}/pipelines"
    saved = expect(
        send, "POST", pipelines, 201, {"name": PIPELINE_NAME, "definition": definition}
    )
    pipeline_id = str(saved["id"])
    run_ids = []
    for _ in range(2):  # the rerun must reproduce the same output
        run = expect(send, "POST", f"{pipelines}/{pipeline_id}/execute", 201)
        run_ids.append(str(run["run_id"]))
    artifact_id = check_run(send, run_ids[-1])
    check_run(send, run_ids[0])
    rows = check_rows(send, artifact_id)
    return {
        "project_id": project_id,
        "pipeline_id": pipeline_id,
        "run_ids": run_ids,
        "artifact_id": artifact_id,
        "rows": rows,
    }


def verify_evidence(send: Send, evidence: Json) -> None:
    """Reopen everything a previous ``run_acceptance`` produced."""
    project_id = evidence["project_id"]
    expect(send, "GET", f"/projects/{project_id}", 200)
    pipeline = f"/projects/{project_id}/pipelines/{evidence['pipeline_id']}"
    if expect(send, "GET", pipeline, 200)["name"] != PIPELINE_NAME:
        raise AcceptanceError("The saved pipeline did not reopen by name")
    for run_id in evidence["run_ids"]:
        check_run(send, run_id)
    check_rows(send, evidence["artifact_id"])


def verify_absent(send: Send, evidence: Json) -> None:
    """After a reset, the demo project must be gone, not silently kept."""
    expect(send, "GET", f"/projects/{evidence['project_id']}", 404)


def folder_writer(workspace_root: Path) -> WriteInput:
    """Write inputs straight into a local workspace (non-container runs)."""

    def write(project_id: str, relative: str, data: bytes) -> None:
        target = workspace_root / project_id / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    return write


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="The API's LPS_WORKSPACE_ROOT on this machine",
    )
    args = parser.parse_args()
    send = http_sender(args.base_url)
    evidence = run_acceptance(send, folder_writer(args.workspace))
    verify_evidence(send, evidence)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
