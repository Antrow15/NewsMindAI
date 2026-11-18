"""Publisher DAO — table publisher."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.publisher import Publisher
from utils.errors import NotFoundError, ValidationError
from utils.validators import require_desk_status, require_optional_str, require_positive_id


class PublisherDAO(BaseDAO):
    table = "publisher"

    def create(self, publisher: Publisher) -> int:
        user_id = require_positive_id(publisher.user_id, "User ID")
        status = require_desk_status(publisher.status or "active")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO publisher (user_id, publishing_group, status)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET publishing_group = EXCLUDED.publishing_group, status = EXCLUDED.status
                RETURNING publisher_id
                """,
                (
                    user_id,
                    require_optional_str(publisher.publishing_group, "Publishing group", max_len=128),
                    status,
                ),
            )
            return int(cur.fetchone()["publisher_id"])

    def ensure_for_user(self, user_id: int) -> int:
        return self.create(Publisher(user_id=user_id, publishing_group="Primary"))

    def read(self, publisher_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id("publisher_id", require_positive_id(publisher_id, "Publisher ID"))

    def require(self, publisher_id: int) -> dict[str, Any]:
        row = self.read(publisher_id)
        if not row:
            raise NotFoundError(f"Publisher ID {publisher_id} was not found.")
        return row

    def read_by_user_id(self, user_id: int) -> Optional[dict[str, Any]]:
        user_id = require_positive_id(user_id, "User ID")
        with db_cursor() as cur:
            cur.execute("SELECT * FROM publisher WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update(self, publisher_id: int, **fields: Any) -> int:
        self.require(publisher_id)
        allowed = {"publishing_group", "status"}
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "status" in cols:
            cols["status"] = require_desk_status(cols["status"])
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE publisher SET {sets}, updated_at = NOW() WHERE publisher_id = %s",
                (*cols.values(), publisher_id),
            )
        )

    def delete(self, publisher_id: int) -> int:
        self.require(publisher_id)
        return self.delete_by_id("publisher_id", publisher_id)
