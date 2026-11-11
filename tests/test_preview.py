"""Real CSV/Select previews, resource bounds and read-only API guarantees."""

from concurrent.futures import ThreadPoolExecutor
import asyncio
from pathlib import Path
from threading import Event
from typing import Any

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from starlette.types import Message, Receive, Scope, Send

from app.blocks.context import BlockContext
from app.blocks.contracts import PreviewLimits, PreviewObservation, Table
from app.blocks.errors import BlockError
from app.blocks.files import CsvSource
from app.blocks.transforms import SelectColumns
from app.config import settings
from app.main import app
from app.metadata.models import (
    OutputEndpoint,
    PipelineRevision,
    Run,
    RunEvent,
    WorkspaceBinding,
)
from app.preview import api as preview_api
from app.preview import service
from app.preview.errors import PreviewError


def node(key: str, block: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": key,
        "block_id": block,
        "block_version": "1.0.0",
        "config": config or {},
    }


def edge(source: str, target: str) -> dict[str, Any]:
    return {
        "id": f"{source}-{target}",
        "source": {"node_id": source, "port": "table"},
        "target": {"node_id": target, "port": "table"},
    }


def payload(*, select_columns: bool = False) -> dict[str, Any]:
    nodes = [node("csv", "source.csv", {"resource_ref": "input.csv"})]
    if select_columns:
        nodes.append(node("select", "transform.select", {"columns": ["value"]}))
    return {
        "definition": {
            "schema_version": 1,
            "nodes": nodes,
            "edges": [edge("csv", "select")] if select_columns else [],
        },
        "node_id": nodes[-1]["id"],
        "output_port": "table",
        "limits": {"max_rows": 2, "max_cells": 20},
    }


@pytest.fixture
def workspace(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[str, Path]:
    project = client.post("/api/v1/projects", json={"name": "Preview"}).json()["id"]
    monkeypatch.setattr(settings, "workspace_root", tmp_path / "workspaces")
    root = tmp_path / "workspaces" / project
    root.mkdir(parents=True)
    (root / "input.csv").write_text("id,value\n1,10\n2,NULL\n3,30\n", encoding="utf-8")
    return f"/api/v1/projects/{project}/pipelines/preview", root


def test_source_and_select_counts_schema_nulls_and_no_side_effects(
    client: TestClient, workspace: tuple[str, Path], monkeypatch: pytest.MonkeyPatch
):
    url, root = workspace

    def no_execution(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Preview must not execute")

    monkeypatch.setattr(CsvSource, "_execute", no_execution)
    monkeypatch.setattr(SelectColumns, "_execute", no_execution)
    request = payload(select_columns=True)
    request["definition"]["nodes"].append(
        node("sink", "sink.csv", {"resource_ref": "output.csv"})
    )
    request["definition"]["edges"].append(edge("select", "sink"))
    response = client.post(
        url, json=request, headers={"X-Correlation-ID": "preview-test"}
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-correlation-id"] == "preview-test"
    assert result["rows"] == [{"value": "10"}, {"value": None}]
    assert result["sample_row_count"] == 2 and result["sample_cell_count"] == 2
    assert result["inspected_row_count"] == 3 and result["full_row_count"] is None
    assert result["truncated"] and result["schema_scope"] == "header"
    assert result["nulls"] == [{"column": "value", "null_count": 1}]
    assert result["null_scope"] == "returned_sample"
    assert result["evaluated_node_ids"] == ["csv", "select"]
    assert not (root / "output.csv").exists()
    with app.state.database.transaction() as session:
        for entity in (PipelineRevision, Run, RunEvent, OutputEndpoint):
            assert session.scalar(select(func.count()).select_from(entity)) == 0


@pytest.mark.parametrize(
    "body,expected", [("id,value\n", 0), ("id,value\n1,NULL\n2,3\n", 2)]
)
def test_exact_and_empty_counts_keep_declared_schema(
    client: TestClient, workspace: tuple[str, Path], body: str, expected: int
):
    url, root = workspace
    (root / "input.csv").write_text(body, encoding="utf-8")
    request = payload(select_columns=True)
    request["definition"]["nodes"][0]["config"].update(
        columns=["id", "value"], types=["integer", "number"], nullable=[False, True]
    )
    response = client.post(url, json=request)
    assert response.status_code == 200, response.text
    result = response.json()
    assert (
        result["full_row_count"] == expected and result["sample_row_count"] == expected
    )
    assert result["inspected_row_count"] == expected and not result["truncated"]
    assert result["data_schema"]["columns"] == [
        {"name": "value", "dtype": "number", "nullable": True}
    ]
    assert result["schema_scope"] == "declared"


def test_prefix_is_bounded_and_does_not_validate_unsampled_tail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    path = tmp_path / "input.csv"
    path.write_text(
        "value\n1\n2\n3\n" + "malformed,tail\n" * 10000, encoding="utf-8", newline=""
    )

    def forbidden_read(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("No whole-file reads")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
    observations: list[PreviewObservation] = []
    result = CsvSource().preview(
        {"resource_ref": "input.csv"},
        {},
        BlockContext(
            "preview",
            "source",
            workspace_root=tmp_path,
            observe_preview=observations.append,
        ),
        PreviewLimits(max_rows=2),
    )
    table = result["table"][0]
    assert isinstance(table, Table) and len(table.rows) == 2
    assert observations[0].read_bytes == len("value\n1\n2\n3\n")
    assert observations[0].full_row_count is None


@pytest.mark.parametrize(
    "body,config,code",
    [
        ("a,b\n1\n", {}, "invalid_csv"),
        ("a,a\n1,2\n", {}, "invalid_csv"),
        ("a\n" + "x" * 4097 + "\n", {}, "preview_field_limit"),
        (",".join(f"c{i}" for i in range(129)) + "\n", {}, "preview_columns"),
        ('a\n"' + "x\n" * 40000, {}, "preview_read_limit"),
        ("a\nhello\n", {"max_bytes": 4}, "preview_read_limit"),
        (
            "a\nnot-a-number\n",
            {"columns": ["a"], "types": ["integer"], "nullable": [False]},
            "cast_failed",
        ),
        (
            "a\nNULL\n",
            {"columns": ["a"], "types": ["string"], "nullable": [False]},
            "schema_mismatch",
        ),
    ],
    ids=[
        "width",
        "header",
        "field",
        "columns",
        "record",
        "bytes",
        "cast",
        "nullability",
    ],
)
def test_csv_limits_and_safe_errors(
    client: TestClient,
    workspace: tuple[str, Path],
    body: str,
    config: dict[str, Any],
    code: str,
):
    url, root = workspace
    (root / "input.csv").write_text(body, encoding="utf-8")
    request = payload()
    request["definition"]["nodes"][0]["config"].update(config)
    response = client.post(url, json=request)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["node_context"] == "csv"
    assert str(root) not in response.text and "not-a-number" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_cell_and_source_limits_are_applied_before_transform(
    client: TestClient, workspace: tuple[str, Path]
):
    url, _ = workspace
    request = payload(select_columns=True)
    request["limits"] = {"max_rows": 100, "max_cells": 2}
    response = client.post(url, json=request)
    assert response.json()["sample_row_count"] == 1
    assert response.json()["full_row_count"] is None
    request["limits"]["max_cells"] = 1
    assert client.post(url, json=request).json()["error"]["code"] == "preview_limit"
    request["limits"]["max_cells"] = 2000
    request["definition"]["nodes"][0]["config"]["max_rows"] = 1
    assert client.post(url, json=request).json()["sample_row_count"] == 1


@pytest.mark.parametrize(
    "block",
    [
        "sink.csv",
        "trigger.timer",
        "quality.null_check",
        "transform.sort",
    ],
)
def test_unsupported_blocks_never_read_or_execute(
    client: TestClient,
    workspace: tuple[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    block: str,
):
    url, _ = workspace

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Must reject before reading")

    monkeypatch.setattr(CsvSource, "_preview", forbidden)
    request = payload()
    request["definition"]["nodes"].append(node("unsupported", block))
    request["definition"]["edges"].append(edge("csv", "unsupported"))
    request["node_id"] = "unsupported"
    response = client.post(url, json=request)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "preview_unsupported"


def test_invalid_ancestors_block_but_unrelated_nodes_do_not(
    client: TestClient, workspace: tuple[str, Path]
):
    url, _ = workspace
    request = payload(select_columns=True)
    request["definition"]["nodes"].append(node("unrelated", "missing.block"))
    assert client.post(url, json=request).status_code == 200
    request["definition"]["nodes"][1]["config"] = {}
    error = client.post(url, json=request).json()["error"]
    assert error["code"] == "preview_invalid_graph" and error["field"] == "columns"
    request["definition"]["nodes"][1]["config"] = {"columns": ["absent"]}
    assert client.post(url, json=request).json()["error"]["code"] == "missing_column"
    request["definition"]["edges"].append(edge("select", "csv"))
    assert (
        client.post(url, json=request).json()["error"]["code"]
        == "preview_invalid_graph"
    )


def test_private_binding_is_project_scoped_and_contained(
    client: TestClient, workspace: tuple[str, Path], tmp_path: Path
):
    url, root = workspace
    (root / "alternate.csv").write_text("value\nprivate-binding\n", encoding="utf-8")
    with app.state.database.transaction() as session:
        binding = WorkspaceBinding(
            project_id=root.name, resource_id="input.csv", local_path="alternate.csv"
        )
        session.add(binding)
    response = client.post(url, json=payload())
    assert response.json()["rows"] == [{"value": "private-binding"}]
    outside = tmp_path / "outside.csv"
    outside.write_text("secret\nnever-return-this\n", encoding="utf-8")
    with app.state.database.transaction() as session:
        saved = session.scalar(
            select(WorkspaceBinding).where(WorkspaceBinding.project_id == root.name)
        )
        assert saved is not None
        saved.local_path = str(outside)
    response = client.post(url, json=payload())
    assert (
        response.status_code == 422
        and response.json()["error"]["code"] == "unsafe_resource"
    )
    assert (
        "never-return-this" not in response.text and str(outside) not in response.text
    )
    other = client.post("/api/v1/projects", json={"name": "Other"}).json()["id"]
    other_root = root.parent / other
    other_root.mkdir(exist_ok=True)
    (other_root / "input.csv").write_text("value\nother-project\n", encoding="utf-8")
    assert client.post(url.replace(root.name, other), json=payload()).json()[
        "rows"
    ] == [{"value": "other-project"}]


def test_missing_project_workspace_and_output_are_actionable(
    client: TestClient, workspace: tuple[str, Path], monkeypatch: pytest.MonkeyPatch
):
    url, root = workspace
    assert (
        client.post(
            url.replace(root.name, "00000000-0000-0000-0000-000000000000"),
            json=payload(),
        ).status_code
        == 404
    )
    request = payload()
    request["output_port"] = "absent"
    assert (
        client.post(url, json=request).json()["error"]["code"]
        == "preview_output_missing"
    )
    monkeypatch.setattr(settings, "workspace_root", None)
    assert (
        client.post(url, json=payload()).json()["error"]["code"] == "workspace_required"
    )


@pytest.mark.parametrize(
    "limits",
    [
        {"max_rows": 0},
        {"max_rows": 1001},
        {"max_cells": 10001},
        {"max_rows": True},
        {"max_rows": "2"},
    ],
)
def test_invalid_limits_and_cache_headers(
    client: TestClient, workspace: tuple[str, Path], limits: dict[str, Any]
):
    request = payload()
    request["limits"] = limits
    response = client.post(workspace[0], json=request)
    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"


def test_raw_request_graph_and_response_limits(
    client: TestClient, workspace: tuple[str, Path], monkeypatch: pytest.MonkeyPatch
):
    url, _ = workspace
    response = client.post(
        url,
        content=b"x" * (256 * 1024 + 1),
        headers={"content-type": "application/json"},
    )
    assert (
        response.status_code == 413 and response.headers["cache-control"] == "no-store"
    )
    request = payload()
    request["definition"]["nodes"] *= 101
    assert client.post(url, json=request).status_code == 422
    monkeypatch.setattr(preview_api, "MAX_RESPONSE_BYTES", 10)
    assert (
        client.post(url, json=payload()).json()["error"]["code"]
        == "preview_response_limit"
    )


def test_timeout_and_cancellation_stop_before_reading(
    client: TestClient, workspace: tuple[str, Path], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(service, "MAX_SECONDS", 0)
    response = client.post(workspace[0], json=payload())
    assert response.json()["error"]["code"] == "preview_timeout"
    with pytest.raises(BlockError) as caught:
        CsvSource().preview(
            {"resource_ref": "input.csv"},
            {},
            BlockContext(
                "preview", "csv", workspace_root=workspace[1], is_cancelled=lambda: True
            ),
        )
    assert caught.value.failure.code == "cancelled"


def test_disconnect_cancels_worker_and_frees_capacity(
    client: TestClient, workspace: tuple[str, Path], monkeypatch: pytest.MonkeyPatch
):
    def waiting_preview(*args: Any, **kwargs: Any) -> Any:
        event = args[-1]
        assert isinstance(event, Event)
        assert event.wait(3)
        raise PreviewError("preview_cancelled", "Preview was cancelled.")

    async def disconnected(self: Request) -> bool:
        return True

    monkeypatch.setattr(preview_api, "preview", waiting_preview)
    monkeypatch.setattr(Request, "is_disconnected", disconnected)
    for _ in range(3):
        response = client.post(workspace[0], json=payload())
        assert response.json()["error"]["code"] == "preview_cancelled"


def test_large_integer_is_never_silently_rounded(
    client: TestClient, workspace: tuple[str, Path]
):
    url, root = workspace
    (root / "input.csv").write_text("value\n9007199254740993\n", encoding="utf-8")
    request = payload()
    assert client.post(url, json=request).json()["rows"] == [
        {"value": "9007199254740993"}
    ]
    request["definition"]["nodes"][0]["config"].update(
        columns=["value"], types=["integer"], nullable=[False]
    )
    error = client.post(url, json=request).json()["error"]
    assert error["code"] == "preview_value_range" and error["field"] == "value"


def test_concurrency_admission_releases_capacity(
    client: TestClient, workspace: tuple[str, Path], monkeypatch: pytest.MonkeyPatch
):
    original = service.preview
    entered = [Event(), Event()]
    release = Event()

    def slow(*args: Any, **kwargs: Any) -> Any:
        for event in entered:
            if not event.is_set():
                event.set()
                break
        assert release.wait(5)
        return original(*args, **kwargs)

    monkeypatch.setattr(preview_api, "preview", slow)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = [
            pool.submit(client.post, workspace[0], json=payload()) for _ in range(2)
        ]
        try:
            assert all(event.wait(3) for event in entered)
            response = client.post(workspace[0], json=payload())
            assert (
                response.status_code == 429
                and response.json()["error"]["code"] == "preview_busy"
            )
        finally:
            release.set()
        assert all(result.result().status_code == 200 for result in pending)
    assert client.post(workspace[0], json=payload()).status_code == 200


def test_body_timeout_is_bounded_before_json_parsing(monkeypatch: pytest.MonkeyPatch):
    messages: list[Message] = []

    async def unreachable(scope: Scope, receive: Receive, send: Send) -> None:
        raise AssertionError("Body timeout must precede the application")

    async def receive() -> Message:
        await asyncio.sleep(1)
        return {"type": "http.request", "body": b"{}"}

    async def send(message: Message) -> None:
        messages.append(message)

    monkeypatch.setattr(preview_api, "MAX_BODY_SECONDS", 0.001)
    middleware = preview_api.PreviewBoundaryMiddleware(unreachable)
    asyncio.run(
        middleware({"type": "http", "path": "/pipelines/preview"}, receive, send)
    )
    assert messages[0]["status"] == 408
    assert b"preview_request_timeout" in messages[1]["body"]


def test_dependency_failures_are_also_uncacheable(
    client: TestClient, workspace: tuple[str, Path], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(app.state, "database", None)
    response = client.post(workspace[0], json=payload())
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert response.headers["cache-control"] == "no-store"


def test_ancestor_budget_and_malformed_requests(
    client: TestClient, workspace: tuple[str, Path]
):
    request = payload()
    previous = "csv"
    for index in range(20):
        key = f"select-{index}"
        request["definition"]["nodes"].append(
            node(key, "transform.select", {"columns": ["value"]})
        )
        request["definition"]["edges"].append(edge(previous, key))
        previous = key
    request["node_id"] = previous
    assert (
        client.post(workspace[0], json=request).json()["error"]["code"]
        == "preview_graph_limit"
    )
    response = client.post(
        workspace[0], content=b"{", headers={"Content-Type": "application/json"}
    )
    assert (
        response.status_code == 422 and response.headers["cache-control"] == "no-store"
    )
