# AI contribution: 50% or more AI-generated
"""Read-only run status and detail endpoints over persisted telemetry (#27)."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import Select, func, select

from app.metadata.database import Database
from app.metadata.models import Pipeline, PipelineRevision, Project, Run
from app.workspace_storage import projects_filter, visible_project
from app.runs.redaction import redact
from app.projects import database
from app.schemas.runs import (
    RunBlockDetail,
    RunDetail,
    RunEventDetail,
    RunFailure,
    RunOutputLink,
    RunPage,
    RunState,
    RunSummary,
)

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


class RunNotFound(Exception):
    pass


def failure(code: str | None, reason: str | None) -> RunFailure | None:
    if code is None:
        return None
    return RunFailure(code=code, reason=reason or "No details recorded.")


def summarize(run: Run) -> RunSummary:
    revision = run.pipeline_revision
    return RunSummary(
        id=run.id,
        project_id=revision.pipeline.project_id,
        pipeline_id=revision.pipeline_id,
        pipeline_revision_id=revision.id,
        revision=revision.revision,
        state=run.state,  # type: ignore[arg-type]  # enforced by a CHECK constraint
        created_at=run.created_at,
        started_at=run.started_at,
        ended_at=run.ended_at,
        duration_ms=run.duration_ms,
        row_count=run.row_count,
        error=failure(run.error_code, run.error_reason),
    )


def describe(run: Run) -> RunDetail:
    blocks = [
        RunBlockDetail(
            position=b.position,
            node_id=b.node_id,
            block_id=b.block_id,
            block_version=b.block_version,
            state=b.state,  # type: ignore[arg-type]  # enforced by a CHECK constraint
            started_at=b.started_at,
            ended_at=b.ended_at,
            duration_ms=b.duration_ms,
            rows_in=b.rows_in,
            rows_out=b.rows_out,
            error=failure(b.error_code, b.error_reason),
        )
        for b in run.blocks
    ]
    outputs = sorted(run.outputs, key=lambda item: (item.created_at, item.id))
    return RunDetail(
        **summarize(run).model_dump(),
        blocks=blocks,
        events=[RunEventDetail.model_validate(event) for event in run.events],
        outputs=[RunOutputLink.model_validate(output) for output in outputs],
    )


def filtered(
    query: Select[Any],
    project_id: UUID | None,
    pipeline_id: UUID | None,
    state: RunState | None,
) -> Select[Any]:
    query = query.join(PipelineRevision).join(Pipeline)
    if project_id is not None:
        query = query.where(Pipeline.project_id == str(project_id))
    if pipeline_id is not None:
        query = query.where(Pipeline.id == str(pipeline_id))
    if state is not None:
        query = query.where(Run.state == state)
    return query


@router.get("", response_model=RunPage)
def list_runs(
    db: Annotated[Database, Depends(database)],
    project_id: UUID | None = None,
    pipeline_id: UUID | None = None,
    state: RunState | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> RunPage:
    """Newest runs first, optionally narrowed to a project, pipeline or state."""
    with db.transaction() as session:
        total = session.scalar(
            filtered(select(func.count(Run.id)), project_id, pipeline_id, state)
            .join(Project)
            .where(projects_filter(db))
        )
        runs = session.scalars(
            filtered(select(Run), project_id, pipeline_id, state)
            .join(Project)
            .where(projects_filter(db))
            .order_by(Run.created_at.desc(), Run.id)
            .offset(offset)
            .limit(limit)
        )
        # Workspace identity is private metadata, never part of portable graphs.
        return RunPage(
            items=[summarize(run) for run in runs],
            total=total or 0,
            offset=offset,
            limit=limit,
        )


@router.get("/{run_id}", response_model=RunDetail)
def get_run(run_id: UUID, db: Annotated[Database, Depends(database)]) -> RunDetail:
    """Full evidence for one run: block states, redacted log and artifacts."""
    with db.transaction() as session:
        run = session.get(Run, str(run_id))
        if run is None or not visible_project(
            run.pipeline_revision.pipeline.project, db
        ):
            raise RunNotFound()
        return describe(run)


@router.get("/{run_id}/log")
def download_run_log(
    run_id: UUID, db: Annotated[Database, Depends(database)]
) -> Response:
    """Download every persisted event and block result, with redaction retained."""
    with db.transaction() as session:
        run = session.get(Run, str(run_id))
        if run is None or not visible_project(
            run.pipeline_revision.pipeline.project, db
        ):
            raise RunNotFound()
        lines = [
            f"Run {run.id}",
            f"Result: {run.state}",
            f"Revision: {run.pipeline_revision.revision}",
            f"Duration: {run.duration_ms} ms"
            if run.duration_ms is not None
            else "Duration: Unknown",
            f"Rows: {run.row_count if run.row_count is not None else 'Unknown'}",
            "",
            "Blocks",
        ]
        for block in run.blocks:
            lines.append(
                redact(
                    f"{block.node_id} | {block.block_id} | {block.state} | "
                    f"duration={block.duration_ms} | rows_in={block.rows_in} | "
                    f"rows_out={block.rows_out}"
                )
            )
            if block.error_code:
                lines.append(redact(f"{block.error_code}: {block.error_reason}"))
        if run.error_code:
            lines.append(redact(f"Run error: {run.error_code}: {run.error_reason}"))
        lines.extend(["", "Events (credentials and machine paths redacted)"])
        for event in run.events:
            lines.append(
                f"{event.sequence} | {event.created_at.isoformat()} | {event.level} | "
                f"{redact(event.node_id or '-')} | "
                f"{redact(event.code or event.kind)} | "
                f"{redact(event.message)}"
            )
    return Response(
        "\n".join(lines) + "\n",
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="run-{run_id}.log"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
