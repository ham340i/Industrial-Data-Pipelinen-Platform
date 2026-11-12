# AI contribution: 50% or more AI-generated
"""SQL block security, schema and real execution integration (#23)."""

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.blocks.context import BlockContext
from app.blocks.contracts import Table
from app.blocks.errors import BlockError
from app.blocks.sql import SqlSource
from app.config import settings


@pytest.fixture
def database(tmp_path: Path) -> Path:
    with sqlite3.connect(tmp_path / "data.sqlite3") as connection:
        connection.executescript(
            "CREATE TABLE assets (asset_id INTEGER, label TEXT);"
            "INSERT INTO assets VALUES (1, 'A'), (2, NULL);"
        )
    return tmp_path


def config(**changes: Any) -> dict[str, Any]:
    return {
        "resource_ref": "data.sqlite3",
        "query": "SELECT asset_id, label FROM assets ORDER BY asset_id",
        "columns": ["asset_id", "label"],
        "types": ["integer", "string"],
        "nullable": [False, True],
        **changes,
    }


def read(root: Path, **changes: Any) -> Table:
    result = SqlSource().run(
        config(**changes),
        {},
        BlockContext(run_id="sql", node_id="source", workspace_root=root),
    )["table"][0]
    assert isinstance(result, Table)
    return result


def test_types_nulls_empty_and_bound_values(database: Path):
    table = read(database)
    assert table.rows == ({"asset_id": 1, "label": "A"}, {"asset_id": 2, "label": None})
    empty = read(
        database,
        query="SELECT asset_id, label FROM assets WHERE asset_id=:id",
        parameters_json='{"id":"1 OR 1=1"}',
    )
    assert empty.rows == ()
    assert empty.data_schema == table.data_schema


@pytest.mark.parametrize(
    "changes",
    [
        {"query": "DELETE FROM assets"},
        {"parameters_json": '{"password":"hidden"}'},
        {"parameters_json": '{"id":NaN}'},
        {"parameters_json": '{"id":[]}'},
        {"resource_ref": "../data.sqlite3"},
    ],
)
def test_invalid_portable_inputs(database: Path, changes: dict[str, Any]):
    with pytest.raises(BlockError, match="configuration"):
        read(database, **changes)


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"max_rows": 1}, "sql_query_failed"),
        ({"query": "SELECT missing FROM assets"}, "sql_query_failed"),
        ({"query": "SELECT 1 AS asset_id, X'00' AS label"}, "schema_mismatch"),
        ({"types": ["string", "string"]}, "schema_mismatch"),
        ({"resource_ref": "missing.sqlite3"}, "file_unavailable"),
        ({"max_bytes": 1}, "file_limit"),
        ({"max_columns": 1}, "sql_query_failed"),
        ({"nullable": [False, False]}, "schema_mismatch"),
        (
            {
                "query": "SELECT 9223372036854775807 AS asset_id, NULL AS label",
                "types": ["number", "string"],
            },
            "schema_mismatch",
        ),
        (
            {
                "query": "WITH RECURSIVE x(n) AS "
                "(SELECT 1 UNION ALL SELECT n+1 FROM x) "
                "SELECT n AS asset_id, 'A' AS label FROM x",
                "max_steps": 1000,
            },
            "sql_query_failed",
        ),
    ],
)
def test_failures_are_structured_and_redacted(
    database: Path, changes: dict[str, Any], code: str
):
    with pytest.raises(BlockError) as failure:
        read(database, **changes)
    assert failure.value.failure.code == code
    assert str(database) not in str(failure.value)
    assert "SELECT" not in str(failure.value)
    with sqlite3.connect(database / "data.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM assets").fetchone() == (2,)


def test_runtime_resolver_cannot_escape_workspace(database: Path, tmp_path: Path):
    outside = tmp_path.parent / "outside.sqlite3"
    context = BlockContext(
        run_id="sql",
        node_id="source",
        workspace_root=database,
        resolve_resource=lambda _: outside,
    )
    with pytest.raises(BlockError) as failure:
        SqlSource().run(config(), {}, context)
    assert failure.value.failure.code == "unsafe_resource"


def release_graph() -> dict[str, Any]:
    schema = [
        {"name": "asset_id", "dtype": "integer", "nullable": False},
        {"name": "reading", "dtype": "integer", "nullable": False},
    ]
    specifications = [
        (
            "csv",
            "source.csv",
            {
                "resource_ref": "readings.csv",
                "columns": ["asset_id", "reading"],
                "types": ["integer", "integer"],
                "nullable": [False, False],
            },
        ),
        ("validate", "quality.schema_validation", {"columns": schema}),
        (
            "filter",
            "transform.filter",
            {"column": "reading", "operator": "gt", "value_text": "10"},
        ),
        (
            "sql",
            "source.sql",
            config(query="SELECT asset_id, label FROM assets WHERE label IS NOT NULL"),
        ),
        ("join", "transform.join", {"left_on": ["asset_id"], "right_on": ["asset_id"]}),
        (
            "aggregate",
            "transform.aggregate",
            {
                "group_by": ["label"],
                "operations": [
                    {"column": "reading", "function": "sum", "output_name": "total"}
                ],
            },
        ),
        (
            "sink",
            "sink.parquet",
            {"resource_ref": "result.parquet", "overwrite": "replace"},
        ),
    ]
    connections = [
        ("csv", "validate", "table"),
        ("validate", "filter", "table"),
        ("filter", "join", "left"),
        ("sql", "join", "right"),
        ("join", "aggregate", "table"),
        ("aggregate", "sink", "table"),
    ]
    return {
        "schema_version": 1,
        "nodes": [
            {"id": i, "block_id": b, "block_version": "1.0.0", "config": c}
            for i, b, c in specifications
        ],
        "edges": [
            {
                "id": f"e{i}",
                "source": {"node_id": s, "port": "table"},
                "target": {"node_id": t, "port": p},
            }
            for i, (s, t, p) in enumerate(connections)
        ],
    }


def test_real_saved_release_graph_executes_and_reruns(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    database: Path,
):
    import pyarrow.parquet as pq
    import shutil

    monkeypatch.setattr(settings, "workspace_root", tmp_path / "workspaces")
    (tmp_path / "workspaces").mkdir()
    # App selection must also drive execution/timer resource resolution.
    selected = tmp_path / "selected"
    selected.mkdir()
    monkeypatch.setattr(settings, "allowed_workspace_roots", [selected])
    client.put(
        "/api/v1/settings/workspace", json={"root_path": str(selected)}
    ).raise_for_status()
    project = client.post("/api/v1/projects", json={"name": "SQL release"}).json()
    workspace = selected / project["id"]
    workspace.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(database / "data.sqlite3", workspace / "data.sqlite3")
    (workspace / "readings.csv").write_text("asset_id,reading\n1,5\n1,20\n1,30\n2,99\n")
    graph = release_graph()
    validation = client.post("/api/v1/pipelines/validate", json={"definition": graph})
    assert validation.json()["valid"], validation.text
    path = f"/api/v1/projects/{project['id']}/pipelines"
    saved = client.post(path, json={"name": "Release", "definition": graph})
    assert saved.status_code == 201, saved.text
    pipeline = f"{path}/{saved.json()['id']}"
    assert client.get(pipeline).json()["definition"]["nodes"] == graph["nodes"]
    for _ in range(2):
        result = client.post(pipeline + "/execute")
        assert result.status_code == 201, result.text
        detail = client.get(f"/api/v1/runs/{result.json()['run_id']}").json()
        assert detail["state"] == "succeeded", json.dumps(detail)
        assert all(b["state"] == "completed" for b in detail["blocks"])
        assert detail["duration_ms"] is not None
        assert detail["events"]
        # Artifact indexing is owned by the still-open issue #28.
        assert detail["row_count"] == 1
        assert pq.read_table(workspace / "result.parquet").to_pylist() == [
            {"label": "A", "total": 50}
        ]


def test_result_byte_budget_stops_repeated_values(database: Path):
    from app.sources.sql import SqlSourceError, execute_read_only_sqlite

    with sqlite3.connect(database / "data.sqlite3") as connection:
        with pytest.raises(SqlSourceError, match="byte budget"):
            execute_read_only_sqlite(
                connection,
                "SELECT label FROM assets UNION ALL SELECT label FROM assets",
                max_bytes=1,
            )


def test_block_read_only_permissions_survive_query_policy_bypass(
    database: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.sources.sql import SqlQueryResult

    def bypass(
        connection: sqlite3.Connection,
        query: str,
        parameters: dict[str, Any] | None = None,
        **limits: int | None,
    ) -> SqlQueryResult:
        connection.execute("DELETE FROM assets")
        return SqlQueryResult(columns=[], rows=[])

    monkeypatch.setattr("app.blocks.sql.execute_read_only_sqlite", bypass)
    with pytest.raises(BlockError) as error:
        read(database)
    assert error.value.failure.code == "sql_connection_failed"
    with sqlite3.connect(database / "data.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM assets").fetchone() == (2,)


def test_internal_conversion_bug_is_not_schema_mismatch(
    database: Path, monkeypatch: pytest.MonkeyPatch
):
    def broken(table: Table) -> None:
        raise RuntimeError("internal bug")

    monkeypatch.setattr("app.blocks.sql.to_frame", broken)
    with pytest.raises(BlockError) as failure:
        read(database)
    assert failure.value.failure.code == "execution_failed"


def test_timer_tick_executes_sql_in_project_workspace(
    client: TestClient, database: Path, monkeypatch: pytest.MonkeyPatch
):
    from app.execution import Cancellation
    from app.runs.scheduler import _Timer

    # Reuse the manual execution integration's saved SQL workflow, then drive
    # one timer tick synchronously so this regression needs no timing sleeps.
    test_real_saved_release_graph_executes_and_reruns(
        client, database, monkeypatch, database
    )
    from sqlalchemy import select
    from app.metadata.models import PipelineRevision, Run

    from app.main import app
    from app.blocks.catalog import executor

    db = app.state.database
    with db.transaction() as session:
        revision = session.execute(select(PipelineRevision)).scalar_one()
        revision_id, pipeline_id = revision.id, revision.pipeline_id
    timer = _Timer(db, executor, pipeline_id, revision_id, 30)
    timer._run_once(Cancellation())
    with db.transaction() as session:
        runs = session.execute(select(Run)).scalars().all()
        assert len(runs) == 3
        assert all(run.state == "succeeded" for run in runs)
