"""6 — News Credibility Assessment."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ml.common import normalize, rank
from services.journalist.evidence_search import search_evidence


def _simple_claims(text: str) -> list[str]:
    """Split into short claim-like sentences (rule-based, no ML)."""
    raw = normalize(text)
    if not raw:
        return []
    parts = [p.strip() for p in raw.replace("!", ".").replace("?", ".").split(".")]
    return [p for p in parts if len(p.split()) >= 4][:10]


def assess_credibility(
    text: str,
    evidence_docs: Sequence[Mapping[str, Any]] | None = None,
    *,
    limit: int = 5,
) -> dict[str, Any]:
    """Label claims as supported / unverified using evidence search + similarity."""
    claims = _simple_claims(text)
    docs = list(evidence_docs or [])
    if not claims:
        return {"claims": [], "summary": "no_claims"}

    results: list[dict[str, Any]] = []
    for claim in claims:
        hits = search_evidence(claim, docs, limit=limit)
        if not hits:
            # still try full-corpus rank (same helper) for empty-shaped docs
            hits = rank(claim, docs, limit=limit)
        best = hits[0]["score"] if hits else 0.0
        if best >= 0.35:
            label = "supported"
        elif best > 0:
            label = "weak_support"
        else:
            label = "unverified"
        results.append(
            {
                "claim": claim,
                "label": label,
                "score": best,
                "evidence": hits[:3],
            }
        )

    labels = {row["label"] for row in results}
    if labels == {"supported"}:
        summary = "supported"
    elif "supported" in labels or "weak_support" in labels:
        summary = "mixed"
    else:
        summary = "unverified"

    return {"claims": results, "summary": summary}
