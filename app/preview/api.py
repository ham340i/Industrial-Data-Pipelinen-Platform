"""Read-only draft preview with bounded request admission and cancellation."""

import asyncio
from threading import BoundedSemaphore, Event
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.blocks.catalog import registry
from app.workspace import effective_workspace_root
from app.metadata.database import Database
from app.preview.errors import PreviewError, failure_response
from app.preview.models import (
    MAX_CONCURRENT,
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    PreviewRequest,
    PreviewResult,
)
from app.preview.service import preview
from app.projects import database

router = APIRouter(prefix="/api/v1/projects/{project_id}/pipelines", tags=["preview"])
MAX_BODY_SECONDS = 5.0


class PreviewBoundaryMiddleware:
    """Limit raw bodies before JSON parsing, admit two requests per process.

    Slots remain held until cooperative worker completion, including disconnects.
    All preview responses (even framework errors) prohibit caching.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.slots = BoundedSemaphore(MAX_CONCURRENT)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].endswith("/pipelines/preview"):
            await self.app(scope, receive, send)
            return

        async def no_store(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.lower() != b"cache-control"
                ] + [(b"cache-control", b"no-store")]
            await send(message)

        if not self.slots.acquire(blocking=False):
            await failure_response(
                PreviewError(
                    "preview_busy",
                    "Two previews are already running. Try again shortly.",
                    status=429,
                ),
                scope.get("correlation_id", "preview"),
            )(scope, receive, no_store)
            return
        try:
            body = bytearray()
            body_deadline = asyncio.get_running_loop().time() + MAX_BODY_SECONDS
            while True:
                try:
                    message = await asyncio.wait_for(
                        receive(),
                        timeout=max(
                            0, body_deadline - asyncio.get_running_loop().time()
                        ),
                    )
                except TimeoutError:
                    await failure_response(
                        PreviewError(
                            "preview_request_timeout",
                            "Preview request body took too long to arrive.",
                            status=408,
                        ),
                        scope.get("correlation_id", "preview"),
                    )(scope, receive, no_store)
                    return
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                if len(body) + len(chunk) > MAX_REQUEST_BYTES:
                    await failure_response(
                        PreviewError(
                            "preview_request_limit",
                            "Preview requests must be at most 256 KiB.",
                            status=413,
                        ),
                        scope.get("correlation_id", "preview"),
                    )(scope, receive, no_store)
                    return
                body.extend(chunk)
                if not message.get("more_body", False):
                    break
            delivered = False

            async def replay() -> Message:
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {
                        "type": "http.request",
                        "body": bytes(body),
                        "more_body": False,
                    }
                return await receive()

            await self.app(scope, replay, no_store)
        finally:
            self.slots.release()


@router.post("/preview", response_model=PreviewResult)
async def preview_pipeline(
    project_id: UUID,
    payload: PreviewRequest,
    request: Request,
    db: Annotated[Database, Depends(database)],
) -> Response:
    cancelled = Event()
    task = asyncio.create_task(
        asyncio.to_thread(
            preview,
            payload,
            str(project_id),
            db,
            registry,
            effective_workspace_root(db),
            cancelled,
        )
    )
    try:
        while not task.done():
            await asyncio.wait({task}, timeout=0.05)
            if await request.is_disconnected():
                cancelled.set()
        result = await task
        content = result.model_dump_json().encode("utf-8")
        if len(content) > MAX_RESPONSE_BYTES:
            raise PreviewError(
                "preview_response_limit",
                "The sample exceeds the 2 MiB response limit. "
                "Request fewer rows or cells.",
            )
        return Response(
            content,
            media_type="application/json",
            headers={"Cache-Control": "no-store"},
        )
    except PreviewError as exc:
        return failure_response(exc, request.scope["correlation_id"])
    except Exception:
        return failure_response(
            PreviewError(
                "preview_failed",
                "Preview failed. Check the input and configuration.",
                status=500,
            ),
            request.scope["correlation_id"],
        )
    finally:
        cancelled.set()
        # A disconnected caller must not release capacity while its worker runs.
        if not task.done():
            try:
                await asyncio.shield(task)
            except (Exception, asyncio.CancelledError):
                pass
