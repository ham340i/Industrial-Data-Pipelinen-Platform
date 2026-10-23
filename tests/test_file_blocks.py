"""Requirements-derived reader/writer/SDK integration cases (#16, #20)."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
import pytest

from app.blocks.catalog import registry
from app.blocks.context import BlockContext, BlockEvent
from app.blocks.contracts import Column, DataSchema, Table
from app.blocks.errors import BlockError
from app.blocks.files import CsvSink, CsvSource, JsonSource, ParquetSink, ParquetSource
from app.blocks.registry import RegisteredBlock

FIXTURES = Path(__file__).parent / "fixtures" / "blocks"


def run(
    block: RegisteredBlock,
    root: Path,
    config: dict[str, Any],
    table: Table | None = None,
    events: list[BlockEvent] | None = None,
) -> Table:
    outputs = block.run(
        config,
        {} if table is None else {"table": (table,)},
        BlockContext(
            run_id="fixture",
            node_id="test",
            workspace_root=root,
            log_sink=events.append if events is not None else None,
        ),
    )
    value = next(iter(outputs.values()))[0]
    assert isinstance(value, Table)
    return value


def scalar_table(empty: bool = False) -> Table:
    return Table(
        data_schema=DataSchema(
            columns=(
                Column(name="name", dtype="string"),
                Column(name="count", dtype="integer", nullable=True),
                Column(name="reading", dtype="number"),
                Column(name="active", dtype="boolean"),
            )
        ),
        rows=()
        if empty
        else (
            {
                "name": "é, quoted\ntext",
                "count": 2**63 - 1,
                "reading": -3.125,
                "active": True,
            },
            {"name": "", "count": None, "reading": 0.0, "active": False},
        ),
    )


@pytest.mark.parametrize(
    "name",
    [
        "source.csv",
        "source.json",
        "source.parquet",
        "transform.select",
        "transform.rename",
        "transform.filter",
        "transform.cast",
        "transform.join",
        "transform.aggregate",
        "transform.sort",
        "sink.csv",
        "sink.parquet",
    ],
)
def test_registered(name: str):
    block = registry.resolve(name, "1.0.0")
    assert block.public_metadata()["config_schema"]["additionalProperties"] is False


def test_csv_encoding_null_and_schema(tmp_path: Path):
    (tmp_path / "data.csv").write_bytes(
        "name,count,active\ncafé,2,true\n, NULL,false\n".replace(
            " NULL", "NULL"
        ).encode("latin-1")
    )
    config = {
        "resource_ref": "data.csv",
        "encoding": "latin-1",
        "columns": ["name", "count", "active"],
        "types": ["string", "integer", "boolean"],
        "nullable": [False, True, False],
    }
    table = run(CsvSource(), tmp_path, config)
    assert table.rows == (
        {"name": "café", "count": 2, "active": True},
        {"name": "", "count": None, "active": False},
    )
    assert table.data_schema.columns[1].nullable
    with pytest.raises(BlockError, match="format, encoding"):
        run(CsvSource(), tmp_path, {"resource_ref": "data.csv"})


@pytest.mark.parametrize(
    "data", ["", "a,a\n1,2\n", "a, \n1,2\n", "a,b\n1\n", 'a\n"unterminated']
)
def test_invalid_csv(tmp_path: Path, data: str):
    (tmp_path / "bad.csv").write_text(data)
    with pytest.raises(BlockError):
        run(CsvSource(), tmp_path, {"resource_ref": "bad.csv"})


def test_header_only_csv(tmp_path: Path):
    (tmp_path / "empty.csv").write_text("name,value\n")
    table = run(CsvSource(), tmp_path, {"resource_ref": "empty.csv"})
    assert table.rows == ()
    assert [c.name for c in table.data_schema.columns] == ["name", "value"]


def test_json_records_and_nulls(tmp_path: Path):
    (tmp_path / "rows.json").write_text(
        '[{"n":1,"flag":true,"s":null},{"n":2,"flag":false,"s":"é"}]', encoding="utf-8"
    )
    table = run(JsonSource(), tmp_path, {"resource_ref": "rows.json"})
    assert table.rows[0] == {"n": 1, "flag": True, "s": None}
    assert [(c.dtype, c.nullable) for c in table.data_schema.columns] == [
        ("integer", False),
        ("boolean", False),
        ("string", True),
    ]


@pytest.mark.parametrize(
    "data",
    [
        "{",
        "{}",
        "[1]",
        '[{"a":1,"a":2}]',
        '[{"a":[]}]',
        '[{"a":1},{"b":2}]',
        '[{"a":true},{"a":1}]',
        '[{"a":NaN}]',
        '[{"a":Infinity}]',
        '[{"a":1},{"a":"1"}]',
    ],
)
def test_invalid_json(tmp_path: Path, data: str):
    (tmp_path / "bad.json").write_text(data)
    with pytest.raises(BlockError):
        run(JsonSource(), tmp_path, {"resource_ref": "bad.json"})


def test_empty_json_requires_schema(tmp_path: Path):
    (tmp_path / "empty.json").write_text("[]")
    with pytest.raises(BlockError) as error:
        run(JsonSource(), tmp_path, {"resource_ref": "empty.json"})
    assert error.value.failure.code == "schema_required"
    table = run(
        JsonSource(),
        tmp_path,
        {
            "resource_ref": "empty.json",
            "columns": ["n"],
            "types": ["integer"],
            "nullable": [False],
        },
    )
    assert table.rows == () and table.data_schema.columns[0].dtype == "integer"


@pytest.mark.parametrize(
    "config",
    [
        {"columns": ["a"]},
        {
            "columns": ["a", "a"],
            "types": ["string", "string"],
            "nullable": [True, True],
        },
        {"columns": ["a"], "types": ["object"], "nullable": [True]},
        {"max_bytes": 0},
        {"max_rows": True},
    ],
)
def test_invalid_source_configuration(tmp_path: Path, config: dict[str, Any]):
    with pytest.raises(BlockError) as error:
        run(CsvSource(), tmp_path, {"resource_ref": "data.csv", **config})
    assert error.value.failure.code == "invalid_config"


@pytest.mark.parametrize(
    "resource",
    [
        "../data.csv",
        "/data.csv",
        "C:/data.csv",
        "a\\b.csv",
        "a/../b.csv",
        "a//b.csv",
        "https://host/data.csv",
    ],
)
def test_path_rejection(tmp_path: Path, resource: str):
    for block in (CsvSource(), CsvSink()):
        with pytest.raises(BlockError) as error:
            run(
                block,
                tmp_path,
                {"resource_ref": resource},
                scalar_table() if isinstance(block, CsvSink) else None,
            )
        assert error.value.failure.code == "invalid_config"


def test_workspace_and_resolver_policy(tmp_path: Path):
    with pytest.raises(BlockError) as error:
        CsvSource().run({"resource_ref": "data.csv"}, {}, BlockContext("run", "node"))
    assert error.value.failure.code == "workspace_required"
    context = BlockContext(
        "run",
        "node",
        workspace_root=tmp_path,
        resolve_resource=lambda _: tmp_path.parent / "outside.csv",
    )
    with pytest.raises(BlockError) as error:
        CsvSource().run({"resource_ref": "data.csv"}, {}, context)
    assert error.value.failure.code == "unsafe_resource"
    assert str(tmp_path) not in str(error.value)


def test_symlink_escape(tmp_path: Path):
    outside = tmp_path.parent / (tmp_path.name + "-outside.csv")
    outside.write_text("a\n1\n")
    try:
        try:
            (tmp_path / "link.csv").symlink_to(outside)
        except OSError:
            pytest.skip("Host does not permit creating symbolic links")
        with pytest.raises(BlockError) as error:
            run(CsvSource(), tmp_path, {"resource_ref": "link.csv"})
        assert error.value.failure.code == "unsafe_resource"
    finally:
        outside.unlink()


def test_missing_unreadable_wrong_suffix(tmp_path: Path):
    with pytest.raises(BlockError) as error:
        run(CsvSource(), tmp_path, {"resource_ref": "missing.csv"})
    assert error.value.failure.code == "file_unavailable"
    (tmp_path / "data.csv").write_text("a\n1\n")
    with patch.object(Path, "read_bytes", side_effect=PermissionError("private path")):
        with pytest.raises(BlockError) as error:
            run(CsvSource(), tmp_path, {"resource_ref": "data.csv"})
        assert error.value.failure.code == "file_unavailable"
    with pytest.raises(BlockError) as error:
        run(CsvSource(), tmp_path, {"resource_ref": "data.txt"})
    assert error.value.failure.code == "unsafe_resource"


@pytest.mark.parametrize(
    "limit", [{"max_bytes": 1}, {"max_rows": 1}, {"max_columns": 1}, {"max_cells": 3}]
)
def test_csv_limits(tmp_path: Path, limit: dict[str, int]):
    (tmp_path / "data.csv").write_text("a,b\n1,2\n3,4\n")
    with pytest.raises(BlockError) as error:
        run(CsvSource(), tmp_path, {"resource_ref": "data.csv", **limit})
    assert error.value.failure.code in ("file_limit", "table_limit", "invalid_csv")


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("format_name", ["csv", "parquet"])
def test_round_trip_schema_metadata(tmp_path: Path, empty: bool, format_name: str):
    table = scalar_table(empty)
    sink = CsvSink() if format_name == "csv" else ParquetSink()
    source = CsvSource() if format_name == "csv" else ParquetSource()
    resource = "output." + format_name
    artifact = run(sink, tmp_path, {"resource_ref": resource}, table)
    assert artifact.rows == (
        {
            "location": resource,
            "format": format_name,
            "row_count": len(table.rows),
            "schema_json": table.data_schema.model_dump_json(),
        },
    )
    config: dict[str, Any] = {"resource_ref": resource}
    if format_name == "csv":
        config.update(
            columns=[c.name for c in table.data_schema.columns],
            types=[c.dtype for c in table.data_schema.columns],
            nullable=[c.nullable for c in table.data_schema.columns],
        )
    actual = run(source, tmp_path, config)
    assert actual == table
    if format_name == "parquet":
        schema = pq.read_schema(tmp_path / resource)
        assert schema.field("count").nullable
        assert not schema.field("active").nullable


def test_parquet_unsupported_and_corrupt(tmp_path: Path):
    pq.write_table(pa.table({"a": [[1, 2]]}), tmp_path / "nested.parquet")
    with pytest.raises(BlockError) as error:
        run(ParquetSource(), tmp_path, {"resource_ref": "nested.parquet"})
    assert error.value.failure.code == "unsupported_type"
    (tmp_path / "bad.parquet").write_bytes(b"broken")
    with pytest.raises(BlockError):
        run(ParquetSource(), tmp_path, {"resource_ref": "bad.parquet"})


@pytest.mark.parametrize(
    "sink,extension", [(CsvSink(), "csv"), (ParquetSink(), "parquet")]
)
def test_overwrite_and_failure_cleanup(
    tmp_path: Path, sink: RegisteredBlock, extension: str
):
    resource = "result." + extension
    target = tmp_path / resource
    target.write_bytes(b"original")
    events: list[BlockEvent] = []
    with pytest.raises(BlockError) as error:
        run(sink, tmp_path, {"resource_ref": resource}, scalar_table(), events)
    assert error.value.failure.code == "output_exists"
    assert target.read_bytes() == b"original"
    assert events[-1].event == "failed"
    with patch.object(type(sink), "_write", side_effect=OSError("private failure")):
        with pytest.raises(BlockError):
            run(
                sink,
                tmp_path,
                {"resource_ref": resource, "overwrite": "replace"},
                scalar_table(),
            )
    assert target.read_bytes() == b"original"
    assert not list(tmp_path.glob(".lps-*"))
    run(
        sink,
        tmp_path,
        {"resource_ref": resource, "overwrite": "replace"},
        scalar_table(),
    )
    assert target.read_bytes() != b"original"


@pytest.mark.parametrize(
    "operation,overwrite", [("link", "error"), ("replace", "replace")]
)
def test_publish_failure_cleanup(tmp_path: Path, operation: str, overwrite: str):
    with patch(
        "app.blocks.files.os." + operation, side_effect=OSError("not supported")
    ):
        with pytest.raises(BlockError) as error:
            run(
                CsvSink(),
                tmp_path,
                {"resource_ref": "out.csv", "overwrite": overwrite},
                scalar_table(),
            )
    assert error.value.failure.code == "write_failed"
    assert list(tmp_path.iterdir()) == []


def test_csv_null_marker_and_no_sink_preview(tmp_path: Path):
    table = Table(
        data_schema=DataSchema(columns=(Column(name="a", dtype="string"),)),
        rows=({"a": "NULL"},),
    )
    with pytest.raises(BlockError) as error:
        run(CsvSink(), tmp_path, {"resource_ref": "out.csv"}, table)
    assert error.value.failure.code == "ambiguous_null"
    with pytest.raises(BlockError) as error:
        CsvSink().preview(
            {"resource_ref": "out.csv"},
            {"table": (table,)},
            BlockContext("run", "node", workspace_root=tmp_path),
        )
    assert error.value.failure.code == "preview_unsupported"
    assert list(tmp_path.iterdir()) == []


def test_full_golden_pipeline(tmp_path: Path):
    (tmp_path / "input.csv").write_bytes((FIXTURES / "file_pipeline.csv").read_bytes())
    expected = json.loads((FIXTURES / "file_golden.json").read_text())
    table = run(
        registry.resolve("source.csv", "1.0.0"), tmp_path, {"resource_ref": "input.csv"}
    )
    for block_id, config, stage in (
        ("transform.select", {"columns": ["sensor", "reading"]}, "selected"),
        ("transform.cast", {"column": "reading", "dtype": "number"}, "cast"),
        (
            "transform.rename",
            {"columns": ["reading"], "names": ["temperature"]},
            "renamed",
        ),
        (
            "transform.filter",
            {"column": "temperature", "operator": "gt", "value_text": "0"},
            "filtered",
        ),
    ):
        table = run(registry.resolve(block_id, "1.0.0"), tmp_path, config, table)
        assert list(table.rows) == expected[stage]
    for extension in ("csv", "parquet"):
        run(
            registry.resolve("sink." + extension, "1.0.0"),
            tmp_path,
            {"resource_ref": "result." + extension},
            table,
        )
    assert (
        pq.read_table(tmp_path / "result.parquet").to_pylist() == expected["filtered"]
    )
    assert (
        tmp_path / "result.csv"
    ).read_text() == "sensor,temperature\nA,12.5\nD,3.25\n"
