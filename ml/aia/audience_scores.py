"""AIA audience scores — formulas only (no category model).

1) Engagement score  — formula from views/likes/shares/comments
2) Audience interest — formula from how intense the interactions are
3) Trend score       — heuristic from headline/body cues
"""

from __future__ import annotations

import re
from typing import Any

TREND_WORDS = re.compile(
    r"\b(breaking|surge|record|viral|trending|boom|crisis|election|finals|"
    r"championship|outbreak|ban|protest|strike|launch)\b",
    re.I,
)


def predict_engagement(
    *,
    views: float = 120,
    likes: float = 25,
    shares: float = 8,
    comments: float = 4,
) -> dict[str, Any]:
    """Simple engagement score from interaction counts."""
    raw = likes * 2.0 + shares * 3.0 + comments * 4.0 + views * 0.05
    score = round(min(100.0, max(0.0, raw / 10.0)), 2)
    return {
        "engagement_score": score,
        "source": "heuristic",
        "raw": round(raw, 4),
        "features_used": ["views", "likes", "shares", "comments"],
    }


def predict_interest(
    *,
    views: float = 120,
    likes: float = 25,
    shares: float = 8,
    comments: float = 4,
    engagement_raw: float | None = None,
) -> dict[str, Any]:
    """Simple audience-interest score (interactions per view)."""
    if engagement_raw is None:
        engagement_raw = float(
            predict_engagement(views=views, likes=likes, shares=shares, comments=comments)["raw"]
        )

    intensity = (likes + shares * 2.0 + comments * 2.0) / max(float(views), 1.0)
    score = round(min(100.0, max(0.0, intensity * 100.0)), 2)

    if score >= 70:
        segment = 2  # high interest
    elif score >= 35:
        segment = 1  # medium
    else:
        segment = 0  # low

    return {
        "audience_interest_score": score,
        "source": "heuristic",
        "segment": segment,
        "distance": None,
        "engagement_raw": round(float(engagement_raw), 4),
    }


def predict_trend(headline: str = "", body: str = "") -> dict[str, Any]:
    """Trend score from simple text cues (no category model)."""
    text = f"{headline or ''}. {body or ''}".strip()
    hits = len(TREND_WORDS.findall(text))
    length_boost = min(15.0, len(text.split()) / 20.0)
    score = round(min(100.0, max(20.0, 45.0 + hits * 12.0 + length_boost)), 2)
    return {
        "trend_score": score,
        "source": "heuristic",
        "category": None,
        "category_confidence": None,
    }
