"""Simple text cleanup and n-grams."""

from __future__ import annotations

import re

_WS = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^\w\s]", re.UNICODE)


def normalize(text: str) -> str:
    """Lowercase, strip punctuation-ish noise, collapse spaces."""
    raw = "" if text is None else str(text)
    cleaned = _NON_WORD.sub(" ", raw.lower())
    return _WS.sub(" ", cleaned).strip()


def word_ngrams(text: str, n: int = 2) -> list[str]:
    """Return word n-grams from normalized text."""
    tokens = normalize(text).split()
    if n < 1 or len(tokens) < n:
        return tokens[:]
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
