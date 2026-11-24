"""Create multi-platform adaptation requests + drafts."""

from __future__ import annotations

from typing import Any

from config.constants import ADAPTATION_PLATFORMS
from dao.adaptation_dao import AdaptationDAO
from ml.adaptation import format_output, predict_sentences, validate_facts
from utils.errors import ValidationError
from utils.validators import require_nonempty, require_title


class AdaptationService:
    def __init__(self, dao: AdaptationDAO | None = None) -> None:
        self.dao = dao or AdaptationDAO()

    def create(
        self,
        *,
        original_title: str,
        original_content: str,
        target_platforms: list[str],
        created_by: int | None,
    ) -> dict[str, Any]:
        title = require_title(original_title)
        content = require_nonempty(original_content, "Original content")
        if len(content) < 20:
            raise ValidationError("Original content must be at least 20 characters.")
        if not target_platforms:
            raise ValidationError("Select at least one target platform.")

        platforms: list[str] = []
        for raw in target_platforms:
            platform = str(raw).strip().upper()
            if platform not in ADAPTATION_PLATFORMS:
                raise ValidationError(
                    f"Unsupported platform '{raw}'. Allowed: {', '.join(ADAPTATION_PLATFORMS)}"
                )
            if platform in platforms:
                raise ValidationError("target_platforms must not contain duplicates.")
            platforms.append(platform)

        request_id = self.dao.create_request(
            original_title=title,
            original_content=content,
            created_by=created_by,
            status="PROCESSING",
        )
        try:
            for platform in platforms:
                selected, meta, threshold = predict_sentences(title, content, platform)
                adapted_title, adapted_content = format_output(platform, title, selected)
                flags = validate_facts(content, adapted_content)
                status = (
                    "PENDING_REVIEW" if flags.get("passed") else "REQUIRES_MANUAL_REVIEW"
                )
                self.dao.create_draft(
                    request_id=request_id,
                    platform=platform,
                    version_number=1,
                    adapted_title=adapted_title,
                    adapted_content=adapted_content,
                    model_version=str(meta.get("version", "heuristic-1.0.0")),
                    status=status,
                    generation_parameters={
                        "threshold": threshold,
                        "selected_sentence_indexes": [row[0] for row in selected],
                    },
                    validation_flags=flags,
                )
            self.dao.update_request_status(request_id, "COMPLETED")
        except Exception:
            self.dao.update_request_status(request_id, "FAILED")
            raise

        return self.get_request(request_id)

    def get_request(self, request_id: int) -> dict[str, Any]:
        request = self.dao.require_request(request_id)
        drafts = self.dao.list_drafts_for_request(request_id)
        return {**request, "drafts": drafts}

    def review_queue(self, *, limit: int = 50) -> dict[str, Any]:
        items = self.dao.list_review_queue(limit=limit)
        pending = sum(1 for i in items if i.get("draft_status") == "PENDING_REVIEW")
        manual = sum(1 for i in items if i.get("draft_status") == "REQUIRES_MANUAL_REVIEW")
        return {
            "pending_count": pending,
            "manual_count": manual,
            "total": len(items),
            "items": items,
        }

    def recent_requests(self, *, limit: int = 20) -> dict[str, Any]:
        return {"requests": self.dao.list_recent_requests(limit=limit)}

    def source_articles(self, *, limit: int = 30) -> dict[str, Any]:
        """Approved desk stories ready for CAE (not published — those already shipped)."""
        from database.connection import db_cursor

        limit = max(1, min(int(limit), 100))
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.content_id,
                    c.title,
                    c.summary,
                    COALESCE(c.content_body, c.raw_body, '') AS body,
                    c.status,
                    c.updated_at
                FROM content c
                WHERE c.status = 'approved'
                  AND LENGTH(COALESCE(c.content_body, c.raw_body, '')) >= 20
                ORDER BY c.updated_at DESC NULLS LAST, c.content_id DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = [dict(r) for r in cur.fetchall() or []]
        return {"articles": rows}
