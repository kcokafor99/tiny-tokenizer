from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings


def _anon_key(request: Request) -> str:
    """
    Rate-limit by signed session cookie if present, falling back to IP.
    Avoids the cookie being unset on first request leaking through as
    "unlimited" — we always have *something* to key on.
    """
    settings = get_settings()
    cookie = request.cookies.get(settings.cookie_name)
    if cookie:
        return f"cookie:{cookie[:48]}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=_anon_key,
    default_limits=[f"{get_settings().rate_limit_per_minute}/minute"],
    headers_enabled=True,
)
