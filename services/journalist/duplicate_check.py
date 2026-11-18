"""4 — Duplicate & Plagiarism Detection (editorial — not ingest cleaner)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ml.common import similar_pairs


def find_duplicates(
    documents: Sequence[Mapping[str, Any]] | None = None,
    *,
    threshold: float = 0.5,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Near-duplicate pairs via shared MinHash helper. Empty → []."""
    return similar_pairs(documents or [], threshold=threshold, limit=limit)
