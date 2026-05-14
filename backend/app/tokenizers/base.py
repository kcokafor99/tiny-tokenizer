from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class TokenizerError(Exception):
    """Raised when a tokenizer fails to encode (bad input, missing model, etc.)."""


@dataclass(frozen=True)
class EncodedToken:
    id: int
    raw: bytes


class TokenizerAdapter(Protocol):
    """All tokenizer backends conform to this interface."""

    slug: str
    label: str

    def encode(self, text: str) -> list[EncodedToken]: ...
