# AI contribution: below 50% AI-generated
"""Project-scoped authoring persistence with atomic, optimistic revisions (#14)."""

import json
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.blocks.catalog import executor, registry
from app.blocks.triggers import TimerTriggerConfig
from app.metadata.database import Database
from app.metadata.models import Pipeline, PipelineRevision, Project
from app.pipelines.models import GraphDraft, Node, PipelineDefinition
from app.pipelines.validation import ValidationReport, validate
from app.projects import ProjectNotFound, database
from app.runs import RevisionNotFound, execute_revision
from app.runs.scheduler import (
    TimerAlreadyRunning,
    TimerNotRunning,
    TimerScheduler,
    scheduler,
)
from app.schemas.execute import ExecuteResponse, TimerStatusResponse
from app.schemas.projects import ProjectCreate

router = APIRouter(prefix="/api/v1/projects/{project_id}/pipelines", tags=["pipelines"])
validation_router = APIRouter(prefix="/api/v1/pipelines", tags=["pipelines"])


class ValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    definition: GraphDraft

    @field_validator("definition", mode="before")
    @classmethod
    def draft_graph(cls, value: Any) -> GraphDraft:
        # Strict contracts accept JSON arrays as tuples only in JSON mode.
        if not isinstance(value, dict):
            raise ValueError("The definition must be a JSON object.")
        return GraphDraft.model_validate_json(json.dumps(value))


@validation_router.post("/validate", response_model=ValidationReport)
def validate_pipeline(payload: ValidationRequest) -> ValidationReport:
    """Check an unsaved draft for execution readiness; never runs blocks (#21).

    A well-formed request always returns 200 with ``valid`` and diagnostics.
    Malformed JSON, unsupported versions and nonportable configuration remain
    422 errors, matching the save boundary.
    """
    return validate(payload.definition, registry)


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


def latest_revision(
    session: Session, project_id: UUID, pipeline_id: UUID
) -> PipelineRevision:
    """The latest saved revision row, for execute/timer (#29): needs the
    revision's own id, which ``load``'s ``PipelineResponse`` does not carry.
    """
    require_project(session, project_id)
    revision = session.scalar(
        select(PipelineRevision)
        .join(Pipeline)
        .where(Pipeline.id == str(pipeline_id), Pipeline.project_id == str(project_id))
        .order_by(PipelineRevision.revision.desc())
        .limit(1)
    )
    if revision is None:
        raise PipelineError("pipeline_not_found", "Pipeline was not found.", 404)
    return revision


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


def load_latest_definition(
    db: Database, project_id: UUID, pipeline_id: UUID
) -> tuple[str, PipelineDefinition]:
    """The latest revision's id and parsed definition, for execute/timer (#29)."""
    with db.transaction() as session:
        revision = latest_revision(session, project_id, pipeline_id)
        revision_id, stored = revision.id, revision.definition
    return revision_id, PipelineDefinition.from_json(json.dumps(stored))


def find_trigger(definition: PipelineDefinition, block_id: str) -> Node | None:
    """The first node using the given trigger block, if any (#29).

    A pipeline is expected to have at most one trigger node; a second one is
    simply ignored here rather than specially rejected, since the structural
    graph rules (#21) already do not require a trigger at all.
    """
    return next((node for node in definition.nodes if node.block_id == block_id), None)


@router.post("/{pipeline_id}/execute", response_model=ExecuteResponse, status_code=201)
def execute_pipeline(
    project_id: UUID,
    pipeline_id: UUID,
    db: Annotated[Database, Depends(database)],
) -> ExecuteResponse:
    """Run the latest saved revision now and return its run ID (#29).

    Invalid pipelines (unavailable blocks, missing required input, etc.) are
    refused with a structured ``invalid_pipeline`` error and create no run,
    exactly like a direct ``execute_revision`` call.
    """
    revision_id, _ = load_latest_definition(db, project_id, pipeline_id)
    try:
        outcome = execute_revision(db, executor, revision_id)
    except RevisionNotFound:
        raise PipelineError(
            "pipeline_not_found", "Pipeline was not found.", 404
        ) from None
    return ExecuteResponse(
        run_id=outcome.run_id,
        state=outcome.state,  # type: ignore[arg-type]  # recorder only sets terminal states
    )


@router.post(
    "/{pipeline_id}/timer/start", response_model=TimerStatusResponse, status_code=201
)
def start_timer(
    project_id: UUID,
    pipeline_id: UUID,
    db: Annotated[Database, Depends(database)],
    sched: Annotated[TimerScheduler, Depends(scheduler)],
) -> TimerStatusResponse:
    """Start the bounded interval timer for this pipeline's Timer trigger (#29).

    The interval comes from the saved ``trigger.timer`` node's own config, not
    the request, so the same saved definition can be started without edits.
    """
    revision_id, definition = load_latest_definition(db, project_id, pipeline_id)
    node = find_trigger(definition, "trigger.timer")
    if node is None:
        raise PipelineError(
            "timer_trigger_missing",
            "This pipeline has no Timer trigger node. Add one before starting a timer.",
            422,
        )
    try:
        config = TimerTriggerConfig.model_validate(node.config)
    except ValidationError:
        raise PipelineError(
            "invalid_trigger_config",
            "The Timer trigger's configuration is invalid.",
            422,
        ) from None
    try:
        sched.start(str(pipeline_id), revision_id, config.interval_seconds)
    except TimerAlreadyRunning:
        raise PipelineError(
            "timer_already_running",
            "A timer is already running for this pipeline. Stop it first.",
            409,
        ) from None
    return TimerStatusResponse(
        running=True, revision_id=revision_id, interval_seconds=config.interval_seconds
    )


@router.post("/{pipeline_id}/timer/stop", response_model=TimerStatusResponse)
def stop_timer(
    project_id: UUID,
    pipeline_id: UUID,
    db: Annotated[Database, Depends(database)],
    sched: Annotated[TimerScheduler, Depends(scheduler)],
) -> TimerStatusResponse:
    with db.transaction() as session:
        latest_revision(session, project_id, pipeline_id)
    try:
        sched.stop(str(pipeline_id))
    except TimerNotRunning:
        raise PipelineError(
            "timer_not_running", "No timer is running for this pipeline.", 404
        ) from None
    return TimerStatusResponse(running=False)


@router.get("/{pipeline_id}/timer", response_model=TimerStatusResponse)
def get_timer_status(
    project_id: UUID,
    pipeline_id: UUID,
    db: Annotated[Database, Depends(database)],
    sched: Annotated[TimerScheduler, Depends(scheduler)],
) -> TimerStatusResponse:
    with db.transaction() as session:
        latest_revision(session, project_id, pipeline_id)
    status = sched.status(str(pipeline_id))
    if status is None:
        return TimerStatusResponse(running=False)
    return TimerStatusResponse(
        running=True,
        revision_id=status.revision_id,
        interval_seconds=status.interval_seconds,
    )
