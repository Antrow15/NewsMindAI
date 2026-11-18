"""AudienceInsightAnalyst DAO — table audience_insight_analyst."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.audience_insight_analyst import AudienceInsightAnalyst
from utils.errors import NotFoundError, ValidationError
from utils.validators import require_desk_status, require_optional_str, require_positive_id


class AudienceInsightAnalystDAO(BaseDAO):
    table = "audience_insight_analyst"

    def create(self, aia: AudienceInsightAnalyst) -> int:
        user_id = require_positive_id(aia.user_id, "User ID")
        status = require_desk_status(aia.status or "active")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO audience_insight_analyst (user_id, focus_region, status)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET focus_region = EXCLUDED.focus_region, status = EXCLUDED.status
                RETURNING aia_id
                """,
                (
                    user_id,
                    require_optional_str(aia.focus_region, "Focus region", max_len=128),
                    status,
                ),
            )
            return int(cur.fetchone()["aia_id"])

    def ensure_for_user(self, user_id: int) -> int:
        return self.create(AudienceInsightAnalyst(user_id=user_id, focus_region="National"))

    def read(self, aia_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id("aia_id", require_positive_id(aia_id, "AIA ID"))

    def require(self, aia_id: int) -> dict[str, Any]:
        row = self.read(aia_id)
        if not row:
            raise NotFoundError(f"AIA ID {aia_id} was not found.")
        return row

    def read_by_user_id(self, user_id: int) -> Optional[dict[str, Any]]:
        user_id = require_positive_id(user_id, "User ID")
        with db_cursor() as cur:
            cur.execute("SELECT * FROM audience_insight_analyst WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update(self, aia_id: int, **fields: Any) -> int:
        self.require(aia_id)
        allowed = {"focus_region", "status"}
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "status" in cols:
            cols["status"] = require_desk_status(cols["status"])
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE audience_insight_analyst SET {sets}, updated_at = NOW() WHERE aia_id = %s",
                (*cols.values(), aia_id),
            )
        )

    def delete(self, aia_id: int) -> int:
        self.require(aia_id)
        return self.delete_by_id("aia_id", aia_id)
