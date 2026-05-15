from __future__ import annotations

import tiktoken

from app.logging_setup import get_logger
from app.tokenizers.base import EncodedToken, TokenizerError

logger = get_logger(__name__)


class TiktokenAdapter:
    """
    Adapter around an OpenAI tiktoken encoding (e.g. o200k_base, cl100k_base).

    One instance per encoding. The first call downloads BPE files into
    tiktoken's on-disk cache (~/.cache/tiktoken); subsequent calls hit the
    cache only.
    """

    def __init__(self, encoding_name: str, slug: str, label: str) -> None:
        self.slug = slug
        self.label = label
        self._encoding_name = encoding_name
        try:
            self._encoding = tiktoken.get_encoding(encoding_name)
        except Exception as exc:
            raise TokenizerError(
                f"Failed to load tiktoken encoding {encoding_name!r}: {exc}"
            ) from exc
        logger.info(
            "tiktoken_loaded",
            encoding=encoding_name,
            slug=slug,
            n_vocab=self._encoding.n_vocab,
        )

    def encode(self, text: str) -> list[EncodedToken]:
        try:
            ids = self._encoding.encode(text)
        except Exception as exc:
            raise TokenizerError(f"tiktoken encode failed: {exc}") from exc

        decode_single = self._encoding.decode_single_token_bytes
        return [EncodedToken(id=tok_id, raw=decode_single(tok_id)) for tok_id in ids]
