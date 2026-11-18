"""ContentAdaptationEditor DAO — table content_adaptation_editor."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.content_adaptation_editor import ContentAdaptationEditor
from utils.errors import NotFoundError, ValidationError
from utils.validators import require_desk_status, require_optional_str, require_positive_id


class ContentAdaptationEditorDAO(BaseDAO):
    table = "content_adaptation_editor"

    def create(self, cae: ContentAdaptationEditor) -> int:
        user_id = require_positive_id(cae.user_id, "User ID")
        status = require_desk_status(cae.status or "active")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO content_adaptation_editor (user_id, specialization_channel, status)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET specialization_channel = EXCLUDED.specialization_channel,
                    status = EXCLUDED.status
                RETURNING cae_id
                """,
                (
                    user_id,
                    require_optional_str(cae.specialization_channel, "Specialization channel", max_len=128),
                    status,
                ),
            )
            return int(cur.fetchone()["cae_id"])

    def ensure_for_user(self, user_id: int) -> int:
        return self.create(
            ContentAdaptationEditor(user_id=user_id, specialization_channel="digital")
        )

    def read(self, cae_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id("cae_id", require_positive_id(cae_id, "CAE ID"))

    def require(self, cae_id: int) -> dict[str, Any]:
        row = self.read(cae_id)
        if not row:
            raise NotFoundError(f"CAE ID {cae_id} was not found.")
        return row

    def read_by_user_id(self, user_id: int) -> Optional[dict[str, Any]]:
        user_id = require_positive_id(user_id, "User ID")
        with db_cursor() as cur:
            cur.execute("SELECT * FROM content_adaptation_editor WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update(self, cae_id: int, **fields: Any) -> int:
        self.require(cae_id)
        allowed = {"specialization_channel", "status"}
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "status" in cols:
            cols["status"] = require_desk_status(cols["status"])
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE content_adaptation_editor SET {sets}, updated_at = NOW() WHERE cae_id = %s",
                (*cols.values(), cae_id),
            )
        )

    def delete(self, cae_id: int) -> int:
        self.require(cae_id)
        return self.delete_by_id("cae_id", cae_id)
