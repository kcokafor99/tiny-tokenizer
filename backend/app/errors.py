from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging_setup import get_logger

logger = get_logger(__name__)


def _problem(status: int, code: str, message: str, **extra) -> JSONResponse:
    body = {"error": {"code": code, "message": message}}
    if extra:
        body["error"]["context"] = extra
    return JSONResponse(status_code=status, content=body)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        logger.info("validation_error", errors=exc.errors())
        return _problem(422, "validation_error", "Request failed validation",
                        details=exc.errors())

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(_: Request, exc: RateLimitExceeded):
        logger.warning("rate_limited", detail=str(exc))
        return _problem(429, "rate_limited", "Too many requests")

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        logger.info("http_exception", status=exc.status_code, detail=exc.detail)
        return _problem(exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.exception("unhandled_exception", error_type=type(exc).__name__)
        return _problem(500, "internal_error", "An internal error occurred")
