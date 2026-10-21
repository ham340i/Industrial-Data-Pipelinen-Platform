"""Logical golden output and failure-boundary regression tests."""

import json

import pyarrow.parquet as pq
import pytest

from app.blocks.errors import BlockError
from app.pipelines.models import GraphError, PipelineDefinition
from experiments.headless_etl.spike import FIXTURES, demo, execute


def definition():
    return json.loads((FIXTURES / "pipeline.json").read_text())


def test_golden_and_lifecycle():
    result = demo()
    assert result["verified"]
    assert [(e["node_id"], e["event"]) for e in result["events"]] == [
        (node, event)
        for node in ("source", "select", "sink")
        for event in ("started", "succeeded")
    ]


def test_empty_rows_and_column_order(tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("sensor_id,reading,unit\n")
    value = definition()
    value["nodes"][1]["config"]["columns"] = ["reading", "sensor_id"]
    output = tmp_path / "result.parquet"
    execute(
        PipelineDefinition.from_json(json.dumps(value)),
        {"input": source, "output": output},
        [],
    )
    table = pq.read_table(output)
    assert table.column_names == ["reading", "sensor_id"]
    assert table.num_rows == 0
    assert all(str(field.type) == "string" for field in table.schema)


@pytest.mark.parametrize("csv", ["", "a,a\n1,2\n", "a,b\n1\n", "a,b\n1,2,3\n"])
def test_bad_csv_stops_before_sink(tmp_path, csv):
    source = tmp_path / "input.csv"
    source.write_text(csv)
    output = tmp_path / "result.parquet"
    events = []
    with pytest.raises(BlockError) as error:
        execute(
            PipelineDefinition.from_json(json.dumps(definition())),
            {"input": source, "output": output},
            events,
        )
    assert error.value.failure.node_id == "source"
    assert events[-1].event == "failed"
    assert not output.exists()


def test_missing_column(tmp_path):
    value = definition()
    value["nodes"][1]["config"]["columns"] = ["absent"]
    output = tmp_path / "result.parquet"
    with pytest.raises(BlockError) as error:
        execute(
            PipelineDefinition.from_json(json.dumps(value)),
            {"input": FIXTURES / "input.csv", "output": output},
            [],
        )
    assert error.value.failure.code == "missing_column"
    assert error.value.failure.node_id == "select"
    assert not output.exists()


@pytest.mark.parametrize("change", ["duplicate", "version", "port"])
def test_invalid_graph_has_no_io(tmp_path, change):
    value = definition()
    if change == "duplicate":
        value["nodes"][1]["config"]["columns"] = ["reading", "reading"]
    elif change == "version":
        value["nodes"][2]["block_version"] = "99.0.0"
    else:
        value["edges"][0]["source"]["port"] = "unknown"
    events = []
    with pytest.raises(GraphError):
        execute(PipelineDefinition.from_json(json.dumps(value)), {}, events)
    assert events == []


def test_existing_output_preserved(tmp_path):
    output = tmp_path / "result.parquet"
    output.write_bytes(b"existing")
    with pytest.raises(BlockError) as error:
        execute(
            PipelineDefinition.from_json(json.dumps(definition())),
            {"input": FIXTURES / "input.csv", "output": output},
            [],
        )
    assert error.value.failure.node_id == "sink"
    assert output.read_bytes() == b"existing"


def test_failed_write_removes_partial_output(tmp_path, monkeypatch):
    output = tmp_path / "result.parquet"

    def fail(table, stream):
        stream.write(b"partial")
        raise OSError("private details")

    monkeypatch.setattr(pq, "write_table", fail)
    with pytest.raises(BlockError) as error:
        execute(
            PipelineDefinition.from_json(json.dumps(definition())),
            {"input": FIXTURES / "input.csv", "output": output},
            [],
        )
    assert "private details" not in str(error.value)
    assert not output.exists()
