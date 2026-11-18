# AI contribution: 50% or more AI-generated
"""Workspace-scoped metadata and safe, human-readable project/pipeline directories."""

import os
from pathlib import Path
import re
import shutil
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from threading import Lock, RLock

from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.metadata.database import Database
from app.metadata.models import Pipeline, Project
from app.workspace import (
    WorkspaceError,
    _store_setting,
    effective_workspace_root,
    prepare_project,
    project_data_folder,
    workspace_choice,
    workspace_lock,
)

_pipeline_locks: dict[str, RLock] = {}
_pipeline_locks_guard = Lock()


@contextmanager
def pipeline_storage(pipeline_id: str, *, wait: bool = False) -> Iterator[None]:
    """Keep folder renames from racing execution or timer publication."""
    with _pipeline_locks_guard:
        lock = _pipeline_locks.setdefault(pipeline_id, RLock())
    if not lock.acquire(blocking=wait):
        raise WorkspaceError(
            "pipeline_busy",
            "This pipeline is running. Wait for it to finish before "
            "changing its folders or running it again.",
            409,
        )
    try:
        yield
    finally:
        lock.release()


def workspace_key(root: Path | None) -> str:
    return os.path.normcase(str(root.resolve())) if root is not None else ""


def active_workspace_key(db: Database) -> str:
    return workspace_key(effective_workspace_root(db))


def visible_project(project: Project, db: Database) -> bool:
    return (
        project.workspace_root is None
        or project.workspace_root == active_workspace_key(db)
    )


def projects_filter(db: Database) -> ColumnElement[bool]:
    return or_(
        Project.workspace_root == active_workspace_key(db),
        Project.workspace_root.is_(None),
    )


def directory_name(name: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", unicodedata.normalize("NFC", name))
    # Bound UTF-16 units as well as characters, leaving room for nested paths
    # and temporary access probes on Windows (including emoji names).
    value = (
        value.strip(" .")
        .encode("utf-16-le")[:96]
        .decode("utf-16-le", errors="ignore")
        .rstrip(" .")
        or "Untitled"
    )
    if value.split(".")[0].upper() in {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        value = "_" + value
    return value


def allocate_directory(
    name: str,
    parent: Path | None,
    reserved: list[str | None],
    *,
    exclude: str | None = None,
) -> str:
    occupied = {value.casefold() for value in reserved if value}
    try:
        if parent is not None and parent.is_dir():
            with os.scandir(parent) as entries:
                occupied.update(
                    entry.name.casefold() for entry in entries if entry.name != exclude
                )
    except OSError:
        raise WorkspaceError(
            "workspace_project_folder",
            "Project folders are unavailable. "
            "Check their permissions before continuing.",
        ) from None
    base = directory_name(name)
    candidate, suffix = base, 2
    while candidate.casefold() in occupied:
        candidate = f"{base} ({suffix})"
        suffix += 1
    return candidate


def prepare_named_project(
    session: Session, project: Project, root: Path | None
) -> Path | None:
    if project.directory_name is None:
        if root is not None:
            legacy = root / project.id
            for binding in project.bindings:
                if binding.local_path:
                    path = Path(binding.local_path)
                    if (
                        path.is_absolute()
                        and ".." not in path.parts
                        and path.is_relative_to(legacy)
                    ):
                        binding.local_path = str(path.relative_to(legacy))
        reserved = list(
            session.scalars(
                select(Project.directory_name).where(
                    Project.workspace_root == project.workspace_root,
                    Project.id != project.id,
                )
            )
        )
        project.directory_name = allocate_directory(project.name, root, reserved)
    if root is None:
        return None
    prepare_project(root, project.directory_name, inputs_folder=False)
    return project_data_folder(root, project.directory_name)


def copy_legacy_tree(source: Path, destination: Path) -> None:
    """Reject links throughout the source; copy into a new folder without overwrites."""

    def validate(folder: Path) -> None:
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.is_symlink() or entry.is_junction():
                    raise WorkspaceError(
                        "workspace_project_folder",
                        "Legacy data contains links. "
                        "Move the data into real folders before migrating.",
                    )
                if entry.is_dir(follow_symlinks=False):
                    validate(Path(entry.path))

    try:
        validate(source)
        shutil.copytree(source, destination)
    except OSError:
        raise WorkspaceError(
            "workspace_project_folder",
            "Legacy data could not be copied. The original folders have been retained.",
        ) from None


def prepare_named_pipeline(
    session: Session, pipeline: Pipeline, root: Path | None
) -> Path | None:
    parent = prepare_named_project(session, pipeline.project, root)
    if pipeline.directory_name is None:
        reserved = list(
            session.scalars(
                select(Pipeline.directory_name).where(
                    Pipeline.project_id == pipeline.project_id,
                    Pipeline.id != pipeline.id,
                )
            )
        )
        pipeline.directory_name = allocate_directory(pipeline.name, parent, reserved)
    if parent is None or root is None:
        return None
    destination = parent / pipeline.directory_name
    if not destination.exists():
        # Old installations shared <workspace>/<UUID> among their pipelines.
        legacy = root / pipeline.project_id
        if (
            legacy.is_symlink()
            or legacy.is_junction()
            or (legacy.exists() and not legacy.is_dir())
        ):
            raise WorkspaceError(
                "workspace_project_folder",
                "The legacy project folder is unavailable or aliases another folder.",
            )
        if legacy.is_dir():
            copy_legacy_tree(legacy, destination)
    prepare_project(parent, pipeline.directory_name)
    return project_data_folder(parent, pipeline.directory_name)


def pipeline_data_folder(
    db: Database, pipeline_id: str, *, root: Path | None = None
) -> Path:
    with db.transaction() as session:
        pipeline = session.get(Pipeline, pipeline_id)
        if pipeline is None:
            raise ValueError("Pipeline is unavailable")
        project = pipeline.project
        base = root or (
            Path(project.workspace_root)
            if project.workspace_root
            else effective_workspace_root(db)
        )
        if base is None:
            raise ValueError("Workspace is not configured")
        if not project.directory_name or not pipeline.directory_name:
            # Compatibility for legacy metadata created by standalone engine clients.
            return project_data_folder(base, project.id)
        return project_data_folder(
            project_data_folder(base, project.directory_name), pipeline.directory_name
        )


def initialize_workspace_storage(db: Database) -> None:
    """Assign pre-upgrade metadata to its current workspace, retaining legacy data."""
    root = effective_workspace_root(db)
    with workspace_lock, db.transaction(write=True) as session:
        for project in session.scalars(
            select(Project).where(Project.workspace_root.is_(None))
        ):
            project.workspace_root = workspace_key(root)
            prepare_named_project(session, project, root)
            for pipeline in project.pipelines:
                prepare_named_pipeline(session, pipeline, root)


def switch_workspace(db: Database, root: Path | None, override: Path | None) -> None:
    try:
        previous, source = workspace_choice(db)
    except WorkspaceError:
        previous, source = None, "unconfigured"
    previous_override = previous if source == "application" else None
    stored = False
    try:
        with db.transaction(write=True) as session:
            for project in session.scalars(select(Project)):
                if project.workspace_root is None:
                    project.workspace_root = workspace_key(previous or root)
                elif (
                    project.workspace_root == ""
                    and previous is None
                    and root is not None
                ):
                    project.workspace_root = workspace_key(root)
                    project.directory_name = None
                    for pipeline in project.pipelines:
                        pipeline.directory_name = None
                if project.workspace_root == workspace_key(root):
                    prepare_named_project(session, project, root)
                    for pipeline in project.pipelines:
                        prepare_named_pipeline(session, pipeline, root)
            _store_setting(db, override)
            stored = True
    except BaseException:
        if stored:
            _store_setting(db, previous_override)
        raise
