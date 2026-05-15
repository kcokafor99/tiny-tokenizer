from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging_setup import get_logger

logger = get_logger(__name__)


def _build_error_response(
    status: int, code: str, message: str, **extra
) -> JSONResponse:
    body = {"error": {"code": code, "message": message}}
    if extra:
        body["error"]["context"] = extra
    return JSONResponse(status_code=status, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_: Request, exc: RequestValidationError):
        logger.info("validation_error", errors=exc.errors())
        return _build_error_response(
            422, "validation_error", "Request failed validation", details=exc.errors()
        )

    @app.exception_handler(RateLimitExceeded)
    async def _handle_rate_limit_exceeded(_: Request, exc: RateLimitExceeded):
        logger.warning("rate_limited", detail=str(exc))
        return _build_error_response(429, "rate_limited", "Too many requests")

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(_: Request, exc: StarletteHTTPException):
        logger.info("http_exception", status=exc.status_code, detail=exc.detail)
        return _build_error_response(exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(Exception)
    async def _handle_unhandled_exception(_: Request, exc: Exception):
        logger.exception("unhandled_exception", error_type=type(exc).__name__)
        return _build_error_response(500, "internal_error", "An internal error occurred")
