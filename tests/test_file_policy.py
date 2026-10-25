"""Separate correctness pass: limits, partial writes and competing writers."""

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from app.blocks.context import BlockEvent
from app.blocks.contracts import Table
from app.blocks.errors import BlockError
from app.blocks.files import CsvSink, CsvSource, JsonSource, ParquetSource
from app.blocks.registry import RegisteredBlock
from tests.test_file_blocks import run, scalar_table


@pytest.mark.parametrize("extension", ["json", "parquet"])
@pytest.mark.parametrize(
    "limit", [{"max_bytes": 1}, {"max_rows": 1}, {"max_columns": 1}, {"max_cells": 3}]
)
def test_json_parquet_limits(tmp_path: Path, extension: str, limit: dict[str, int]):
    if extension == "json":
        (tmp_path / "data.json").write_text('[{"a":1,"b":2},{"a":3,"b":4}]')
        source: RegisteredBlock = JsonSource()
    else:
        pq.write_table(pa.table({"a": [1, 3], "b": [2, 4]}), tmp_path / "data.parquet")
        source = ParquetSource()
    with pytest.raises(BlockError) as error:
        run(source, tmp_path, {"resource_ref": "data." + extension, **limit})
    assert error.value.failure.code in ("file_limit", "table_limit")


@pytest.mark.parametrize(
    "config",
    [
        {"columns": ["wrong"], "types": ["string"], "nullable": [False]},
        {"columns": ["a"], "types": ["integer"], "nullable": [False]},
    ],
)
def test_declared_schema_rejects_mismatch_and_null(
    tmp_path: Path, config: dict[str, Any]
):
    (tmp_path / "data.csv").write_text("a\nNULL\n")
    with pytest.raises(BlockError) as error:
        run(CsvSource(), tmp_path, {"resource_ref": "data.csv", **config})
    assert error.value.failure.code == "schema_mismatch"


def test_partial_serialization_is_removed(tmp_path: Path):
    def partial(self: CsvSink, path: Path, table: Table, config: Any) -> None:
        path.write_bytes(b"partial")
        raise OSError("synthetic disk failure")

    events: list[BlockEvent] = []
    with patch.object(CsvSink, "_write", partial):
        with pytest.raises(BlockError):
            run(
                CsvSink(),
                tmp_path,
                {"resource_ref": "output.csv"},
                scalar_table(),
                events,
            )
    assert list(tmp_path.iterdir()) == []
    assert [event.event for event in events] == ["started", "failed"]


def test_no_clobber_publication_race(tmp_path: Path):
    link = os.link
    target = tmp_path / "output.csv"

    def competing_writer(source: Path, destination: Path) -> None:
        target.write_bytes(b"other writer")
        link(source, destination)

    with patch("app.blocks.files.os.link", side_effect=competing_writer):
        with pytest.raises(BlockError) as error:
            run(CsvSink(), tmp_path, {"resource_ref": "output.csv"}, scalar_table())
    assert error.value.failure.code == "output_exists"
    assert target.read_bytes() == b"other writer"
    assert not list(tmp_path.glob(".lps-*"))


def test_byte_limit_boundary_and_utf8_bom(tmp_path: Path):
    data = "a\né\n".encode("utf-8-sig")
    (tmp_path / "bom.csv").write_bytes(data)
    table = run(
        CsvSource(),
        tmp_path,
        {
            "resource_ref": "bom.csv",
            "encoding": "utf-8-sig",
            "max_bytes": len(data),
            "max_rows": 1,
            "max_columns": 1,
            "max_cells": 1,
        },
    )
    assert table.rows == ({"a": "é"},)


@pytest.mark.parametrize(
    "resource", ["CON.csv", "inputs/NUL.csv", "COM1.csv", "LPT9.csv"]
)
def test_windows_device_names_rejected(tmp_path: Path, resource: str):
    with pytest.raises(BlockError) as error:
        run(CsvSink(), tmp_path, {"resource_ref": resource}, scalar_table())
    assert error.value.failure.code == "invalid_config"


def test_input_numeric_range_and_precision(tmp_path: Path):
    for text in ('[{"n":9223372036854775808}]', '[{"n":9007199254740993},{"n":1.5}]'):
        (tmp_path / "numbers.json").write_text(text)
        with pytest.raises(BlockError) as error:
            run(JsonSource(), tmp_path, {"resource_ref": "numbers.json"})
        assert error.value.failure.code == "unsupported_value"
