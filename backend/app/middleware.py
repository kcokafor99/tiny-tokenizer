from __future__ import annotations

import time
import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import get_settings
from app.logging_setup import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """One structured log line per request — entry on exception, exit always."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=round(elapsed_ms, 2),
            )
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            status=response.status_code,
            duration_ms=round(elapsed_ms, 2),
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Defense-in-depth headers. The API serves only JSON, so the CSP can be
    extremely strict — no inline scripts, no remote resources at all.
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        settings = get_settings()
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
        if settings.env == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response
