"""NewsroomManager DAO — table newsroom_manager."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.newsroom_manager import NewsroomManager
from utils.errors import NotFoundError, ValidationError
from utils.validators import require_desk_status, require_optional_str, require_positive_id


class NewsroomManagerDAO(BaseDAO):
    table = "newsroom_manager"

    def create(self, manager: NewsroomManager) -> int:
        user_id = require_positive_id(manager.user_id, "User ID")
        status = require_desk_status(manager.status or "active")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO newsroom_manager (user_id, managed_region, status)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET managed_region = EXCLUDED.managed_region, status = EXCLUDED.status
                RETURNING newsroom_manager_id
                """,
                (
                    user_id,
                    require_optional_str(manager.managed_region, "Managed region", max_len=128),
                    status,
                ),
            )
            return int(cur.fetchone()["newsroom_manager_id"])

    def ensure_for_user(self, user_id: int) -> int:
        return self.create(NewsroomManager(user_id=user_id, managed_region="HQ"))

    def read(self, newsroom_manager_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id(
            "newsroom_manager_id",
            require_positive_id(newsroom_manager_id, "Newsroom manager ID"),
        )

    def require(self, newsroom_manager_id: int) -> dict[str, Any]:
        row = self.read(newsroom_manager_id)
        if not row:
            raise NotFoundError(f"Newsroom manager ID {newsroom_manager_id} was not found.")
        return row

    def read_by_user_id(self, user_id: int) -> Optional[dict[str, Any]]:
        user_id = require_positive_id(user_id, "User ID")
        with db_cursor() as cur:
            cur.execute("SELECT * FROM newsroom_manager WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update(self, newsroom_manager_id: int, **fields: Any) -> int:
        self.require(newsroom_manager_id)
        allowed = {"managed_region", "status"}
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "status" in cols:
            cols["status"] = require_desk_status(cols["status"])
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE newsroom_manager SET {sets}, updated_at = NOW() WHERE newsroom_manager_id = %s",
                (*cols.values(), newsroom_manager_id),
            )
        )

    def delete(self, newsroom_manager_id: int) -> int:
        self.require(newsroom_manager_id)
        return self.delete_by_id("newsroom_manager_id", newsroom_manager_id)
