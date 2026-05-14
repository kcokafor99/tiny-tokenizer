from __future__ import annotations
import logging
import json
from pathlib import Path
import pymupdf
import argparse
from collections import Counter, defaultdict
from typing import Iterable
import regex

logger = logging.getLogger(__name__)

Token = bytes
MergeRule = tuple[Token, Token]
Word = tuple[list[Token], int]

# start with 256 single-byte tokens to prevent out of vocabulary in the tokenizer.
BASE_ALPHABETS: list[Token] = [bytes([b]) for b in range(256)]
PRE_TOKENIZATION_PATTERN = regex.compile(
    r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
)


class TinyTokenizer:

    def __init__(self, vocab_size: int = 1000) -> None:
        if vocab_size < 256:
            raise ValueError("vocab_size must be at least 256 (the base byte alphabet)")
        self.vocab_size = vocab_size
        self.merge_rules: list[MergeRule] = []
        self.id_to_token: dict[int, Token] = {}
        self.token_to_id: dict[Token, int] = {}

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
        return instance

    def train_tokenizer(self, corpus):
        corpus_arr = self._pre_tokenize(corpus)
        corpus_freq = Counter(corpus_arr)
        logging.info("Training on %d words (%d unique)", len(corpus_arr), len(corpus_freq))

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
        """Assign integer IDs: 0-255 for base bytes, then merges in priority order."""
        self.token_to_id = {t: i for i, t in enumerate(BASE_ALPHABETS)}
        for a, b in self.merge_rules:
            merged = a + b
            if merged not in self.token_to_id:
                self.token_to_id[merged] = len(self.token_to_id)
        self.id_to_token = {i: t for t, i in self.token_to_id.items()}

    def save(self, path: str | Path) -> None:
        payload = {
            "vocab_size": self.vocab_size,
            "merge_rules": [
                [a.hex(), b.hex()] for a, b in self.merge_rules
            ],
            "vocab": {token.hex(): tid for token, tid in self.token_to_id.items()}
        }
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def tokenize(self, text: str) -> list[Token]:
        if not self.merge_rules or not self.token_to_id:
            raise RuntimeError("Tokenizer has not been trained or loaded")
        result: list[Token] = []
        for word in self._pre_tokenize(text):
            tokens = [bytes([b]) for b in word.encode("utf-8")]
            for pair in self.merge_rules:
                tokens = self._apply_merge(tokens, pair)
            result.extend(tokens)
        return result

    def encode(self, text: str) -> list[int]:
        """Convert text into a list of integer token IDs."""
        tokens = self.tokenize(text)
        return [self.token_to_id[token] for token in tokens if token in self.token_to_id]

    def decode(self, ids: Iterable[int]) -> str:
        """Convert token IDs back into a string."""
        joined = b"".join(self.id_to_token[id] for id in ids if id in self.id_to_token)
        return joined.decode("utf-8", errors="replace")

    @staticmethod
    def _pre_tokenize(corpus: str) -> list:
        return PRE_TOKENIZATION_PATTERN.findall(corpus)

    @staticmethod
    def _apply_merge(tokens: list[Token], pair: MergeRule) -> list[Token]:
        a, b = pair
        i, n = 0, len(tokens)
        new_tokens: list[Token] = []
        while i < n:
            if i < n - 1 and (tokens[i] == a and tokens[i + 1] == b):
                new_tokens.append(a + b)
                i += 2
            else:
                new_tokens.append(tokens[i])
                i += 1
        return new_tokens


def _is_valid_utf8(b: bytes) -> bool:
    try:
        b.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def load_pdf_corpus(path: str | Path) -> str:
    pages: list[str] = []
    with pymupdf.open(path) as doc:
        for page in doc:
            pages.append(page.get_text().replace("\n", " "))
    return "\n".join(pages)


def main():
    parser = argparse.ArgumentParser(description="TinyTokenizer — train or encode")
    parser.add_argument("text", help="Text to encode after training")
    parser.add_argument("--corpus", default="template.pdf", help="Path to PDF training corpus")
    parser.add_argument("--vocab-size", type=int, default=512, help="Target vocab size")
    parser.add_argument("--save", help="Save trained tokenizer to this path")
    parser.add_argument("--load", help="Load tokenizer from this path instead of training")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.load:
        tokenizer = TinyTokenizer.load(args.load)
    else:
        corpus = load_pdf_corpus(args.corpus)
        tokenizer = TinyTokenizer(vocab_size=args.vocab_size)
        tokenizer.train_tokenizer(corpus)
        if args.save:
            tokenizer.save(args.save)

    tokens = tokenizer.tokenize(args.text)
    ids = tokenizer.encode(args.text)
    decoded = tokenizer.decode(ids)
    display = [
        t.decode("utf-8") if _is_valid_utf8(t) else t.hex()
        for t in tokens
    ]
    print(f"tokens ({len(tokens)}): {display}")
    print(f"ids:    {ids}")
    print(f"decoded: {decoded!r}")
    print(f"roundtrip ok: {decoded == args.text}")


if __name__ == "__main__":
    main()
