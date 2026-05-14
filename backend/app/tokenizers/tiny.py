from __future__ import annotations

from pathlib import Path

from app.logging_setup import get_logger
from app.tokenizers.base import EncodedToken, TokenizerError
from tokenizer.tiny import TinyTokenizer

logger = get_logger(__name__)


class TinyAdapter:
    slug = "tiny"
    label = "TinyTokenizer (this project)"

    def __init__(self, model_path: Path) -> None:
        if not model_path.exists():
            raise TokenizerError(
                f"TinyTokenizer model not found at {model_path}. "
                f"Train one first with `python -m tokenizer.cli ...`."
            )
        self._model = TinyTokenizer.load(model_path)
        logger.info(
            "tiny_tokenizer_loaded",
            path=str(model_path),
            vocab_size=self._model.vocab_size,
            merge_rules=len(self._model.merge_rules),
        )

    def encode(self, text: str) -> list[EncodedToken]:
        try:
            raw_tokens = self._model.tokenize(text)
        except Exception as e:
            raise TokenizerError(f"TinyTokenizer encode failed: {e}") from e
        out: list[EncodedToken] = []
        for tok in raw_tokens:
            tok_id = self._model.token_to_id.get(tok)
            if tok_id is None:
                raise TokenizerError(f"Token {tok!r} not in vocab")
            out.append(EncodedToken(id=tok_id, raw=tok))
        return out
