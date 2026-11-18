"""1 — News Research & Discovery."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ml.common import rank


def search_related_news(
    query: str,
    documents: Sequence[Mapping[str, Any]] | None = None,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Find related news by TF-style cosine ranking. Empty corpus → []."""
    return rank(query, documents or [], limit=limit)
