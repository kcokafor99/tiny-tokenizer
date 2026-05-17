from __future__ import annotations

from pathlib import Path

from app.logging_setup import get_logger
from app.metrics import word_cache_hits_total, word_cache_misses_total
from app.tokenizers.base import EncodedToken, TokenizerError
from tokenizer.tiny import TinyTokenizer

logger = get_logger(__name__)


class TinyAdapter:
    slug = "tiny"
    label = "TinyTokenizer"

    def __init__(self, model_path: Path) -> None:
        if not model_path.exists():
            raise TokenizerError(
                f"TinyTokenizer model not found at {model_path}. "
                f"Train one first with `python -m tokenizer.cli ...`."
            )
        self._model = TinyTokenizer.load(model_path)
        # Cached labeled-counter handles; .labels() is internally memoized but
        # this hoists one attribute lookup out of the encode hot path.
        self._hits_counter = word_cache_hits_total.labels(tokenizer=self.slug)
        self._misses_counter = word_cache_misses_total.labels(tokenizer=self.slug)
        logger.info(
            "tiny_tokenizer_loaded",
            path=str(model_path),
            vocab_size=self._model.vocab_size,
            merge_rules=len(self._model.merge_rules),
        )

    def encode(self, text: str) -> list[EncodedToken]:
        pre_hits, pre_misses = self._model.cache_stats()
        try:
            ids = self._model.encode(text)
        except Exception as e:
            raise TokenizerError(f"TinyTokenizer encode failed: {e}") from e
        hits, misses = self._model.cache_stats()
        hits_delta = hits - pre_hits
        misses_delta = misses - pre_misses
        if hits_delta:
            self._hits_counter.inc(hits_delta)
        if misses_delta:
            self._misses_counter.inc(misses_delta)
        id_to_token = self._model.id_to_token
        return [EncodedToken(id=tid, raw=id_to_token[tid]) for tid in ids]
