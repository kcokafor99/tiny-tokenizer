from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.errors import register_exception_handlers
from app.logging_setup import configure_logging, get_logger
from app.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.rate_limit import limiter
from app.routes import router
from app.tokenizers import list_available


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    App lifecycle hooks. Pre-warm tokenizer adapters at startup so the first
    request never pays the lazy-load tax (~210 ms for TinyTokenizer plus the
    one-time tiktoken BPE file download).
    """
    log = get_logger(__name__)
    available = list_available()
    log.info("tokenizers_warmed", count=len(available), slugs=[a["slug"] for a in available])
    yield
    # No teardown work yet.


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger(__name__)

    app = FastAPI(
        title="TinyTokenizer API",
        version="0.1.0",
        docs_url="/docs" if settings.env != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.env != "production" else None,
        lifespan=lifespan,
    )

    # Order matters — outermost added last.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    register_exception_handlers(app)

    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Anon-Fingerprint", "X-Request-ID"],
        max_age=600,
    )

    app.include_router(router)

    log.info(
        "app_started",
        env=settings.env,
        log_level=settings.log_level,
        allowed_origins=settings.allowed_origins,
    )
    return app


app = create_app()


if __name__ == "__main__":
    # Convenience runner: `python -m app.main` after `pip install -e .`
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8765,
        reload=True,
    )
