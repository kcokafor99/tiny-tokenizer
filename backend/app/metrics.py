from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

requests_total = Counter(
    "tt_requests_total",
    "Total HTTP requests by endpoint and status",
    ["endpoint", "status"],
)

tokenize_latency = Histogram(
    "tt_tokenize_seconds",
    "Latency of /tokenize endpoint by tokenizer",
    ["tokenizer"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

tokenize_tokens = Histogram(
    "tt_tokens_produced",
    "Number of tokens produced per request",
    ["tokenizer"],
    buckets=(10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000),
)

paid_calls_total = Counter(
    "tt_paid_count_calls_total",
    "Number of paid (Anthropic/Gemini) count_tokens calls",
    ["provider", "outcome"],
)


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
