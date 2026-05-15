from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request, Response

from app.analytics import capture
from app.logging_setup import get_logger
from app.metrics import metrics_response, tokenize_latency, tokenize_tokens
from app.rate_limit import limiter
from app.schemas import HealthResponse, TokenInfo, TokenizeRequest, TokenizeResponse
from app.session import get_or_create_anon_id
from app.tokenizers import TokenizerError, get_tokenizer, list_available

router = APIRouter()
logger = get_logger(__name__)

API_VERSION = "0.1.0"


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok", version=API_VERSION)


@router.get("/metrics")
def metrics():
    return metrics_response()


@router.get("/tokenizers")
def tokenizers():
    return {"tokenizers": list_available()}


@router.post("/tokenize", response_model=TokenizeResponse)
@limiter.limit("60/minute")
def tokenize(payload: TokenizeRequest, request: Request, response: Response):
    # Hoist hot accessors into locals — each one was being re-resolved per
    # reference during the hot path.
    slug = payload.tokenizer
    text = payload.text
    text_len = len(text)
    anon_id = get_or_create_anon_id(request, response)

    start = time.perf_counter()

    try:
        adapter = get_tokenizer(slug)
    except TokenizerError as exc:
        logger.info("tokenizer_not_found", slug=slug, error=str(exc))
        raise HTTPException(status_code=404, detail=str(exc))

    try:
        encoded = adapter.encode(text)
    except TokenizerError as exc:
        logger.warning("tokenize_failed", slug=slug, error=str(exc))
        raise HTTPException(status_code=422, detail=str(exc))

    # Single-pass per-token construction. Old code called is_valid_utf8()
    # twice and .hex() twice per token; here every byte sequence is decoded
    # at most once.
    tokens: list[TokenInfo] = []
    append = tokens.append
    for t in encoded:
        raw = t.raw
        hex_str = raw.hex()
        try:
            display = raw.decode("utf-8")
            valid = True
        except UnicodeDecodeError:
            display = hex_str
            valid = False
        append(TokenInfo(id=t.id, bytes_hex=hex_str, display=display, valid_utf8=valid))

    elapsed = time.perf_counter() - start
    token_count = len(tokens)
    duration_ms = round(elapsed * 1000, 2)

    # Prometheus `.labels()` is internally cached so this is O(1) after warm.
    tokenize_latency.labels(tokenizer=slug).observe(elapsed)
    tokenize_tokens.labels(tokenizer=slug).observe(token_count)

    logger.info(
        "tokenize_ok",
        tokenizer=slug,
        anon=anon_id,
        text_len=text_len,
        token_count=token_count,
        duration_ms=duration_ms,
    )
    capture(
        anon_id,
        "prompt_tokenized",
        {
            "tokenizer": slug,
            "text_len": text_len,
            "token_count": token_count,
            "duration_ms": duration_ms,
        },
    )

    return TokenizeResponse(
        tokenizer=slug,
        token_count=token_count,
        tokens=tokens,
        duration_ms=duration_ms,
    )
