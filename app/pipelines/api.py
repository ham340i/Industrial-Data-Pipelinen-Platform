"""Project-scoped authoring persistence with atomic, optimistic revisions (#14)."""

import json
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.metadata.database import Database
from app.metadata.models import Pipeline, PipelineRevision, Project
from app.pipelines.models import PipelineDefinition
from app.projects import ProjectNotFound, database
from app.schemas.projects import ProjectCreate

router = APIRouter(prefix="/api/v1/projects/{project_id}/pipelines", tags=["pipelines"])


class PipelineError(Exception):
    def __init__(self, code: str, message: str, status: int = 409) -> None:
        self.code, self.message, self.status = code, message, status


class PipelineCreate(ProjectCreate):
    definition: dict[str, Any]

    @field_validator("definition")
    @classmethod
    def portable_graph(cls, value: dict[str, Any]) -> dict[str, Any]:
        return PipelineDefinition.from_json(json.dumps(value)).to_dict()


class PipelineUpdate(PipelineCreate):
    expected_revision: int = Field(ge=1)


class PipelineRename(ProjectCreate):
    expected_revision: int = Field(ge=1)


class PipelineSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    name: str
    revision: int


class PipelineResponse(PipelineSummary):
    definition: dict[str, Any]


class PipelinePage(BaseModel):
    items: list[PipelineSummary]
    total: int
    offset: int
    limit: int


def require_project(session: Session, project_id: UUID) -> None:
    if session.get(Project, str(project_id)) is None:
        raise ProjectNotFound()


def load(session: Session, project_id: UUID, pipeline_id: UUID) -> PipelineResponse:
    require_project(session, project_id)
    row = session.execute(
        select(Pipeline, PipelineRevision)
        .join(PipelineRevision)
        .where(Pipeline.id == str(pipeline_id), Pipeline.project_id == str(project_id))
        .order_by(PipelineRevision.revision.desc())
        .limit(1)
    ).first()
    if row is None:
        raise PipelineError("pipeline_not_found", "Pipeline was not found.", 404)
    pipeline, revision = row
    return PipelineResponse(
        id=pipeline.id,
        project_id=pipeline.project_id,
        name=pipeline.name,
        revision=revision.revision,
        definition=revision.definition,
    )


@router.get("", response_model=PipelinePage)
def list_pipelines(
    project_id: UUID,
    db: Annotated[Database, Depends(database)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PipelinePage:
    with db.transaction() as session:
        require_project(session, project_id)
        total = (
            session.scalar(
                select(func.count())
                .select_from(Pipeline)
                .where(Pipeline.project_id == str(project_id))
            )
            or 0
        )
        rows = session.execute(
            select(Pipeline, func.max(PipelineRevision.revision))
            .join(PipelineRevision)
            .where(Pipeline.project_id == str(project_id))
            .group_by(Pipeline.id)
            .order_by(Pipeline.created_at.desc(), Pipeline.id)
            .offset(offset)
            .limit(limit)
        )
        return PipelinePage(
            items=[
                PipelineSummary(
                    id=p.id, project_id=p.project_id, name=p.name, revision=revision
                )
                for p, revision in rows
            ],
            total=total,
            offset=offset,
            limit=limit,
        )


@router.get("/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(
    project_id: UUID,
    pipeline_id: UUID,
    db: Annotated[Database, Depends(database)],
) -> PipelineResponse:
    with db.transaction() as session:
        return load(session, project_id, pipeline_id)


@router.post("", response_model=PipelineResponse, status_code=201)
def create_pipeline(
    project_id: UUID,
    payload: PipelineCreate,
    db: Annotated[Database, Depends(database)],
) -> PipelineResponse:
    try:
        with db.transaction(write=True) as session:
            require_project(session, project_id)
            pipeline = Pipeline(project_id=str(project_id), name=payload.name)
            session.add(pipeline)
            session.flush()
            session.add(
                PipelineRevision(
                    pipeline_id=pipeline.id, revision=1, definition=payload.definition
                )
            )
            session.flush()
            result = load(session, project_id, UUID(pipeline.id))
        return result
    except IntegrityError:
        raise PipelineError(
            "pipeline_name_conflict",
            "A pipeline with this name already exists. Choose another name.",
        ) from None


def update(
    db: Database,
    project_id: UUID,
    pipeline_id: UUID,
    payload: PipelineUpdate | PipelineRename,
) -> PipelineResponse:
    try:
        # BEGIN IMMEDIATE acquires the writer lock before reading the revision.
        with db.transaction(write=True) as session:
            previous = load(session, project_id, pipeline_id)
            if previous.revision != payload.expected_revision:
                raise PipelineError(
                    "revision_conflict",
                    "This pipeline changed since it was opened. "
                    "Open the latest version or save a copy.",
                )
            pipeline = session.get(Pipeline, str(pipeline_id))
            assert pipeline is not None
            pipeline.name = payload.name
            definition = (
                payload.definition
                if isinstance(payload, PipelineUpdate)
                else previous.definition
            )
            session.add(
                PipelineRevision(
                    pipeline_id=pipeline.id,
                    revision=previous.revision + 1,
                    definition=definition,
                )
            )
            session.flush()
            result = load(session, project_id, pipeline_id)
        return result
    except IntegrityError:
        raise PipelineError(
            "pipeline_name_conflict",
            "A pipeline with this name already exists. Choose another name.",
        ) from None


@router.put("/{pipeline_id}", response_model=PipelineResponse)
def update_pipeline(
    project_id: UUID,
    pipeline_id: UUID,
    payload: PipelineUpdate,
    db: Annotated[Database, Depends(database)],
) -> PipelineResponse:
    return update(db, project_id, pipeline_id, payload)


@router.patch("/{pipeline_id}", response_model=PipelineResponse)
def rename_pipeline(
    project_id: UUID,
    pipeline_id: UUID,
    payload: PipelineRename,
    db: Annotated[Database, Depends(database)],
) -> PipelineResponse:
    return update(db, project_id, pipeline_id, payload)
