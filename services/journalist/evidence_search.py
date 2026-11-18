"""2 — Evidence Search & Retrieval."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ml.common import normalize, rank


def search_evidence(
    query: str,
    documents: Sequence[Mapping[str, Any]] | None = None,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Rank evidence docs against a query. Empty corpus → []."""
    if not normalize(query):
        return []
    return rank(query, documents or [], limit=limit)
