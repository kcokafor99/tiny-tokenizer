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
from tokenizer.tiny import is_valid_utf8

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
    anon_id = get_or_create_anon_id(request, response)
    start = time.perf_counter()

    try:
        adapter = get_tokenizer(payload.tokenizer)
    except TokenizerError as e:
        logger.info("tokenizer_not_found", slug=payload.tokenizer, error=str(e))
        raise HTTPException(status_code=404, detail=str(e))

    try:
        encoded = adapter.encode(payload.text)
    except TokenizerError as e:
        logger.warning("tokenize_failed", slug=payload.tokenizer, error=str(e))
        raise HTTPException(status_code=422, detail=str(e))

    tokens = [
        TokenInfo(
            id=t.id,
            bytes_hex=t.raw.hex(),
            display=t.raw.decode("utf-8") if is_valid_utf8(t.raw) else t.raw.hex(),
            valid_utf8=is_valid_utf8(t.raw),
        )
        for t in encoded
    ]

    elapsed = time.perf_counter() - start
    tokenize_latency.labels(tokenizer=payload.tokenizer).observe(elapsed)
    tokenize_tokens.labels(tokenizer=payload.tokenizer).observe(len(tokens))

    logger.info(
        "tokenize_ok",
        tokenizer=payload.tokenizer,
        anon=anon_id,
        text_len=len(payload.text),
        token_count=len(tokens),
        duration_ms=round(elapsed * 1000, 2),
    )
    capture(
        anon_id,
        "prompt_tokenized",
        {
            "tokenizer": payload.tokenizer,
            "text_len": len(payload.text),
            "token_count": len(tokens),
            "duration_ms": round(elapsed * 1000, 2),
        },
    )

    return TokenizeResponse(
        tokenizer=payload.tokenizer,
        token_count=len(tokens),
        tokens=tokens,
        duration_ms=round(elapsed * 1000, 2),
    )
