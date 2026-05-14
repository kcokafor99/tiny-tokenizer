from __future__ import annotations

import hashlib
import secrets

from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeSerializer

from app.config import get_settings
from app.logging_setup import get_logger

logger = get_logger(__name__)

FINGERPRINT_HEADER = "X-Anon-Fingerprint"


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().session_secret, salt="tt-anon-session")


def _new_session_id() -> str:
    return secrets.token_urlsafe(24)


def _read_cookie(request: Request) -> str | None:
    raw = request.cookies.get(get_settings().cookie_name)
    if not raw:
        return None
    try:
        return _serializer().loads(raw)
    except BadSignature:
        logger.warning("session_cookie_bad_signature")
        return None


def _hash_fingerprint(fp: str) -> str:
    """Avoid storing the raw fingerprint anywhere — hash it."""
    return hashlib.sha256(fp.encode("utf-8")).hexdigest()[:32]


def get_or_create_anon_id(request: Request, response: Response) -> str:
    """
    Combine signed session cookie + browser fingerprint header into a stable
    anonymous identifier. Either alone is weak; together they're a reasonable
    abuse-control signal without authentication.
    """
    session_id = _read_cookie(request)
    if not session_id:
        session_id = _new_session_id()
        settings = get_settings()
        response.set_cookie(
            key=settings.cookie_name,
            value=_serializer().dumps(session_id),
            httponly=True,
            secure=settings.cookie_secure,
            samesite="strict",
            max_age=60 * 60 * 24 * 365,  # 1 year
        )

    fp_raw = request.headers.get(FINGERPRINT_HEADER)
    fp_hash = _hash_fingerprint(fp_raw) if fp_raw else "no-fp"

    return f"{session_id}:{fp_hash}"
