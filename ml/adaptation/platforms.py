"""Platform-specific adaptation formatting."""

from __future__ import annotations

import re

from config.constants import (
    PLATFORM_EMAIL,
    PLATFORM_PRINT,
    PLATFORM_SOCIAL,
    PLATFORM_WEB,
)


def clean_title(title: str) -> str:
    return re.sub(r"\s+", " ", title or "").strip().rstrip(".")


def _keywords(text: str, limit: int = 2) -> list[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "will",
        "this",
        "that",
        "have",
        "has",
        "was",
        "were",
        "are",
        "its",
        "into",
        "after",
        "before",
        "about",
    }
    words = re.findall(r"[A-Za-z]{4,}", (text or "").lower())
    counts = {w: words.count(w) for w in set(words) if w not in stop}
    return [w.title() for w, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:limit]]


def format_output(
    platform: str,
    original_title: str,
    selected: list[tuple[int, str, float]],
) -> tuple[str, str]:
    sentences = [item[1] for item in selected]
    title = clean_title(original_title)

    if platform == PLATFORM_SOCIAL:
        content = " ".join(sentences)
        tags = " ".join("#" + k.replace(" ", "") for k in _keywords(content, 2))
        return title, f"{content} {tags}".strip()

    if platform == PLATFORM_EMAIL:
        return title, " ".join(sentences)

    if platform == PLATFORM_PRINT:
        return title, " ".join(sentences)

    # Website — paragraph chunks, no invented summaries
    chunks = []
    for i in range(0, len(sentences), 3):
        chunks.append(" ".join(sentences[i : i + 3]))
    return title, "\n\n".join(chunks)
