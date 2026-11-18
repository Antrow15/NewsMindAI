"""Publisher publication queue — table publication."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from utils.errors import NotFoundError, ValidationError
from utils.validators import require_optional_str, require_positive_id

ALLOWED_PUBLICATION_STATUSES = ("ready", "approved", "scheduled", "published")


class PublicationDAO(BaseDAO):
    table = "publication"

    def ensure_for_content(self, content_id: int) -> dict[str, Any]:
        content_id = require_positive_id(content_id, "Content ID")
        existing = self.read_by_content_id(content_id)
        if existing:
            return existing
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO publication (content_id, status)
                VALUES (%s, 'ready')
                ON CONFLICT (content_id) DO UPDATE
                SET updated_at = NOW()
                RETURNING *
                """,
                (content_id,),
            )
            return dict(cur.fetchone())

    def read(self, publication_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id(
            "publication_id",
            require_positive_id(publication_id, "Publication ID"),
        )

    def require(self, publication_id: int) -> dict[str, Any]:
        row = self.read(publication_id)
        if not row:
            raise NotFoundError(f"Publication ID {publication_id} was not found.")
        return row

    def read_by_content_id(self, content_id: int) -> Optional[dict[str, Any]]:
        content_id = require_positive_id(content_id, "Content ID")
        with db_cursor() as cur:
            cur.execute("SELECT * FROM publication WHERE content_id = %s", (content_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_ready_articles(self, limit: int = 100) -> list[dict[str, Any]]:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.content_id,
                    c.title,
                    c.summary,
                    c.content_body,
                    c.content_kind,
                    c.status AS content_status,
                    p.publication_id,
                    p.template_code,
                    p.status AS publication_status,
                    p.scheduled_at,
                    p.published_at
                FROM content c
                LEFT JOIN publication p ON p.content_id = c.content_id
                WHERE c.status = 'approved'
                  AND (p.publication_id IS NULL OR p.status IN ('ready', 'approved', 'scheduled'))
                ORDER BY c.content_id DESC
                LIMIT %s
                """,
                (max(1, min(int(limit), 500)),),
            )
            return [dict(r) for r in cur.fetchall() or []]

    def update_fields(self, publication_id: int, **fields: Any) -> dict[str, Any]:
        self.require(publication_id)
        allowed = {"template_code", "status", "scheduled_at", "published_at"}
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "status" in cols:
            status = str(cols["status"]).strip().lower()
            if status not in ALLOWED_PUBLICATION_STATUSES:
                raise ValidationError(
                    f"Invalid publication status. Allowed: {', '.join(ALLOWED_PUBLICATION_STATUSES)}"
                )
            cols["status"] = status
        if "template_code" in cols and cols["template_code"] is not None:
            cols["template_code"] = require_optional_str(
                cols["template_code"], "Template code", max_len=64
            )
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        with db_cursor() as cur:
            cur.execute(
                f"""
                UPDATE publication
                SET {sets}, updated_at = NOW()
                WHERE publication_id = %s
                RETURNING *
                """,
                (*cols.values(), publication_id),
            )
            return dict(cur.fetchone())

    def analytics(self) -> dict[str, Any]:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM publication
                GROUP BY status
                """
            )
            by_status = {str(r["status"]): int(r["count"]) for r in cur.fetchall() or []}
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM content
                WHERE status = 'approved'
                """
            )
            approved_content = int(cur.fetchone()["count"])
        return {
            "approved_content": approved_content,
            "publications_by_status": by_status,
            "published": by_status.get("published", 0),
            "scheduled": by_status.get("scheduled", 0),
            "ready": by_status.get("ready", 0),
            "approved": by_status.get("approved", 0),
        }
