from __future__ import annotations

from pathlib import Path

from app.logging_setup import get_logger
from app.tokenizers.base import TokenizerAdapter, TokenizerError
from app.tokenizers.tiny import TinyAdapter

logger = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_TINY_MODEL = _REPO_ROOT / "tokenizer" / "data" / "tok.json"

_adapters: dict[str, TokenizerAdapter] = {}


def _load_adapters_once() -> None:
    if _adapters:
        return
    try:
        tiny = TinyAdapter(_DEFAULT_TINY_MODEL)
        _adapters[tiny.slug] = tiny
    except TokenizerError as e:
        logger.warning("tiny_adapter_unavailable", error=str(e))


def get_tokenizer(slug: str) -> TokenizerAdapter:
    _load_adapters_once()
    adapter = _adapters.get(slug)
    if adapter is None:
        raise TokenizerError(f"Unknown or unavailable tokenizer: {slug!r}")
    return adapter


def list_available() -> list[dict]:
    _load_adapters_once()
    return [{"slug": a.slug, "label": a.label} for a in _adapters.values()]
