from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import regex

logger = logging.getLogger(__name__)

Token = bytes
MergeRule = tuple[Token, Token]

BASE_ALPHABETS: list[Token] = [bytes([b]) for b in range(256)]
PRE_TOKENIZATION_PATTERN = regex.compile(
    r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
)

# Real text repeats the same words constantly — caching per pre-tokenized
# word turns nearly all repeat calls into a single dict lookup. Bounded to
# avoid unbounded memory growth in a long-running process.
_WORD_CACHE_MAX = 4096


class TinyTokenizer:
    def __init__(self, vocab_size: int = 1000) -> None:
        if vocab_size < 256:
            raise ValueError("vocab_size must be at least 256 (the base byte alphabet)")
        self.vocab_size = vocab_size
        self.merge_rules: list[MergeRule] = []
        self.id_to_token: dict[int, Token] = {}
        self.token_to_id: dict[Token, int] = {}
        # Fast encode-path lookups (rebuilt by build_vocab / load):
        #   _merge_table[(left_id, right_id)] = (rank, merged_id)
        # Lower rank = applied earlier. Using ints (not bytes) avoids per-step
        # allocation and uses faster integer hashing in tight loops.
        self._merge_table: dict[tuple[int, int], tuple[int, int]] = {}
        self._word_cache: dict[bytes, tuple[int, ...]] = {}

    @classmethod
    def load(cls, path: str | Path) -> "TinyTokenizer":
        payload = json.loads(Path(path).read_text())
        instance = cls(vocab_size=payload["vocab_size"])
        instance.merge_rules = [
            (bytes.fromhex(a), bytes.fromhex(b)) for a, b in payload["merge_rules"]
        ]
        instance.token_to_id = {
            bytes.fromhex(hex_token): tid for hex_token, tid in payload["vocab"].items()
        }
        instance.id_to_token = {i: t for t, i in instance.token_to_id.items()}
        instance._build_fast_lookups()
        return instance

    def train_tokenizer(self, corpus: str) -> None:
        corpus_arr = self._pre_tokenize(corpus)
        corpus_freq = Counter(corpus_arr)
        logger.info("Training on %d words (%d unique)", len(corpus_arr), len(corpus_freq))

        word_splits: list[list[Token]] = [
            [bytes([b]) for b in word.encode("utf-8")] for word in corpus_freq
        ]
        word_weights: list[int] = list(corpus_freq.values())

        pair_counts: Counter = Counter()
        pair_index: dict[tuple[Token, Token], set[int]] = defaultdict(set)
        for i, word in enumerate(word_splits):
            weight = word_weights[i]
            for j in range(len(word) - 1):
                pair = (word[j], word[j + 1])
                pair_counts[pair] += weight
                pair_index[pair].add(i)

        target_merge_count = self.vocab_size - len(BASE_ALPHABETS)

        for step in range(target_merge_count):
            if not pair_counts:
                logger.info("No more pairs to merge after %d steps", step)
                break

            best_pair, count = pair_counts.most_common(1)[0]
            if count <= 0:
                break
            self.merge_rules.append(best_pair)
            a, b = best_pair
            merged = a + b

            for i in list(pair_index[best_pair]):
                word = word_splits[i]
                weight = word_weights[i]
                new_word: list[Token] = []
                j, n = 0, len(word)
                while j < n:
                    if j < n - 1 and word[j] == a and word[j + 1] == b:
                        if new_word:
                            prev = new_word[-1]
                            pair_counts[(prev, a)] -= weight
                            if pair_counts[(prev, a)] <= 0:
                                del pair_counts[(prev, a)]
                            pair_counts[(prev, merged)] += weight
                            pair_index[(prev, merged)].add(i)
                        if j + 2 < n:
                            nxt = word[j + 2]
                            pair_counts[(b, nxt)] -= weight
                            if pair_counts[(b, nxt)] <= 0:
                                del pair_counts[(b, nxt)]
                            pair_counts[(merged, nxt)] += weight
                            pair_index[(merged, nxt)].add(i)
                        new_word.append(merged)
                        j += 2
                    else:
                        new_word.append(word[j])
                        j += 1
                word_splits[i] = new_word

            del pair_counts[best_pair]
            del pair_index[best_pair]
            logger.debug("Step %d: merged %r (count=%d)", step + 1, best_pair, count)

        self.build_vocab()
        logger.info("Trained: %d merges, %d total tokens", len(self.merge_rules), len(self.token_to_id))

    def build_vocab(self) -> None:
        self.token_to_id = {t: i for i, t in enumerate(BASE_ALPHABETS)}
        for a, b in self.merge_rules:
            merged = a + b
            if merged not in self.token_to_id:
                self.token_to_id[merged] = len(self.token_to_id)
        self.id_to_token = {i: t for t, i in self.token_to_id.items()}
        self._build_fast_lookups()

    def save(self, path: str | Path) -> None:
        payload = {
            "vocab_size": self.vocab_size,
            "merge_rules": [[a.hex(), b.hex()] for a, b in self.merge_rules],
            "vocab": {token.hex(): tid for token, tid in self.token_to_id.items()},
        }
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def encode(self, text: str) -> list[int]:
        """Convert text into a list of integer token IDs (the fast path)."""
        if not self._merge_table and not self.merge_rules:
            raise RuntimeError("Tokenizer has not been trained or loaded")
        result: list[int] = []
        extend = result.extend
        cache = self._word_cache
        cache_get = cache.get
        bpe_encode_word = self._bpe_encode_word
        cache_max = _WORD_CACHE_MAX
        findall = PRE_TOKENIZATION_PATTERN.findall
        for word in findall(text):
            word_bytes = word.encode("utf-8")
            ids = cache_get(word_bytes)
            if ids is None:
                ids = bpe_encode_word(word_bytes)
                if len(cache) < cache_max:
                    cache[word_bytes] = ids
            extend(ids)
        return result

    def tokenize(self, text: str) -> list[Token]:
        """Bytes-level view of the token sequence. Built on top of encode()."""
        id_to_token = self.id_to_token
        return [id_to_token[tid] for tid in self.encode(text)]

    def decode(self, ids: Iterable[int]) -> str:
        id_to_token = self.id_to_token
        joined = b"".join(id_to_token[tid] for tid in ids if tid in id_to_token)
        return joined.decode("utf-8", errors="replace")

    # ---------- internals ----------

    def _build_fast_lookups(self) -> None:
        """Build the int-keyed merge table that powers _bpe_encode_word."""
        table: dict[tuple[int, int], tuple[int, int]] = {}
        token_to_id = self.token_to_id
        for rank, (a, b) in enumerate(self.merge_rules):
            table[(token_to_id[a], token_to_id[b])] = (rank, token_to_id[a + b])
        self._merge_table = table
        self._word_cache.clear()

    def _bpe_encode_word(self, word_bytes: bytes) -> tuple[int, ...]:
        """
        Encode one pre-tokenized word's bytes using the lowest-rank-first BPE
        algorithm.

        At each step we scan the current sequence once to find the highest-
        priority mergeable pair (lowest rank), apply that single merge, and
        repeat. This is O(W²) per word in the worst case — but W is small
        because pre-tokenization splits on word boundaries, and the constant
        factor is small (integer compares, no bytes allocation, no method
        dispatch). The old code did O(M × W) Python-level loops per word,
        where M was the merge-rule count regardless of how many actually fired.
        """
        n = len(word_bytes)
        if n == 0:
            return ()
        if n == 1:
            return (word_bytes[0],)  # base alphabet: each byte's value is its token ID

        # Each byte is its own base-alphabet token ID (0–255).
        ids: list[int] = list(word_bytes)
        table_get = self._merge_table.get
        # Sentinel rank larger than any real rank ⇒ eliminates the
        # `best_rank is None or rank < best_rank` branch (the `is None` check
        # runs every iteration of the inner scan otherwise).
        SENTINEL_RANK = 1 << 62

        while True:
            best_rank = SENTINEL_RANK
            best_pos = -1
            best_merged = -1
            last = len(ids) - 1
            for i in range(last):
                entry = table_get((ids[i], ids[i + 1]))
                if entry is not None and entry[0] < best_rank:
                    best_rank = entry[0]
                    best_pos = i
                    best_merged = entry[1]
                    if best_rank == 0:
                        # Rank 0 is the highest priority — nothing can beat it.
                        break
            if best_pos == -1:
                break
            # Slice assignment is one C-level memmove vs the previous
            # `ids[k] = v` followed by `del ids[k+1]` (two operations).
            ids[best_pos : best_pos + 2] = (best_merged,)
            if len(ids) == 1:
                break
        return tuple(ids)

    @staticmethod
    def _pre_tokenize(corpus: str) -> list[str]:
        return PRE_TOKENIZATION_PATTERN.findall(corpus)


def is_valid_utf8(b: bytes) -> bool:
    try:
        b.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False
