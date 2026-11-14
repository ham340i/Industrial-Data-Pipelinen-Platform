# AI contribution: 50% or more AI-generated
"""API-level integration fixtures for the Release 1 block matrix (#37).

Every helper drives the real FastAPI application through ``TestClient`` over
a real SQLite metadata database and a real per-project workspace folder, so
the matrix exercises the same validate → save → execute → status → output
path the Builder uses. No block is invoked directly from these helpers.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq
from fastapi.testclient import TestClient
from httpx import Response

VERSION = "1.0.0"
Row = tuple[str, int | None, bool]

# One synthetic dataset shared by every source format, so a compatibility
# case can assert the same rows regardless of how they were read.
READINGS: tuple[Row, ...] = (
    ("alpha", 1, True),
    ("beta", None, False),
    ("gamma", 3, True),
    ("delta", 4, False),
)
READINGS_SCHEMA: dict[str, list[Any]] = {
    "columns": ["name", "value", "active"],
    "types": ["string", "integer", "boolean"],
    "nullable": [False, True, False],
}
ARROW_READINGS = pa.schema(
    [
        pa.field("name", pa.string(), nullable=False),
        pa.field("value", pa.int64(), nullable=True),
        pa.field("active", pa.bool_(), nullable=False),
    ]
)


def node(key: str, block: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": key,
        "block_id": block,
        "block_version": VERSION,
        "config": config or {},
    }


def edge(
    source: str, target: str, *, source_port: str = "table", target_port: str = "table"
) -> dict[str, Any]:
    return {
        "id": f"{source}-{target}-{target_port}",
        "source": {"node_id": source, "port": source_port},
        "target": {"node_id": target, "port": target_port},
    }


def graph(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema_version": 1, "nodes": nodes, "edges": edges}


def linear(*nodes: dict[str, Any]) -> dict[str, Any]:
    """A chain over the default ``table`` ports, in the given order."""
    return graph(
        list(nodes),
        [edge(a["id"], b["id"]) for a, b in zip(nodes, nodes[1:], strict=False)],
    )


def as_records(rows: tuple[Row, ...]) -> list[dict[str, Any]]:
    return [dict(zip(READINGS_SCHEMA["columns"], row, strict=True)) for row in rows]


def csv_text(rows: tuple[Row, ...], null: str = "NULL") -> str:
    def cell(value: object) -> str:
        if value is None:
            return null
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    header = ",".join(READINGS_SCHEMA["columns"])
    body = "".join(",".join(map(cell, row)) + "\n" for row in rows)
    return f"{header}\n{body}"


@dataclass(frozen=True)
class Workbench:
    """One project with a prepared workspace folder behind the real API."""

    client: TestClient
    project_id: str
    root: Path

    @property
    def pipelines(self) -> str:
        return f"/api/v1/projects/{self.project_id}/pipelines"

    # -- synthetic inputs ---------------------------------------------------

    def write_csv(
        self, rows: tuple[Row, ...] = READINGS, name: str = "inputs/readings.csv"
    ) -> str:
        (self.root / name).write_text(csv_text(rows), encoding="utf-8")
        return name

    def write_json(
        self, rows: tuple[Row, ...] = READINGS, name: str = "inputs/readings.json"
    ) -> str:
        (self.root / name).write_text(json.dumps(as_records(rows)), encoding="utf-8")
        return name

    def write_parquet(
        self, rows: tuple[Row, ...] = READINGS, name: str = "inputs/readings.parquet"
    ) -> str:
        table = pa.Table.from_pylist(as_records(rows), schema=ARROW_READINGS)
        pq.write_table(table, self.root / name)
        return name

    def write_sqlite(
        self, rows: tuple[Row, ...] = READINGS, name: str = "inputs/readings.sqlite3"
    ) -> str:
        connection = sqlite3.connect(self.root / name)
        try:
            connection.execute(
                "CREATE TABLE readings "
                "(name TEXT NOT NULL, value INTEGER, active INTEGER NOT NULL)"
            )
            connection.executemany(
                "INSERT INTO readings VALUES (?, ?, ?)",
                [(n, v, int(a)) for n, v, a in rows],
            )
            connection.commit()
        finally:
            connection.close()
        return name

    # -- API steps ----------------------------------------------------------

    def validate(self, definition: dict[str, Any]) -> Response:
        response = self.client.post(
            "/api/v1/pipelines/validate", json={"definition": definition}
        )
        return cast(Response, response)

    def try_save(self, definition: dict[str, Any], name: str | None = None) -> Response:
        # Pipeline names are unique per project; default to a fresh one.
        name = name or f"matrix-{uuid4().hex[:8]}"
        response = self.client.post(
            self.pipelines, json={"name": name, "definition": definition}
        )
        return cast(Response, response)

    def save(self, definition: dict[str, Any], name: str | None = None) -> str:
        response = self.try_save(definition, name)
        assert response.status_code == 201, response.text
        return str(response.json()["id"])

    def execute(self, pipeline_id: str) -> Response:
        return cast(
            Response, self.client.post(f"{self.pipelines}/{pipeline_id}/execute")
        )

    def run(self, run_id: str) -> dict[str, Any]:
        response = self.client.get(f"/api/v1/runs/{run_id}")
        assert response.status_code == 200, response.text
        return dict(response.json())

    def runs(self, **params: Any) -> dict[str, Any]:
        response = self.client.get("/api/v1/runs", params=params)
        assert response.status_code == 200, response.text
        return dict(response.json())

    def artifact(self, artifact_id: str) -> Response:
        return cast(Response, self.client.get(f"/api/v1/artifacts/{artifact_id}"))

    def query(self, artifact_id: str, **payload: Any) -> Response:
        url = f"/api/v1/artifacts/{artifact_id}/query"
        return cast(Response, self.client.post(url, json=payload))

    def preview(
        self, definition: dict[str, Any], node_id: str, **limits: int
    ) -> Response:
        payload: dict[str, Any] = {"definition": definition, "node_id": node_id}
        if limits:
            payload["limits"] = limits
        return cast(
            Response, self.client.post(f"{self.pipelines}/preview", json=payload)
        )

    def run_pipeline(self, definition: dict[str, Any]) -> dict[str, Any]:
        """Save, execute and return the persisted run detail (validation OK)."""
        report = self.validate(definition)
        assert report.status_code == 200, report.text
        assert report.json()["valid"], report.json()["diagnostics"]
        response = self.execute(self.save(definition))
        assert response.status_code == 201, response.text
        return self.run(response.json()["run_id"])


def block_states(detail: dict[str, Any]) -> dict[str, str]:
    return {block["node_id"]: block["state"] for block in detail["blocks"]}


def build_workbench(client: TestClient, workspace_root: Path) -> Workbench:
    """Create a project through the API; the API prepares its data folder."""
    response = client.post("/api/v1/projects", json={"name": "Integration"})
    assert response.status_code == 201, response.text
    project_id = str(response.json()["id"])
    root = workspace_root.resolve() / project_id
    assert (root / "inputs").is_dir(), "prepare_project did not create inputs/"
    return Workbench(client, project_id, root)
