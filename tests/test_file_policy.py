# AI contribution: 50% or more AI-generated
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
from app.blocks.file_sinks import CsvSink, FileSink
from app.blocks.files import CsvSource, FileSource, JsonSource, ParquetSource
from app.blocks.parquet_decode import (
    MAX_PARQUET_DECODE_BYTES,
    PARQUET_DECODE_FACTOR,
    decoded_bytes,
    parquet_decode_budget,
    uncompressed_bytes,
)
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

    with patch("app.blocks.file_sinks.os.link", side_effect=competing_writer):
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


def write_repetitive_parquet(path: Path, rows: int, width: int) -> None:
    """A few hundred bytes on disk; ``rows * width`` bytes once decoded (#32)."""
    pq.write_table(
        pa.table({"payload": pa.array(["A" * width] * rows)}),
        path,
        compression="zstd",
    )


def test_parquet_dictionary_bomb_is_refused_before_expansion(tmp_path: Path):
    write_repetitive_parquet(tmp_path / "data.parquet", rows=2000, width=50_000)
    assert (tmp_path / "data.parquet").stat().st_size < 4096
    with pytest.raises(BlockError) as error:
        # Budget 16 x 1 MiB = 16 MiB; the file decodes to 100 MB.
        run(
            ParquetSource(),
            tmp_path,
            {"resource_ref": "data.parquet", "max_bytes": 1024 * 1024},
        )
    assert error.value.failure.code == "file_limit"


def test_parquet_large_declared_pages_are_refused_before_reading(tmp_path: Path):
    pq.write_table(
        pa.table({"payload": ["A" * 200_000]}),
        tmp_path / "data.parquet",
        compression="zstd",
        use_dictionary=False,
    )
    with patch.object(pq.ParquetFile, "read", side_effect=AssertionError("read")):
        with pytest.raises(BlockError) as error:
            run(
                ParquetSource(),
                tmp_path,
                {"resource_ref": "data.parquet", "max_bytes": 4096},
            )
    assert error.value.failure.code == "file_limit"


MIB = 1024 * 1024


@pytest.mark.parametrize(
    ("max_bytes", "budget"),
    [
        (1, PARQUET_DECODE_FACTOR),
        # The 16x factor and the 1 GiB cap meet at max_bytes = 64 MiB.
        (64 * MIB - 1, PARQUET_DECODE_FACTOR * (64 * MIB - 1)),
        (64 * MIB, MAX_PARQUET_DECODE_BYTES),
        (64 * MIB + 1, MAX_PARQUET_DECODE_BYTES),
        (128 * MIB, MAX_PARQUET_DECODE_BYTES),  # largest allowed max_bytes
    ],
)
def test_parquet_decode_budget_is_sixteen_times_capped_at_one_gib(
    max_bytes: int, budget: int
):
    assert parquet_decode_budget(max_bytes) == budget


def test_parquet_declared_pages_just_within_and_just_over_the_budget(
    tmp_path: Path,
):
    path = tmp_path / "data.parquet"
    pq.write_table(
        pa.table({"payload": ["A" * 200_000]}),
        path,
        compression="zstd",
        use_dictionary=False,
    )
    declared = uncompressed_bytes(pq.ParquetFile(path).metadata)
    # Smallest max_bytes whose budget holds the declared pages; one less
    # leaves the budget 1 to 16 bytes short. The on-disk size fits both.
    fits = -(-declared // PARQUET_DECODE_FACTOR)
    assert parquet_decode_budget(fits) >= declared
    assert parquet_decode_budget(fits - 1) < declared
    assert path.stat().st_size <= fits - 1
    config = {"resource_ref": "data.parquet"}
    table = run(ParquetSource(), tmp_path, {**config, "max_bytes": fits})
    assert [len(str(row["payload"])) for row in table.rows] == [200_000]
    with patch.object(pq.ParquetFile, "read", side_effect=AssertionError("read")):
        with pytest.raises(BlockError) as error:
            run(ParquetSource(), tmp_path, {**config, "max_bytes": fits - 1})
    assert error.value.failure.code == "file_limit"


@pytest.mark.parametrize(("over_cap", "allowed"), [(0, True), (1, False)])
def test_parquet_declared_pages_at_the_one_gib_cap(
    tmp_path: Path, over_cap: int, allowed: bool
):
    # A real 1 GiB declared file is too heavy for CI, so the declared size is
    # substituted; the comparison and the capped budget are the real ones.
    pq.write_table(pa.table({"a": [1, 2]}), tmp_path / "data.parquet")
    config = {"resource_ref": "data.parquet", "max_bytes": 128 * MIB}
    declared = MAX_PARQUET_DECODE_BYTES + over_cap
    with patch("app.blocks.files.uncompressed_bytes", return_value=declared):
        if allowed:
            assert len(run(ParquetSource(), tmp_path, config).rows) == 2
            return
        with patch.object(pq.ParquetFile, "read", side_effect=AssertionError):
            with pytest.raises(BlockError) as error:
                run(ParquetSource(), tmp_path, config)
    assert error.value.failure.code == "file_limit"


def test_parquet_row_count_is_checked_from_metadata_before_decoding(tmp_path: Path):
    pq.write_table(pa.table({"a": list(range(50))}), tmp_path / "data.parquet")
    with patch.object(pq.ParquetFile, "read", side_effect=AssertionError("read")):
        with pytest.raises(BlockError) as error:
            run(
                ParquetSource(),
                tmp_path,
                {"resource_ref": "data.parquet", "max_rows": 10},
            )
    assert error.value.failure.code == "table_limit"


def test_dictionary_strings_within_budget_decode_to_plain_values(tmp_path: Path):
    pq.write_table(
        pa.table({"label": ["x", "y", None, "x"], "n": [1, 2, 3, 4]}),
        tmp_path / "data.parquet",
    )
    table = run(ParquetSource(), tmp_path, {"resource_ref": "data.parquet"})
    assert [row["label"] for row in table.rows] == ["x", "y", None, "x"]
    assert [c.dtype for c in table.data_schema.columns] == ["string", "integer"]


def test_decoded_bytes_counts_dictionary_expansion(tmp_path: Path):
    write_repetitive_parquet(tmp_path / "data.parquet", rows=1000, width=10_000)
    encoded = pq.ParquetFile(
        tmp_path / "data.parquet", read_dictionary=["payload"]
    ).read()
    assert encoded.nbytes < 100_000
    assert decoded_bytes(encoded) >= 1000 * 10_000


@pytest.mark.parametrize(
    ("base", "hook"), [(FileSource, "_read"), (FileSink, "_write")]
)
def test_file_block_hooks_are_abstract(base: type[Any], hook: str):
    """The format hooks are abstract methods, not runtime NotImplementedError."""
    assert hook in base.__abstractmethods__
    with pytest.raises(TypeError, match=hook):
        base()
