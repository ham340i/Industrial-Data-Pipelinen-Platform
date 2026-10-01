from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings
from app.schemas.errors import ApiError, ErrorEnvelope
from app.schemas.health import HealthResponse
from app.schemas.requests import ExampleRequest, ExampleResponse


_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")


def get_correlation_id(request: Request) -> str:
    supplied_id = request.headers.get("X-Correlation-ID")

    if supplied_id and _CORRELATION_ID_PATTERN.fullmatch(supplied_id):
        return supplied_id

    return str(uuid4())


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        correlation_id = get_correlation_id(request)

        async def send_with_correlation_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append(
                    (
                        b"x-correlation-id",
                        correlation_id.encode("ascii"),
                    )
                )
                message["headers"] = headers

            await send(message)

        scope["correlation_id"] = correlation_id
        await self.app(scope, receive, send_with_correlation_id)


app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    description="Local-first API contracts for the Industrial Data Pipeline Platform.",
)

app.add_middleware(CorrelationIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Correlation-ID"],
)


def error_response(
    *,
    request: Request,
    code: str,
    message: str,
    status_code: int,
    node_context: str | None = None,
) -> JSONResponse:
    correlation_id = request.scope.get("correlation_id", str(uuid4()))

    payload = ErrorEnvelope(
        error=ApiError(
            code=code,
            message=message,
            correlation_id=correlation_id,
            node_context=node_context,
        )
    )

    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers={"X-Correlation-ID": correlation_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return error_response(
        request=request,
        code="validation_error",
        message="The request body or parameters are invalid.",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return error_response(
        request=request,
        code="internal_error",
        message="An unexpected error occurred.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    tags=["health"],
)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="local-pipeline-studio",
        version=settings.api_version,
    )


@app.post(
    "/api/v1/example",
    response_model=ExampleResponse,
    tags=["example"],
)
async def example(payload: ExampleRequest) -> ExampleResponse:
    return ExampleResponse(
        name=payload.name,
        count=payload.count,
    )