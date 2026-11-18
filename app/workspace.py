# AI contribution: below 50% AI-generated
"""Private local workspace settings; never part of portable pipeline definitions."""

import json
import logging
import os
import subprocess
import sys
from sys import platform
from ipaddress import ip_address
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock, RLock
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.metadata.database import Database
from app.native_folder_picker import open_folder_dialog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings/workspace", tags=["settings"])
workspace_lock = RLock()
folder_picker_lock = Lock()


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


class WorkspacePickRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    initial_path: str | None = Field(default=None, max_length=4096)


class WorkspacePickResult(BaseModel):
    path: str | None


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


def local_workspace_request(request: Request) -> bool:
    """Full browsing requires a loopback peer/Host and a trusted browser origin.

    CORS alone does not prevent requests from hostile pages. Do not use
    forwarded host headers to grant local access (including DNS rebinding).
    Requests without Origin remain usable by local command-line clients.
    """
    origin = request.headers.get("origin")
    if (
        origin is not None
        and origin not in settings.allowed_origins
        and origin != str(request.base_url).rstrip("/")
    ) or (origin is None and request.headers.get("sec-fetch-site") == "cross-site"):
        raise WorkspaceError(
            "workspace_origin_denied",
            "Open workspace settings from the workbench to browse or save folders.",
            403,
        )
    if request.url.hostname not in {"localhost", "127.0.0.1", "::1"}:
        return False
    try:
        return (
            request.client is not None and ip_address(request.client.host).is_loopback
        )
    except ValueError:
        return False


def local_drives() -> list[Path]:
    # Mypy recognizes sys.platform guards for Windows-only stdlib APIs.
    if sys.platform == "win32":
        return [Path(drive) for drive in os.listdrives()]
    return [Path("/")]


def workspace_folder(
    value: str, db: Database, *, local: bool = False
) -> tuple[Path, Path]:
    """Validate containment before touching paths; reject links below trusted roots."""
    path = Path(value)
    if "\x00" in value or not path.is_absolute() or ".." in path.parts:
        raise WorkspaceError(
            "workspace_invalid_path", "Choose an existing absolute folder path."
        )
    roots = allowed_roots(db)
    if local:
        roots = [*local_drives(), *roots]
    # Only startup configuration may authorize network roots; arbitrary UNC/device paths
    # cannot cause network probes even for a local caller.
    boundary = next((root for root in roots if path.is_relative_to(root)), None)
    if boundary is None:
        raise WorkspaceError(
            "workspace_invalid_path",
            "Choose an existing folder inside one of the available locations.",
        )
    try:
        base = boundary.resolve(strict=True)
        folder = base
        for part in path.relative_to(boundary).parts:
            folder = folder / part
            if folder.is_symlink() or folder.is_junction():
                raise ValueError("Aliased folder")
        if not folder.is_dir():
            raise ValueError("Missing directory")
        return folder, base
    except (OSError, ValueError):
        raise WorkspaceError(
            "workspace_invalid_path",
            "Choose an existing folder the API can access without links or junctions.",
        ) from None


def selected_root(value: str, db: Database, *, local: bool = False) -> Path:
    folder, _ = workspace_folder(value, db, local=local)
    return checked_root(folder)


@router.post("/pick-folder", response_model=WorkspacePickResult)
def pick_workspace_folder(
    payload: WorkspacePickRequest,
    request: Request,
    response: Response,
    db: Annotated[Database, Depends(database)],
) -> WorkspacePickResult:
    response.headers["Cache-Control"] = "no-store"
    if not local_workspace_request(request) or platform != "win32":
        raise WorkspaceError(
            "workspace_picker_unavailable",
            "File Explorer selection requires the API to run locally on Windows. "
            "Enter a workspace folder path instead.",
            409,
        )
    if not folder_picker_lock.acquire(blocking=False):
        raise WorkspaceError(
            "workspace_picker_busy",
            "A folder picker is already open. Select a folder or cancel that window.",
            409,
        )
    try:
        initial_path = None
        if payload.initial_path:
            try:
                initial_path = str(
                    workspace_folder(payload.initial_path, db, local=True)[0]
                )
            except WorkspaceError:
                # An invalid draft path must not prevent choosing a valid folder.
                pass
        try:
            path = open_folder_dialog(initial_path)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            logger.info("Native workspace picker failed: %s", type(exc).__name__)
            raise WorkspaceError(
                "workspace_picker_failed",
                "The folder picker could not finish. "
                "Try Browse again or enter a folder path.",
                503,
            ) from None
        return WorkspacePickResult(
            path=str(workspace_folder(path, db, local=True)[0])
            if path is not None
            else None
        )
    finally:
        folder_picker_lock.release()


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


def project_folders(root: Path) -> dict[str, Path]:
    """Real project directories directly beneath the canonical workspace root.

    Symlinks and junctions are excluded on the listing itself, without
    following them, so every returned path is canonical by construction.
    This is the only function that touches the filesystem for project
    lookup, and it never receives request data.
    """
    base = root.resolve(strict=True)
    with os.scandir(base) as entries:
        return {
            entry.name: base / entry.name
            for entry in entries
            if not entry.is_symlink()
            and not entry.is_junction()
            and entry.is_dir(follow_symlinks=False)
        }


def project_data_folder(root: Path, project_id: str) -> Path:
    """The prepared ``<root>/<project_id>`` folder, rejecting links and aliases.

    One containment rule for every path that reads or writes project data:
    preview, execute, timer ticks and artifact queries. ``resource_path``
    trusts the root it is given, so a symlink or junction installed at the
    project folder would otherwise redirect reads into another project or
    outside the workspace (#37 review).

    The request-supplied ``project_id`` is only ever used as a key into the
    trusted listing from ``project_folders``; it never reaches a filesystem
    call. Where the workspace filesystem is case-insensitive (NTFS, default
    APFS) a case-only rename of the folder still addresses the same
    directory, so the lookup follows the filesystem's own rule instead of a
    byte comparison (PR #85 review). Raises ``ValueError`` when no real
    directory of that name exists.
    """
    try:
        folders = project_folders(root)
    except OSError:
        raise ValueError("Workspace root is unavailable") from None
    folder = folders.get(project_id)
    if folder is None:
        wanted = project_id.casefold()
        folder = next(
            (
                candidate
                for name, candidate in folders.items()
                if name.casefold() == wanted and _case_insensitive(candidate)
            ),
            None,
        )
    if folder is None:
        raise ValueError("Project folder is missing or aliases another folder")
    return folder


def _case_insensitive(folder: Path) -> bool:
    """Whether this directory's filesystem ignores case in its own name.

    Probed with a listing-derived name only (its case-swapped spelling), so
    nothing from a request is handed to the filesystem.
    """
    swapped = folder.with_name(folder.name.swapcase())
    # Compare the names as strings: WindowsPath equality already ignores case.
    if swapped.name == folder.name:
        return False
    try:
        return os.path.samefile(folder, swapped)
    except OSError:
        return False


def prepare_project(root: Path, project_id: str, *, inputs_folder: bool = True) -> None:
    try:
        base = root.resolve(strict=True)
        project = base / project_id
        inputs = project / "inputs" if inputs_folder else project
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
        except OSError as exc:
            # An unreadable folder is reported to the user as "not ready".
            logger.info("Workspace readiness check failed: %s", type(exc).__name__)
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


def _store_setting(db: Database, root: Path | None) -> None:
    """Atomically replace the saved workspace override; ``None`` removes it."""
    temporary: Path | None = None
    try:
        if root is None:
            settings_file(db).unlink(missing_ok=True)
            return
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
            except OSError as exc:
                # Only a stale temporary file remains; the setting is decided.
                logger.warning(
                    "Could not remove temporary workspace settings file: %s",
                    type(exc).__name__,
                )


@router.put("", response_model=WorkspaceStatus)
def save_workspace(
    payload: WorkspaceUpdate,
    request: Request,
    response: Response,
    db: Annotated[Database, Depends(database)],
) -> WorkspaceStatus:
    response.headers["Cache-Control"] = "no-store"
    local = local_workspace_request(request)
    with workspace_lock:
        from app.workspace_storage import switch_workspace

        # Null removes the app override and restores the startup environment.
        root = (
            selected_root(payload.root_path, db, local=local)
            if payload.root_path is not None
            else (
                checked_root(settings.workspace_root.absolute())
                if settings.workspace_root
                else None
            )
        )
        switch_workspace(db, root, None if payload.root_path is None else root)
        return status(db)
