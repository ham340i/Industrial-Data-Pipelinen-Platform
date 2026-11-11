"""Bounded, registered-artifact-only DuckDB query policy (#28)."""

from collections.abc import Iterator
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError

from app.artifacts import (
    ArtifactNotFound,
    ArtifactNotQueryable,
    ArtifactQuery,
    ArtifactUnavailable,
    get_artifact,
    query_artifact,
)
from app.blocks.contracts import Column, DataSchema
from app.metadata.database import Database
from app.metadata.migrate import upgrade
from app.metadata.models import OutputEndpoint, Run
from tests.run_support import chain, seed_revision

SCHEMA = DataSchema(
    columns=(
        Column(name="label", dtype="string", nullable=True),
        Column(name="count", dtype="integer", nullable=False),
        Column(name="ratio", dtype="number", nullable=True),
        Column(name="active", dtype="boolean", nullable=False),
    )
)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "query.sqlite3")
    upgrade(database)
    yield database
    database.close()


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    output = root / "outputs"
    output.mkdir(parents=True)
    table = pa.Table.from_pylist(
        [
            {"label": "first", "count": 1, "ratio": 1.5, "active": True},
            {"label": None, "count": 2, "ratio": None, "active": False},
            {"label": "third", "count": 3, "ratio": 3.5, "active": True},
        ],
        schema=pa.schema(
            [
                pa.field("label", pa.string(), nullable=True),
                pa.field("count", pa.int64(), nullable=False),
                pa.field("ratio", pa.float64(), nullable=True),
                pa.field("active", pa.bool_(), nullable=False),
            ]
        ),
    )
    pq.write_table(table, output / "result.parquet")
    return root


def register(
    db: Database,
    *,
    artifact_id: str = "artifact",
    format_: str = "parquet",
    artifact_ref: str = "outputs/result.parquet",
) -> None:
    revision_id = seed_revision(db, chain("test.source"))
    with db.transaction(write=True) as session:
        session.add(Run(id="run", pipeline_revision_id=revision_id, state="succeeded"))
        session.add(
            OutputEndpoint(
                id=artifact_id,
                run_id="run",
                node_id="sink",
                name="artifact",
                format=format_,
                artifact_ref=artifact_ref,
                row_count=3,
                schema_json=SCHEMA.model_dump(mode="json"),
            )
        )


def test_projection_limit_types_and_provenance(db: Database, workspace: Path):
    register(db)
    result = query_artifact(
        db,
        "artifact",
        workspace,
        ArtifactQuery(columns=["active", "label", "ratio", "count"], limit=2),
    )

    assert result.artifact_id == "artifact"
    assert result.run_id == "run"
    assert result.pipeline_revision_id
    assert result.columns == ("active", "label", "ratio", "count")
    assert result.rows == (
        (True, "first", 1.5, 1),
        (False, None, None, 2),
    )
    assert result.has_more is True


def test_offset_and_end_of_result_are_bounded(db: Database, workspace: Path):
    register(db)
    result = query_artifact(db, "artifact", workspace, ArtifactQuery(offset=2, limit=2))
    assert result.rows == (("third", 3, 3.5, True),)
    assert result.has_more is False


def test_policy_rejects_sql_unknown_columns_and_oversized_requests(
    db: Database, workspace: Path
):
    register(db)
    with pytest.raises(ValidationError):
        ArtifactQuery.model_validate({"sql": "DELETE FROM anything"})
    with pytest.raises(ValidationError):
        ArtifactQuery(limit=501)
    with pytest.raises(ArtifactNotQueryable, match="not registered"):
        query_artifact(db, "artifact", workspace, ArtifactQuery(columns=["unknown"]))


def test_only_registered_parquet_artifacts_can_be_queried(
    db: Database, workspace: Path
):
    with pytest.raises(ArtifactNotFound):
        query_artifact(db, "missing", workspace, ArtifactQuery())
    register(db, artifact_id="csv", format_="csv")
    with pytest.raises(ArtifactNotQueryable, match="Parquet"):
        query_artifact(db, "csv", workspace, ArtifactQuery())


def test_registered_reference_cannot_escape_workspace(db: Database, workspace: Path):
    register(db, artifact_ref="../outside.parquet")
    with pytest.raises(ArtifactUnavailable, match="unavailable"):
        query_artifact(db, "artifact", workspace, ArtifactQuery())


def test_legacy_metadata_remains_readable_but_not_queryable(
    db: Database, workspace: Path
):
    register(db)
    with db.transaction(write=True) as session:
        output = session.get(OutputEndpoint, "artifact")
        assert output is not None
        output.schema_json = {}

    assert get_artifact(db, "artifact").schema is None
    with pytest.raises(ArtifactNotQueryable, match="not available"):
        query_artifact(db, "artifact", workspace, ArtifactQuery())
