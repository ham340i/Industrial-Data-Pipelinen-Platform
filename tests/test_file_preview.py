"""JSON/Parquet previews: bounded reads, honest provenance and API isolation."""

import io
import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.blocks.context import BlockContext
from app.blocks.contracts import PreviewLimits, PreviewObservation, Table
from app.blocks.errors import BlockError
from app.blocks.file_preview import BudgetFile, MAX_DECODE_BYTES, MAX_FOOTER_BYTES
from app.blocks.files import FileSource, JsonSource, ParquetSource
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


def preview_file(
    tmp_path: Path,
    suffix: str,
    config: dict[str, Any] | None = None,
    max_rows: int = 2,
    max_cells: int = 2000,
) -> tuple[Table, PreviewObservation]:
    observations: list[PreviewObservation] = []
    block = JsonSource() if suffix == "json" else ParquetSource()
    result = block.preview(
        {"resource_ref": f"input.{suffix}", **(config or {})},
        {},
        BlockContext(
            "preview",
            "source",
            workspace_root=tmp_path,
            observe_preview=observations.append,
        ),
        PreviewLimits(max_rows=max_rows, max_cells=max_cells),
    )["table"][0]
    assert isinstance(result, Table)
    return result, observations[0]


@pytest.mark.parametrize("suffix", ["json", "parquet"])
@pytest.mark.parametrize("project_columns", [False, True])
def test_api_source_and_select_with_binding_no_execution_or_publication(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
    project_columns: bool,
):
    project = client.post("/api/v1/projects", json={"name": "Files"}).json()["id"]
    monkeypatch.setattr(settings, "workspace_root", tmp_path)
    root = tmp_path / project
    root.mkdir()
    rows = [{"id": 1, "value": 10}, {"id": 2, "value": None}, {"id": 3, "value": 30}]
    actual = root / f"bound.{suffix}"
    if suffix == "json":
        actual.write_text(json.dumps(rows), encoding="utf-8")
    else:
        pq.write_table(pa.Table.from_pylist(rows), actual, row_group_size=1)
    with app.state.database.transaction() as session:
        session.add(
            WorkspaceBinding(
                project_id=project,
                resource_id=f"input.{suffix}",
                local_path=f"bound.{suffix}",
            )
        )

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Preview cannot use execution readers")

    monkeypatch.setattr(FileSource, "_execute", forbidden)
    monkeypatch.setattr(JsonSource, "_read", forbidden)
    monkeypatch.setattr(ParquetSource, "_read", forbidden)
    monkeypatch.setattr(SelectColumns, "_execute", forbidden)
    nodes = [
        {
            "id": "source",
            "block_id": f"source.{suffix}",
            "block_version": "1.0.0",
            "config": {"resource_ref": f"input.{suffix}"},
        }
    ]
    edges = []
    if project_columns:
        nodes.append(
            {
                "id": "select",
                "block_id": "transform.select",
                "block_version": "1.0.0",
                "config": {"columns": ["value"]},
            }
        )
        edges.append(
            {
                "id": "edge",
                "source": {"node_id": "source", "port": "table"},
                "target": {"node_id": "select", "port": "table"},
            }
        )
    target = nodes[-1]["id"]
    nodes.append(
        {
            "id": "sink",
            "block_id": "sink.csv",
            "block_version": "1.0.0",
            "config": {"resource_ref": "output.csv"},
        }
    )
    edges.append(
        {
            "id": "sink-edge",
            "source": {"node_id": target, "port": "table"},
            "target": {"node_id": "sink", "port": "table"},
        }
    )
    request = {
        "definition": {"nodes": nodes, "edges": edges},
        "node_id": target,
        "limits": {"max_rows": 2, "max_cells": 20},
    }
    response = client.post(
        f"/api/v1/projects/{project}/pipelines/preview", json=request
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["rows"] == (
        [{"value": 10}, {"value": None}] if project_columns else rows[:2]
    )
    assert result["schema_scope"] == ("sample" if suffix == "json" else "file_metadata")
    assert result["full_count_scope"] == (
        "unknown" if suffix == "json" else "file_metadata"
    )
    assert result["full_row_count"] == (None if suffix == "json" else 3)
    assert result["nulls"][-1] == {"column": "value", "null_count": 1}
    assert result["truncated"] and response.headers["cache-control"] == "no-store"
    assert not (root / "output.csv").exists()
    with app.state.database.transaction() as session:
        for entity in (Run, RunEvent, PipelineRevision, OutputEndpoint):
            assert session.scalar(select(func.count()).select_from(entity)) == 0
    # Another project cannot use this project's private binding or data.
    other = client.post("/api/v1/projects", json={"name": "Other"}).json()["id"]
    (tmp_path / other).mkdir(exist_ok=True)
    missing = client.post(f"/api/v1/projects/{other}/pipelines/preview", json=request)
    assert missing.json()["error"]["code"] == "file_unavailable"


@pytest.mark.parametrize(
    "body,code",
    [
        ("{}", "invalid_json"),
        ('[{"a":1},]', "invalid_json"),
        ('[{"a":1}] trailing', "invalid_json"),
        ('[{"a":1}', "invalid_json"),
        ('[{"a":1,"a":2}]', "invalid_json"),
        ('[{"a":{"b":1}}]', "unsupported_type"),
        ('[{"a":[]}]', "unsupported_type"),
        ('[{"a":NaN}]', "unsupported_value"),
        ('[{"a":1},{"b":2}]', "schema_mismatch"),
        ('[{"a":true},{"a":1}]', "unsupported_type"),
        ('[{"a":null}]', "schema_required"),
        ("[]", "schema_required"),
        ('[{"a":"' + "x" * 4097 + '"}]', "preview_field_limit"),
        ('[{"a":"' + "x" * 65536 + '"}]', "preview_read_limit"),
        (json.dumps([{str(i): i for i in range(129)}]), "preview_columns"),
        (json.dumps([{"a" * 129: 1}]), "preview_columns"),
    ],
    ids=[
        "object",
        "trailing-comma",
        "trailing-content",
        "incomplete",
        "duplicate",
        "nested-object",
        "nested-array",
        "nonfinite",
        "keys",
        "types",
        "all-null",
        "empty",
        "large-field",
        "large-record",
        "wide",
        "long-name",
    ],
)
def test_json_negative_inputs(tmp_path: Path, body: str, code: str):
    (tmp_path / "input.json").write_text(body, encoding="utf-8")
    with pytest.raises(BlockError) as exc:
        preview_file(tmp_path, "json")
    assert exc.value.failure.code == code


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "latin-1"])
def test_json_encodings_escapes_and_observed_counts(tmp_path: Path, encoding: str):
    rows = [{"text": 'café \\" } [,', "value": 1}, {"text": None, "value": 2.5}]
    (tmp_path / "input.json").write_bytes(
        json.dumps(rows, ensure_ascii=False).encode(encoding)
    )
    table, evidence = preview_file(tmp_path, "json", {"encoding": encoding})
    assert list(table.rows) == rows
    assert evidence.full_row_count == 2 and evidence.full_count_scope == "observed"
    assert evidence.schema_scope == "sample" and not evidence.truncated
    assert all(c.nullable for c in table.data_schema.columns)


def test_json_prefix_is_bounded_and_tail_is_not_validated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "input.json").write_text(
        '[{"v":1},{"v":2},{"v":3},' + "bad" * 100000, encoding="utf-8"
    )

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("No eager reads")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    table, evidence = preview_file(tmp_path, "json")
    assert table.rows == ({"v": 1}, {"v": 2})
    assert evidence.inspected_rows == 3 and evidence.read_bytes == 1024
    assert evidence.full_row_count is None and evidence.truncated


@pytest.mark.parametrize("suffix", ["json", "parquet"])
@pytest.mark.parametrize("empty", [False, True])
def test_declared_schema_empty_and_null_samples(
    tmp_path: Path, suffix: str, empty: bool
):
    rows: list[dict[str, Any]] = [] if empty else [{"v": None}]
    if suffix == "json":
        (tmp_path / "input.json").write_text(json.dumps(rows), encoding="utf-8")
    else:
        pq.write_table(
            pa.Table.from_pylist(rows, schema=pa.schema([("v", pa.int64())])),
            tmp_path / "input.parquet",
        )
    table, evidence = preview_file(
        tmp_path, suffix, {"columns": ["v"], "types": ["integer"], "nullable": [True]}
    )
    assert list(table.rows) == rows
    assert table.data_schema.columns[0].dtype == "integer"
    assert evidence.full_row_count == len(rows) and not evidence.truncated
    assert evidence.schema_scope == "declared"


@pytest.mark.parametrize("suffix", ["json", "parquet"])
def test_source_row_cell_byte_and_declared_cast_limits(tmp_path: Path, suffix: str):
    rows = [
        {"v": "1", "other": True},
        {"v": "2", "other": False},
        {"v": "3", "other": True},
    ]
    if suffix == "json":
        (tmp_path / "input.json").write_text(json.dumps(rows), encoding="utf-8")
    else:
        pq.write_table(
            pa.Table.from_pylist(rows), tmp_path / "input.parquet", row_group_size=2
        )
    table, evidence = preview_file(
        tmp_path,
        suffix,
        {
            "max_rows": 1,
            "columns": ["v", "other"],
            "types": ["integer", "boolean"],
            "nullable": [False, False],
        },
    )
    assert table.rows == ({"v": 1, "other": True},) and evidence.truncated
    assert len(preview_file(tmp_path, suffix, max_cells=2)[0].rows) == 1
    with pytest.raises(BlockError) as exc:
        preview_file(tmp_path, suffix, max_cells=1)
    assert exc.value.failure.code == "preview_limit"
    with pytest.raises(BlockError) as exc:
        preview_file(tmp_path, suffix, {"max_bytes": 8})
    assert exc.value.failure.code == "preview_read_limit"


def test_parquet_multiple_groups_metadata_and_empty(tmp_path: Path):
    path = tmp_path / "input.parquet"
    pq.write_table(pa.table({"v": list(range(9))}), path, row_group_size=2)
    table, evidence = preview_file(tmp_path, "parquet", max_rows=3)
    assert table.rows == ({"v": 0}, {"v": 1}, {"v": 2})
    assert evidence.full_row_count == 9 and evidence.full_count_scope == "file_metadata"
    assert evidence.inspected_rows == 3
    pq.write_table(pa.table({"v": pa.array([], type=pa.int64())}), path)
    table, evidence = preview_file(tmp_path, "parquet")
    assert not table.rows and table.data_schema.columns[0].dtype == "integer"
    assert evidence.full_row_count == 0 and evidence.inspected_rows == 0


def test_parquet_rejects_large_declared_decoding_before_batches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    pq.write_table(
        pa.table({"v": ["x" * 4000] * 2200}),
        tmp_path / "input.parquet",
        use_dictionary=False,
    )

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Must reject before decoding")

    monkeypatch.setattr(pq.ParquetFile, "iter_batches", forbidden)
    with pytest.raises(BlockError) as exc:
        preview_file(tmp_path, "parquet")
    assert exc.value.failure.code == "preview_decode_limit"


@pytest.mark.parametrize(
    "kind,code",
    [
        ("footer", "preview_decode_limit"),
        ("field", "preview_field_limit"),
        ("nested", "unsupported_type"),
        ("invalid", "invalid_parquet"),
    ],
)
def test_parquet_negative_inputs(tmp_path: Path, kind: str, code: str):
    path = tmp_path / "input.parquet"
    if kind == "footer":
        path.write_bytes(
            b"PAR1"
            + b"x" * (MAX_FOOTER_BYTES + 1)
            + (MAX_FOOTER_BYTES + 1).to_bytes(4, "little")
            + b"PAR1"
        )
    elif kind == "field":
        pq.write_table(pa.table({"v": ["x" * 4097]}), path)
    elif kind == "nested":
        pq.write_table(pa.table({"v": [[1, 2]]}), path)
    else:
        path.write_bytes(
            b"PAR1" + b"invalid metadata" + (16).to_bytes(4, "little") + b"PAR1"
        )
    with pytest.raises(BlockError) as exc:
        preview_file(tmp_path, "parquet")
    assert exc.value.failure.code == code


def test_parquet_actual_reads_and_cancellation():
    context = BlockContext("preview", "source")
    source = BudgetFile(io.BytesIO(b"1234567890"), 8, context)
    assert source.read(4) == b"1234"
    source.seek(0)
    assert source.read(4) == b"1234"
    with pytest.raises(BlockError) as exc:
        source.read(1)
    assert exc.value.failure.code == "preview_read_limit"
    assert source.read_bytes == 9
    stopped = BudgetFile(
        io.BytesIO(b"x"),
        MAX_DECODE_BYTES,
        BlockContext("preview", "source", is_cancelled=lambda: True),
    )
    with pytest.raises(BlockError) as exc:
        stopped.read(1)
    assert exc.value.failure.code == "cancelled"


def test_parquet_arrow_reads_preserve_budget_errors(tmp_path: Path):
    pq.write_table(pa.table({"v": list(range(1000))}), tmp_path / "input.parquet")
    # Enough for the explicit magic/footer-length checks, but not Arrow's reads.
    with pytest.raises(BlockError) as exc:
        preview_file(tmp_path, "parquet", {"max_bytes": 128})
    assert exc.value.failure.code == "preview_read_limit"


@pytest.mark.parametrize("suffix", ["json", "parquet"])
def test_new_source_cancellation_during_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suffix: str
):
    from threading import Event
    from app.blocks.file_preview import JsonRecords

    cancelled = Event()
    block: JsonSource | ParquetSource
    if suffix == "json":
        (tmp_path / "input.json").write_text(
            json.dumps([{"v": "x" * 3000}]), encoding="utf-8"
        )
        original_byte = JsonRecords.byte

        def read_byte(reader: JsonRecords) -> int:
            result = original_byte(reader)
            if reader.position == 1024:
                cancelled.set()
            return result

        monkeypatch.setattr(JsonRecords, "byte", read_byte)
        block = JsonSource()
    else:
        pq.write_table(pa.table({"v": [1, 2]}), tmp_path / "input.parquet")
        original_read = BudgetFile.read

        def read_parquet(reader: BudgetFile, size: int = -1) -> bytes:
            result = original_read(reader, size)
            if reader.read_bytes > 12:
                cancelled.set()
            return result

        monkeypatch.setattr(BudgetFile, "read", read_parquet)
        block = ParquetSource()
    with pytest.raises(BlockError) as exc:
        block.preview(
            {"resource_ref": f"input.{suffix}"},
            {},
            BlockContext(
                "preview",
                "source",
                workspace_root=tmp_path,
                is_cancelled=cancelled.is_set,
            ),
            PreviewLimits(),
        )
    assert exc.value.failure.code == "cancelled"
