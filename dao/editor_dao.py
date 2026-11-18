"""Editor DAO — table editor."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.editor import Editor
from utils.errors import NotFoundError, ValidationError
from utils.validators import require_desk_status, require_optional_str, require_positive_id


class EditorDAO(BaseDAO):
    table = "editor"

    def create(self, editor: Editor) -> int:
        user_id = require_positive_id(editor.user_id, "User ID")
        status = require_desk_status(editor.status or "active")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO editor (user_id, editorial_desk, status)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET editorial_desk = EXCLUDED.editorial_desk, status = EXCLUDED.status
                RETURNING editor_id
                """,
                (
                    user_id,
                    require_optional_str(editor.editorial_desk, "Editorial desk", max_len=128),
                    status,
                ),
            )
            return int(cur.fetchone()["editor_id"])

    def ensure_for_user(self, user_id: int) -> int:
        return self.create(Editor(user_id=user_id, editorial_desk="General"))

    def read(self, editor_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id("editor_id", require_positive_id(editor_id, "Editor ID"))

    def require(self, editor_id: int) -> dict[str, Any]:
        row = self.read(editor_id)
        if not row:
            raise NotFoundError(f"Editor ID {editor_id} was not found.")
        return row

    def read_by_user_id(self, user_id: int) -> Optional[dict[str, Any]]:
        user_id = require_positive_id(user_id, "User ID")
        with db_cursor() as cur:
            cur.execute("SELECT * FROM editor WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update(self, editor_id: int, **fields: Any) -> int:
        self.require(editor_id)
        allowed = {"editorial_desk", "status"}
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "status" in cols:
            cols["status"] = require_desk_status(cols["status"])
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE editor SET {sets}, updated_at = NOW() WHERE editor_id = %s",
                (*cols.values(), editor_id),
            )
        )

    def delete(self, editor_id: int) -> int:
        self.require(editor_id)
        return self.delete_by_id("editor_id", editor_id)
