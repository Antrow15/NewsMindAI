"""Content DAO — table content."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.content.content import Content
from utils.errors import NotFoundError, ValidationError
from utils.validators import (
    require_content_kind,
    require_content_status,
    require_optional_positive_id,
    require_optional_str,
    require_positive_id,
    require_title,
)


class ContentDAO(BaseDAO):
    table = "content"

    def create(self, content: Content) -> int:
        status = require_content_status(content.status or "draft")
        kind = require_content_kind(content.content_kind or "article")
        title = require_title(content.title)
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO content (
                    author_id, title, summary, raw_body, content_body,
                    content_kind, source_type, status, current_version
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING content_id
                """,
                (
                    require_optional_positive_id(content.author_id, "Author ID"),
                    title,
                    require_optional_str(content.summary, "Summary"),
                    require_optional_str(content.raw_body, "Raw body"),
                    require_optional_str(content.content_body, "Content body"),
                    kind,
                    require_optional_str(content.source_type, "Source type", max_len=128),
                    status,
                    int(content.current_version or 1),
                ),
            )
            return int(cur.fetchone()["content_id"])

    def read(self, content_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id("content_id", content_id)

    def require(self, content_id: int) -> dict[str, Any]:
        row = self.read(content_id)
        if not row:
            raise NotFoundError(f"Content ID {content_id} was not found.")
        return row

    def update(self, content_id: int, **fields: Any) -> int:
        self.require(content_id)
        allowed = {
            "author_id",
            "title",
            "summary",
            "raw_body",
            "content_body",
            "content_kind",
            "source_type",
            "status",
            "current_version",
        }
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "title" in cols:
            cols["title"] = require_title(cols["title"])
        if "status" in cols:
            cols["status"] = require_content_status(str(cols["status"]))
        if "content_kind" in cols:
            cols["content_kind"] = require_content_kind(str(cols["content_kind"]))
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE content SET {sets}, updated_at = NOW() WHERE content_id = %s",
                (*cols.values(), content_id),
            )
        )

    def update_status(self, content_id: int, status: str) -> int:
        return self.update(content_id, status=status)

    def list_by_status(self, status: str, limit: int = 100) -> list[dict[str, Any]]:
        status = require_content_status(status)
        rows = self.execute(
            """
            SELECT * FROM content
            WHERE status = %s
            ORDER BY content_id DESC
            LIMIT %s
            """,
            (status, max(1, min(int(limit), 500))),
            fetch="all",
        )
        return [dict(r) for r in rows or []]

    def delete(self, content_id: int) -> int:
        self.require(content_id)
        return self.delete_by_id("content_id", content_id)
