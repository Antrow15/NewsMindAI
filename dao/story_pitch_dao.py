"""StoryPitch DAO — table story_pitch."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.content.story_pitch import StoryPitch
from utils.errors import NotFoundError, ValidationError
from utils.validators import (
    require_nonempty,
    require_optional_positive_id,
    require_optional_str,
    require_pitch_status,
    require_positive_id,
    require_priority,
    require_score,
    require_title,
)


class StoryPitchDAO(BaseDAO):
    table = "story_pitch"

    def create(self, pitch: StoryPitch) -> int:
        title = require_title(pitch.title)
        summary = require_nonempty(pitch.summary, "Summary")
        status = require_pitch_status(pitch.status or "submitted")
        priority = require_priority(pitch.priority or "medium")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO story_pitch (
                    audience_insight_id, title, summary, priority, source_type,
                    trend_score, audience_interest_score, coverage_gap_score,
                    status, created_by, approved_by, submitted_at, approved_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING story_pitch_id
                """,
                (
                    require_optional_positive_id(pitch.audience_insight_id, "Audience insight ID"),
                    title,
                    summary,
                    priority,
                    require_optional_str(pitch.source_type, "Source type", max_len=64),
                    require_score(pitch.trend_score, "Trend score"),
                    require_score(pitch.audience_interest_score, "Audience interest score"),
                    require_score(pitch.coverage_gap_score, "Coverage gap score"),
                    status,
                    require_optional_positive_id(pitch.created_by, "Created by"),
                    require_optional_positive_id(pitch.approved_by, "Approved by"),
                    pitch.submitted_at,
                    pitch.approved_at,
                ),
            )
            return int(cur.fetchone()["story_pitch_id"])

    def read(self, story_pitch_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id("story_pitch_id", require_positive_id(story_pitch_id, "Story pitch ID"))

    def require(self, story_pitch_id: int) -> dict[str, Any]:
        row = self.read(story_pitch_id)
        if not row:
            raise NotFoundError(f"Story pitch ID {story_pitch_id} was not found.")
        return row

    def update(self, story_pitch_id: int, **fields: Any) -> int:
        self.require(story_pitch_id)
        allowed = {
            "title",
            "summary",
            "priority",
            "source_type",
            "trend_score",
            "audience_interest_score",
            "coverage_gap_score",
            "status",
            "approved_by",
            "approved_at",
        }
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "title" in cols:
            cols["title"] = require_title(cols["title"])
        if "summary" in cols:
            cols["summary"] = require_nonempty(cols["summary"], "Summary")
        if "status" in cols:
            cols["status"] = require_pitch_status(str(cols["status"]))
        if "priority" in cols:
            cols["priority"] = require_priority(cols["priority"])
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE story_pitch SET {sets}, updated_at = NOW() WHERE story_pitch_id = %s",
                (*cols.values(), story_pitch_id),
            )
        )

    def update_status(self, story_pitch_id: int, status: str) -> int:
        return self.update(story_pitch_id, status=require_pitch_status(status))

    def list_by_status(self, status: str, limit: int = 100) -> list[dict[str, Any]]:
        """List pitches for a status, urgent/high first (Editor queue order)."""
        status = require_pitch_status(status)
        rows = self.execute(
            """
            SELECT * FROM story_pitch
            WHERE status = %s
            ORDER BY
                CASE lower(coalesce(priority, 'medium'))
                    WHEN 'urgent' THEN 0
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4
                END,
                story_pitch_id DESC
            LIMIT %s
            """,
            (status, max(1, min(int(limit), 500))),
            fetch="all",
        )
        return [dict(r) for r in rows or []]

    def delete(self, story_pitch_id: int) -> int:
        self.require(story_pitch_id)
        return self.delete_by_id("story_pitch_id", story_pitch_id)
