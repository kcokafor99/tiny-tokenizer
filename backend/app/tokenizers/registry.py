from __future__ import annotations

from pathlib import Path

from app.logging_setup import get_logger
from app.tokenizers.base import TokenizerAdapter, TokenizerError
from app.tokenizers.tiny import TinyAdapter

logger = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_TINY_MODEL = _REPO_ROOT / "tokenizer" / "data" / "tok.json"

# tiktoken encodings to expose. slug uses the canonical encoding name so the
# mapping is unambiguous; label surfaces which model family uses each.
_TIKTOKEN_ENCODINGS: list[tuple[str, str, str]] = [
    ("o200k_base", "o200k_base", "OpenAI · o200k_base (GPT-4o, GPT-4o-mini)"),
    ("cl100k_base", "cl100k_base", "OpenAI · cl100k_base (GPT-4, GPT-3.5)"),
]

_adapters: dict[str, TokenizerAdapter] = {}


def _try_register_tiny() -> None:
    try:
        tiny = TinyAdapter(_DEFAULT_TINY_MODEL)
        _adapters[tiny.slug] = tiny
    except TokenizerError as exc:
        logger.warning("tiny_adapter_unavailable", error=str(exc))


def _try_register_tiktoken() -> None:
    try:
        from app.tokenizers.tiktoken_adapter import TiktokenAdapter
    except ImportError as exc:
        logger.warning("tiktoken_not_installed", error=str(exc))
        return

    for encoding_name, slug, label in _TIKTOKEN_ENCODINGS:
        try:
            adapter = TiktokenAdapter(encoding_name, slug, label)
            _adapters[adapter.slug] = adapter
        except TokenizerError as exc:
            logger.warning(
                "tiktoken_adapter_unavailable",
                encoding=encoding_name,
                error=str(exc),
            )


def _load_adapters_once() -> None:
    if _adapters:
        return
    _try_register_tiny()
    _try_register_tiktoken()


def get_tokenizer(slug: str) -> TokenizerAdapter:
    _load_adapters_once()
    adapter = _adapters.get(slug)
    if adapter is None:
        raise TokenizerError(f"Unknown or unavailable tokenizer: {slug!r}")
    return adapter


def list_available() -> list[dict]:
    _load_adapters_once()
    return [{"slug": a.slug, "label": a.label} for a in _adapters.values()]
