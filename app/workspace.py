"""Private local workspace settings; never part of portable pipeline definitions."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.config import settings
from app.metadata.database import Database
from app.metadata.models import Project

router = APIRouter(prefix="/api/v1/settings/workspace", tags=["settings"])
workspace_lock = RLock()


class WorkspaceError(Exception):
    def __init__(self, code: str, message: str, status: int = 422) -> None:
        self.code, self.message, self.status = code, message, status


class WorkspaceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    root_path: str | None = Field(max_length=4096)


class WorkspaceStatus(BaseModel):
    root_path: str | None
    source: Literal["application", "environment", "unconfigured"]
    ready: bool
    message: str
    allowed_roots: list[str]


def database(request: Request) -> Database:
    return cast(Database, request.app.state.database)


def settings_file(db: Database) -> Path:
    # Database-specific sidecar keeps separate installations and tests isolated.
    return db.path.with_name(db.path.name + ".workspace.json")


def workspace_choice(
    db: Database,
) -> tuple[Path | None, Literal["application", "environment", "unconfigured"]]:
    try:
        with settings_file(db).open("rb") as stream:
            data = stream.read(16385)
        if len(data) > 16384:
            raise ValueError("Oversized settings")
        saved = WorkspaceUpdate.model_validate_json(data)
        if (
            saved.root_path is None
            or "\x00" in saved.root_path
            or not Path(saved.root_path).is_absolute()
        ):
            raise ValueError("Invalid saved root")
        return Path(saved.root_path), "application"
    except FileNotFoundError:
        if settings.workspace_root is not None:
            return settings.workspace_root.resolve(), "environment"
        return None, "unconfigured"
    except (OSError, ValueError):
        raise WorkspaceError(
            "workspace_settings_unavailable",
            "Saved workspace settings could not be read. "
            "Save a valid root to repair them.",
            503,
        ) from None


def effective_workspace_root(db: Database) -> Path | None:
    return workspace_choice(db)[0]


def allowed_roots(db: Database) -> list[Path]:
    """Only trusted startup configuration supplies filesystem candidates."""
    roots = [db.path.parent / "workspaces", *settings.allowed_workspace_roots]
    if settings.workspace_root is not None:
        roots.append(settings.workspace_root)
    return list(dict.fromkeys(Path(os.path.abspath(root)) for root in roots))


def selected_root(value: str, db: Database) -> Path:
    # Compare lexically, BEFORE resolve/stat/open: even checking whether an
    # arbitrary path exists leaks filesystem information (and UNC can do I/O).
    for candidate in allowed_roots(db):
        if value == str(candidate):
            return checked_root(candidate)
    raise WorkspaceError(
        "workspace_invalid_path",
        "Choose an existing folder from the permitted workspace roots. "
        "Configure LPS_ALLOWED_WORKSPACE_ROOTS on the API computer for other folders.",
    )


def checked_root(path: Path) -> Path:
    if "\x00" in str(path) or not path.is_absolute():
        raise WorkspaceError(
            "workspace_invalid_path",
            "Enter an absolute folder path on the API computer.",
        )
    try:
        root = path.resolve(strict=True)
        if not root.is_dir():
            raise OSError
        # Verify actual access rather than relying only on permission bits.
        with os.scandir(root):
            pass
        with NamedTemporaryFile(prefix=".lps-access-", dir=root):
            pass
        return root
    except (OSError, ValueError):
        raise WorkspaceError(
            "workspace_invalid_path",
            "Choose an existing folder the API can read and write.",
        ) from None


def prepare_project(root: Path, project_id: str) -> None:
    try:
        base = root.resolve(strict=True)
        project = base / project_id
        inputs = project / "inputs"
        # Reject links/junctions before creating anything through them.
        if project.resolve() != project or inputs.resolve() != inputs:
            raise ValueError("Aliased project folder")
        inputs.mkdir(parents=True, exist_ok=True)
        with os.scandir(inputs):
            pass
        with NamedTemporaryFile(prefix=".lps-access-", dir=inputs):
            pass
    except (OSError, ValueError):
        raise WorkspaceError(
            "workspace_project_folder",
            "A project data folder is unavailable, unwritable or aliases "
            "another folder. Check the workspace folders.",
        ) from None


def status(db: Database) -> WorkspaceStatus:
    root, source = workspace_choice(db)
    ready = False
    if root is not None:
        try:
            ready = root.is_dir() and os.access(root, os.R_OK | os.W_OK | os.X_OK)
        except OSError:
            pass
    return WorkspaceStatus(
        root_path=str(root) if root else None,
        source=source,
        ready=ready,
        message=(
            "Workspace configured. Save to validate access and prepare project folders."
            if ready
            else "Select an existing workspace folder on the API computer."
        ),
        allowed_roots=[str(path) for path in allowed_roots(db)],
    )


@router.get("", response_model=WorkspaceStatus)
def get_workspace(
    response: Response, db: Annotated[Database, Depends(database)]
) -> WorkspaceStatus:
    response.headers["Cache-Control"] = "no-store"
    return status(db)


@router.put("", response_model=WorkspaceStatus)
def save_workspace(
    payload: WorkspaceUpdate,
    response: Response,
    db: Annotated[Database, Depends(database)],
) -> WorkspaceStatus:
    response.headers["Cache-Control"] = "no-store"
    with workspace_lock:
        # Null removes the app override and restores the startup environment.
        root = (
            selected_root(payload.root_path, db)
            if payload.root_path is not None
            else (
                checked_root(settings.workspace_root.absolute())
                if settings.workspace_root
                else None
            )
        )
        if root is not None:
            with db.transaction() as session:
                projects = list(session.scalars(select(Project.id)))
            for project in projects:
                prepare_project(root, project)
        temporary: Path | None = None
        try:
            if payload.root_path is None:
                settings_file(db).unlink(missing_ok=True)
            else:
                with NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=db.path.parent,
                    prefix=".workspace-",
                    suffix=".tmp",
                    delete=False,
                ) as stream:
                    temporary = Path(stream.name)
                    json.dump({"root_path": str(root)}, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, settings_file(db))
        except OSError:
            raise WorkspaceError(
                "workspace_save_failed",
                "Workspace settings could not be saved. "
                "The previous setting remains active.",
                503,
            ) from None
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
        return status(db)
