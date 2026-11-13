# AI contribution: below 50% AI-generated
"""Read-only metadata and bounded local Parquet query endpoints (#28)."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.artifacts.query import (
    ArtifactQuery,
    RegisteredArtifact,
    get_artifact,
    query_artifact,
)
from app.artifacts import ArtifactUnavailable
from app.workspace import effective_workspace_root, project_data_folder
from app.metadata.database import Database
from app.projects import database
from app.schemas.artifacts import ArtifactMetadataResponse, ArtifactQueryResponse

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


def workspace_root(db: Annotated[Database, Depends(database)]) -> Path:
    root = effective_workspace_root(db)
    if root is None:
        raise ArtifactUnavailable("Workspace is not configured.")
    return root


def metadata(artifact: RegisteredArtifact) -> ArtifactMetadataResponse:
    return ArtifactMetadataResponse(
        id=artifact.id,
        run_id=artifact.run_id,
        pipeline_revision_id=artifact.pipeline_revision_id,
        pipeline_id=artifact.pipeline_id,
        project_id=artifact.project_id,
        node_id=artifact.node_id,
        name=artifact.name,
        format=artifact.format,  # type: ignore[arg-type]  # database CHECK constraint
        resource_ref=artifact.artifact_ref,
        row_count=artifact.row_count,
        data_schema=artifact.schema,
        created_at=artifact.created_at,
    )


@router.get("/{artifact_id}", response_model=ArtifactMetadataResponse)
def artifact_metadata(
    artifact_id: UUID,
    db: Annotated[Database, Depends(database)],
) -> ArtifactMetadataResponse:
    return metadata(get_artifact(db, str(artifact_id)))


@router.post("/{artifact_id}/query", response_model=ArtifactQueryResponse)
def artifact_query(
    artifact_id: UUID,
    payload: ArtifactQuery,
    db: Annotated[Database, Depends(database)],
) -> ArtifactQueryResponse:
    # Sinks publish under <workspace>/<project>/<resource_ref> (execute, #29),
    # so the query must resolve the artifact inside the same project folder
    # instead of the bare workspace root (#37 integration matrix). The folder
    # is checked for links/aliases first: resource_path trusts its root. The
    # root is read from saved settings here, as the execute API does, rather
    # than injected as a handler parameter.
    artifact = get_artifact(db, str(artifact_id))
    try:
        folder = project_data_folder(workspace_root(db), artifact.project_id)
    except ValueError:
        raise ArtifactUnavailable("Registered artifact is unavailable.") from None
    result = query_artifact(db, str(artifact_id), folder, payload)
    return ArtifactQueryResponse(
        artifact_id=result.artifact_id,
        run_id=result.run_id,
        pipeline_revision_id=result.pipeline_revision_id,
        columns=list(result.columns),
        rows=[list(row) for row in result.rows],
        offset=result.offset,
        limit=result.limit,
        has_more=result.has_more,
    )
