"""Safe errors for the preview boundary; raw exceptions never leave it."""

from fastapi.responses import JSONResponse


class PreviewError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int = 422,
        node_id: str | None = None,
        field: str | None = None,
        port: str | None = None,
    ) -> None:
        self.code, self.message, self.status = code, message, status
        self.node_id, self.field, self.port = node_id, field, port
        super().__init__(message)


def failure_response(error: PreviewError, correlation_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=error.status,
        headers={"Cache-Control": "no-store", "X-Correlation-ID": correlation_id},
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "correlation_id": correlation_id,
                "node_context": error.node_id,
                "field": error.field,
                "port": error.port,
            }
        },
    )
