"""Executor publication -> metadata -> bounded DuckDB acceptance path (#28)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import select

from app.artifacts import ArtifactQuery, query_artifact
from app.blocks.catalog import executor
from app.metadata.database import Database
from app.metadata.migrate import upgrade
from app.metadata.models import OutputEndpoint, Run
from app.runs import execute_revision
from tests.run_support import seed_revision


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "integration.sqlite3")
    upgrade(database)
    yield database
    database.close()


def pipeline() -> dict[str, object]:
    return {
        "schema_version": 1,
        "nodes": [
            {
                "id": "source",
                "block_id": "source.csv",
                "block_version": "1.0.0",
                "config": {
                    "resource_ref": "input.csv",
                    "columns": ["name", "value", "active"],
                    "types": ["string", "integer", "boolean"],
                    "nullable": [False, True, False],
                },
            },
            {
                "id": "sink",
                "block_id": "sink.parquet",
                "block_version": "1.0.0",
                "config": {
                    "resource_ref": "result.parquet",
                    "overwrite": "replace",
                },
            },
        ],
        "edges": [
            {
                "id": "source-to-sink",
                "source": {"node_id": "source", "port": "table"},
                "target": {"node_id": "sink", "port": "table"},
            }
        ],
    }


def test_executor_output_is_registered_and_queryable_by_artifact_id(
    db: Database, tmp_path: Path
):
    (tmp_path / "input.csv").write_text(
        "name,value,active\nalpha,1,true\nbeta,NULL,false\n", encoding="utf-8"
    )
    revision_id = seed_revision(db, pipeline())

    outcome = execute_revision(db, executor, revision_id, workspace_root=tmp_path)
    assert outcome.state == "succeeded", outcome.context.failures

    with db.transaction() as session:
        artifact = session.scalars(select(OutputEndpoint)).one()
        run = session.get(Run, outcome.run_id)
        assert run is not None
        assert artifact.run_id == outcome.run_id
        assert run.pipeline_revision_id == revision_id
        assert artifact.row_count == 2
        artifact_id = artifact.id

    result = query_artifact(
        db,
        artifact_id,
        tmp_path,
        ArtifactQuery(columns=["name", "value", "active"], limit=10),
    )
    assert result.pipeline_revision_id == revision_id
    assert result.rows == (("alpha", 1, True), ("beta", None, False))
    assert result.has_more is False
