"""Audience Insight Analyst — scores, category, story pitches.

Pitch importance = simple weighted formula (NOT the editor queue urgency model).
Editor queue urgency lives in ml/editor/queue_urgency.py.
"""

from __future__ import annotations

from typing import Any

from database.connection import db_cursor
from entities.content.story_pitch import StoryPitch
from ml.aia import predict_engagement, predict_interest, predict_trend
from repository.content_repository import ContentRepository
from utils.errors import ValidationError


def _pitch_importance(
    trend_score: float,
    audience_interest_score: float,
    coverage_gap_score: float,
) -> str:
    """Combine scores into low / medium / high pitch importance."""
    score = (trend_score * 0.4) + (audience_interest_score * 0.4) + (coverage_gap_score * 0.2)
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


class AIAService:
    def __init__(self, repo: ContentRepository | None = None) -> None:
        self.repo = repo or ContentRepository()

    def analyze_engagement(
        self,
        *,
        views: float = 120,
        likes: float = 25,
        shares: float = 8,
        comments: float = 4,
    ) -> dict[str, Any]:
        return predict_engagement(views=views, likes=likes, shares=shares, comments=comments)

    def analyze_interest(
        self,
        *,
        views: float = 120,
        likes: float = 25,
        shares: float = 8,
        comments: float = 4,
    ) -> dict[str, Any]:
        return predict_interest(views=views, likes=likes, shares=shares, comments=comments)

    def analyze_trends(self, title: str = "", summary: str = "") -> dict[str, Any]:
        headline = title or "Audience trend scan across recent newsroom coverage"
        return predict_trend(headline, summary)

    def generate_story_pitch(self, payload: Any) -> dict[str, Any]:
        title = str(payload.title)
        summary = str(payload.summary or "")
        category = str(getattr(payload, "category", "") or "").strip()
        if not category:
            raise ValidationError("category is required (manual entry; no category model).")

        trend_score = float(payload.trend_score or 0)
        interest_score = float(payload.audience_interest_score or 0)
        coverage_gap = float(payload.coverage_gap_score or 0)

        if trend_score <= 0:
            trend_score = float(predict_trend(title, summary)["trend_score"])
        if interest_score <= 0:
            interest_score = float(
                predict_interest(
                    views=float(getattr(payload, "views", 120) or 120),
                    likes=float(getattr(payload, "likes", 25) or 25),
                    shares=float(getattr(payload, "shares", 8) or 8),
                    comments=float(getattr(payload, "comments", 4) or 4),
                )["audience_interest_score"]
            )
        if coverage_gap <= 0:
            coverage_gap = 40.0

        pitch_importance = _pitch_importance(trend_score, interest_score, coverage_gap)

        # DB column is still named "priority"; API uses clearer "pitch_importance"
        pitch = StoryPitch(
            title=title,
            summary=summary,
            priority=pitch_importance,
            source_type="AI_GENERATED",
            trend_score=trend_score,
            audience_interest_score=interest_score,
            coverage_gap_score=coverage_gap,
            status="submitted",
        )
        pitch_id = self.repo.save_pitch(pitch)
        return {
            "story_pitch_id": pitch_id,
            "title": title,
            "summary": summary,
            "pitch_importance": pitch_importance,
            "priority": pitch_importance,
            "importance_source": "formula",
            "source_type": "AI_GENERATED",
            "created_by_desk": "AIA",
            "category": category,
            "trend_score": trend_score,
            "audience_interest_score": interest_score,
            "coverage_gap_score": coverage_gap,
        }

    def get_story_pitches(self) -> dict[str, Any]:
        pitches = self.repo.pitches.list_all()
        return {"pitches": [_annotate_pitch_source(p) for p in pitches]}

    def get_top_story_pitches(self) -> dict[str, Any]:
        pitches = self.repo.pitches.list_all()
        pitches = sorted(
            pitches,
            key=lambda row: (
                float(row.get("trend_score") or 0)
                + float(row.get("audience_interest_score") or 0)
            ),
            reverse=True,
        )
        return {"pitches": [_annotate_pitch_source(p) for p in pitches[:10]]}

    def performance_analytics(self) -> dict[str, Any]:
        """Close the diagram loop: publication/content outcomes back to AIA."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM publication
                GROUP BY status
                """
            )
            publication_by_status = {
                str(r["status"]): int(r["count"]) for r in cur.fetchall() or []
            }

            cur.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM content
                GROUP BY status
                """
            )
            content_by_status = {str(r["status"]): int(r["count"]) for r in cur.fetchall() or []}

            cur.execute(
                """
                SELECT status, COUNT(*) AS count,
                       ROUND(AVG(COALESCE(trend_score, 0))::numeric, 2) AS avg_trend,
                       ROUND(AVG(COALESCE(audience_interest_score, 0))::numeric, 2) AS avg_interest
                FROM story_pitch
                GROUP BY status
                """
            )
            pitch_outcomes = [
                {
                    "status": str(r["status"]),
                    "count": int(r["count"]),
                    "avg_trend": float(r["avg_trend"] or 0),
                    "avg_interest": float(r["avg_interest"] or 0),
                }
                for r in cur.fetchall() or []
            ]

            cur.execute(
                """
                SELECT source_type, COUNT(*) AS count
                FROM story_pitch
                GROUP BY source_type
                """
            )
            pitches_by_source = {
                str(r["source_type"] or "UNKNOWN"): int(r["count"]) for r in cur.fetchall() or []
            }

            cur.execute(
                """
                SELECT c.title, p.status AS publication_status, p.published_at
                FROM publication p
                JOIN content c ON c.content_id = p.content_id
                WHERE p.status IN ('published', 'scheduled')
                ORDER BY COALESCE(p.published_at, p.updated_at) DESC NULLS LAST
                LIMIT 10
                """
            )
            recent_published = [dict(r) for r in cur.fetchall() or []]

        published = publication_by_status.get("published", 0)
        scheduled = publication_by_status.get("scheduled", 0)
        approved_content = content_by_status.get("approved", 0)
        insights = []
        if published + scheduled > 0:
            insights.append(
                f"{published} published and {scheduled} scheduled items — reuse winning topics in new pitches."
            )
        if approved_content:
            insights.append(
                f"{approved_content} approved pieces awaiting adaptation/publish — check coverage gaps."
            )
        aia_pitches = pitches_by_source.get("AI_GENERATED", 0)
        manual_pitches = pitches_by_source.get("MANUAL", 0) + pitches_by_source.get("UNKNOWN", 0)
        insights.append(
            f"Pitch mix: {aia_pitches} AIA-generated vs {manual_pitches} manual/other."
        )

        return {
            "publication_by_status": publication_by_status,
            "content_by_status": content_by_status,
            "pitch_outcomes": pitch_outcomes,
            "pitches_by_source": pitches_by_source,
            "recent_published": recent_published,
            "insights": insights,
            "loop": "publication/content outcomes → AIA performance → story pitch workspace",
        }


def _annotate_pitch_source(pitch: dict[str, Any]) -> dict[str, Any]:
    source = str(pitch.get("source_type") or "").strip().upper() or "UNKNOWN"
    if source in {"AI_GENERATED", "AIA", "AI"}:
        created_by = "AIA"
        source_type = "AI_GENERATED"
    elif source in {"MANUAL", "EDITOR", "HUMAN"}:
        created_by = "MANUAL"
        source_type = "MANUAL"
    else:
        created_by = "UNKNOWN"
        source_type = source
    return {
        **pitch,
        "source_type": source_type,
        "created_by_desk": created_by,
    }
