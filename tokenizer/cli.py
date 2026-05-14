from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pymupdf

from tokenizer.tiny import TinyTokenizer, is_valid_utf8


def load_pdf_corpus(path: str | Path) -> str:
    pages: list[str] = []
    with pymupdf.open(path) as doc:
        for page in doc:
            pages.append(page.get_text().replace("\n", " "))
    return "\n".join(pages)


def main() -> None:
    parser = argparse.ArgumentParser(description="TinyTokenizer — train or encode")
    parser.add_argument("text", help="Text to encode after training")
    parser.add_argument(
        "--corpus",
        default="tokenizer/data/template.pdf",
        help="Path to PDF training corpus",
    )
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
    display = [t.decode("utf-8") if is_valid_utf8(t) else t.hex() for t in tokens]
    print(f"tokens ({len(tokens)}): {display}")
    print(f"ids:    {ids}")
    print(f"decoded: {decoded!r}")
    print(f"roundtrip ok: {decoded == args.text}")


if __name__ == "__main__":
    main()
