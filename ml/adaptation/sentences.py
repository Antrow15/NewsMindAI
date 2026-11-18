"""Sentence splitting for adaptation."""

from __future__ import annotations

import re

ABBREVIATION_PATTERN = re.compile(r"\b(?:Mr|Mrs|Ms|Dr|Prof|Inc|Ltd|No)\.$", re.I)
_WS = re.compile(r"\s+")


def normalize_space(text: str) -> str:
    return _WS.sub(" ", text or "").strip()


def split_sentences(text: str) -> list[str]:
    text = normalize_space(text)
    if not text:
        return []
    pieces = re.split(r'(?<=[.!?])\s+(?=[A-Z“"])', text)
    result: list[str] = []
    carry = ""
    for piece in pieces:
        piece = f"{carry} {piece}".strip() if carry else piece.strip()
        if ABBREVIATION_PATTERN.search(piece):
            carry = piece
            continue
        carry = ""
        if len(piece.split()) >= 3:
            result.append(piece)
    if carry:
        result.append(carry)
    return result


def context_window(sentences: list[str], position: int) -> str:
    """PREVIOUS / CURRENT / NEXT string used by CAE feature extractor."""
    prev = sentences[position - 1] if position > 0 else ""
    current = sentences[position] if 0 <= position < len(sentences) else ""
    nxt = sentences[position + 1] if position + 1 < len(sentences) else ""
    return f"PREVIOUS {prev} CURRENT {current} NEXT {nxt}"
