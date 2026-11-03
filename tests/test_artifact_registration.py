"""Durable registration of atomically published file-sink artifacts (#28)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import select

from app.blocks.contracts import Table
from app.blocks.files import ARTIFACT_SCHEMA
from app.blocks.sample import VALUE_SCHEMA
from app.execution import ExecutionContext, Frame
from app.execution.runtime import State
from app.metadata.database import Database
from app.metadata.migrate import upgrade
from app.metadata.models import OutputEndpoint, Run
from app.pipelines.models import Node, PipelineDefinition
from app.runs import RunRecorder
from tests.run_support import seed_revision


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "artifacts.sqlite3")
    upgrade(database)
    yield database
    database.close()


def definition() -> PipelineDefinition:
    return PipelineDefinition(
        nodes=(
            Node(
                id="sink",
                block_id="sink.parquet",
                block_version="1.0.0",
            ),
        )
    )


def artifact(format_: str = "parquet") -> Frame:
    return Frame.from_table(
        Table(
            data_schema=ARTIFACT_SCHEMA,
            rows=(
                {
                    "location": "outputs/result.parquet",
                    "format": format_,
                    "row_count": 2,
                    "schema_json": VALUE_SCHEMA.model_dump_json(),
                },
            ),
        )
    )


def context(format_: str = "parquet", state: State = "completed") -> ExecutionContext:
    source = Table(
        data_schema=VALUE_SCHEMA,
        rows=({"value": 1}, {"value": 2}),
    )
    return ExecutionContext(
        "run",
        state="completed" if state == "completed" else "failed",
        node_states={"sink": state},
        inputs={"sink": {"table": (Frame.from_table(source),)}},
        outputs={"sink": {"artifact": (artifact(format_),)}},
    )


def recorder(db: Database) -> RunRecorder:
    graph = definition()
    revision_id = seed_revision(db, graph.model_dump(mode="json"))
    return RunRecorder(db, "run", revision_id, graph)


def test_completed_sink_registers_bounded_metadata_and_provenance(db: Database):
    assert recorder(db).finish(context(), cancelled=False) == "succeeded"

    with db.transaction() as session:
        output = session.scalars(select(OutputEndpoint)).one()
        run = session.get(Run, "run")
        assert run is not None
        assert (output.run_id, output.node_id, output.name) == (
            "run",
            "sink",
            "artifact",
        )
        assert (output.format, output.artifact_ref, output.row_count) == (
            "parquet",
            "outputs/result.parquet",
            2,
        )
        assert output.schema_json == VALUE_SCHEMA.model_dump(mode="json")
        assert run.row_count == 2  # consumed data rows, not one metadata row


def test_failed_sink_does_not_register_an_artifact(db: Database):
    recorder(db).finish(context(state="failed"), cancelled=False)
    with db.transaction() as session:
        assert session.scalars(select(OutputEndpoint)).all() == []


def test_mismatched_sink_format_is_rejected_atomically(db: Database):
    with pytest.raises(ValueError, match="format"):
        recorder(db).finish(context("csv"), cancelled=False)
    with db.transaction() as session:
        assert session.scalars(select(OutputEndpoint)).all() == []
        assert session.get(Run, "run") is None
