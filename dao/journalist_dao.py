"""Journalist DAO — table journalist."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.journalist import Journalist
from utils.errors import NotFoundError, ValidationError
from utils.validators import (
    require_availability,
    require_desk_status,
    require_optional_str,
    require_positive_id,
)


class JournalistDAO(BaseDAO):
    table = "journalist"

    def create(self, journalist: Journalist) -> int:
        user_id = require_positive_id(journalist.user_id, "User ID")
        availability = require_availability(journalist.availability_status or "available")
        status = require_desk_status(journalist.status or "active")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO journalist (
                    user_id, primary_specialization, secondary_specialization,
                    availability_status, status
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET primary_specialization = EXCLUDED.primary_specialization,
                    secondary_specialization = EXCLUDED.secondary_specialization,
                    availability_status = EXCLUDED.availability_status,
                    status = EXCLUDED.status
                RETURNING journalist_id
                """,
                (
                    user_id,
                    require_optional_str(journalist.primary_specialization, "Primary specialization", max_len=128),
                    require_optional_str(journalist.secondary_specialization, "Secondary specialization", max_len=128),
                    availability,
                    status,
                ),
            )
            return int(cur.fetchone()["journalist_id"])

    def ensure_for_user(self, user_id: int) -> int:
        return self.create(
            Journalist(
                user_id=user_id,
                primary_specialization="General",
                availability_status="available",
            )
        )

    def read(self, journalist_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id("journalist_id", require_positive_id(journalist_id, "Journalist ID"))

    def require(self, journalist_id: int) -> dict[str, Any]:
        row = self.read(journalist_id)
        if not row:
            raise NotFoundError(f"Journalist ID {journalist_id} was not found.")
        return row

    def read_by_user_id(self, user_id: int) -> Optional[dict[str, Any]]:
        user_id = require_positive_id(user_id, "User ID")
        with db_cursor() as cur:
            cur.execute("SELECT * FROM journalist WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update(self, journalist_id: int, **fields: Any) -> int:
        self.require(journalist_id)
        allowed = {
            "primary_specialization",
            "secondary_specialization",
            "availability_status",
            "status",
        }
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "availability_status" in cols:
            cols["availability_status"] = require_availability(cols["availability_status"])
        if "status" in cols:
            cols["status"] = require_desk_status(cols["status"])
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE journalist SET {sets}, updated_at = NOW() WHERE journalist_id = %s",
                (*cols.values(), journalist_id),
            )
        )

    def delete(self, journalist_id: int) -> int:
        self.require(journalist_id)
        return self.delete_by_id("journalist_id", journalist_id)
