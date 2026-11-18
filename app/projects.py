# AI contribution: 50% or more AI-generated
"""Database-backed project create/list/open operations."""

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select

from app.metadata.database import Database
from app.metadata.models import Project
from app.schemas.projects import ProjectCreate, ProjectPage, ProjectResponse
from app.workspace import effective_workspace_root, workspace_lock
from app.workspace_storage import (
    active_workspace_key,
    prepare_named_project,
    projects_filter,
    visible_project,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectNotFound(Exception):
    pass


def database(request: Request) -> Database:
    configured = cast(Database | None, request.app.state.database)
    if configured is None:
        raise RuntimeError("Metadata database is unavailable")
    requested = request.path_params.get("project_id")
    if requested is not None:
        try:
            identity = str(UUID(str(requested)))
        except ValueError:
            return configured  # Let FastAPI report malformed UUIDs as 422.
        with configured.transaction() as session:
            project = session.get(Project, identity)
            if project is None or not visible_project(project, configured):
                raise ProjectNotFound()
    return configured


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    payload: ProjectCreate, db: Annotated[Database, Depends(database)]
) -> ProjectResponse:
    with workspace_lock, db.transaction() as session:
        project = Project(name=payload.name, workspace_root=active_workspace_key(db))
        session.add(project)
        session.flush()
        root = effective_workspace_root(db)
        prepare_named_project(session, project, root)
        result = ProjectResponse.model_validate(project)
    return result


@router.get("", response_model=ProjectPage)
def list_projects(
    db: Annotated[Database, Depends(database)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProjectPage:
    with db.transaction() as session:
        scope = projects_filter(db)
        total = (
            session.scalar(select(func.count()).select_from(Project).where(scope)) or 0
        )
        rows = session.scalars(
            select(Project)
            .where(scope)
            .order_by(Project.created_at.desc(), Project.id)
            .offset(offset)
            .limit(limit)
        )
        return ProjectPage(
            items=[ProjectResponse.model_validate(row) for row in rows],
            total=total,
            offset=offset,
            limit=limit,
        )


@router.get("/{project_id}", response_model=ProjectResponse)
def open_project(
    project_id: UUID, db: Annotated[Database, Depends(database)]
) -> ProjectResponse:
    with db.transaction() as session:
        project = session.get(Project, str(project_id))
        if project is None:
            raise ProjectNotFound()
        return ProjectResponse.model_validate(project)
