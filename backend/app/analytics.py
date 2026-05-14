from __future__ import annotations

from typing import Any

from posthog import Posthog

from app.config import get_settings
from app.logging_setup import get_logger

logger = get_logger(__name__)

_client: Posthog | None = None


def get_posthog() -> Posthog | None:
    """Lazy singleton. Returns None when no key is configured (dev / offline)."""
    global _client
    if _client is not None:
        return _client
    settings = get_settings()
    if not settings.posthog_api_key:
        logger.info("posthog_disabled", reason="no_api_key")
        return None
    _client = Posthog(
        project_api_key=settings.posthog_api_key,
        host=settings.posthog_host,
        debug=settings.env == "development",
    )
    return _client


def capture(
    distinct_id: str,
    event: str,
    properties: dict[str, Any] | None = None,
) -> None:
    """Best-effort capture — never raises, always logs."""
    client = get_posthog()
    if client is None:
        return
    try:
        client.capture(distinct_id=distinct_id, event=event, properties=properties or {})
    except Exception as e:
        logger.warning("posthog_capture_failed", event=event, error=str(e))
