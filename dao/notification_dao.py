"""Notification DAO — in-app alerts."""

from __future__ import annotations

import json
from typing import Any

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from utils.validators import require_nonempty, require_positive_id


class NotificationDAO(BaseDAO):
    table = "notification"

    def create(
        self,
        *,
        user_id: int,
        type: str,
        title: str,
        body: str = "",
        payload: dict[str, Any] | None = None,
    ) -> int:
        user_id = require_positive_id(user_id, "User ID")
        type = require_nonempty(type, "Notification type")
        title = require_nonempty(title, "Notification title")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO notification (user_id, type, title, body, payload)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                RETURNING notification_id
                """,
                (
                    user_id,
                    type[:64],
                    title[:512],
                    body or "",
                    json.dumps(payload or {}),
                ),
            )
            return int(cur.fetchone()["notification_id"])

    def list_for_user(
        self,
        user_id: int,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        user_id = require_positive_id(user_id, "User ID")
        limit = max(1, min(int(limit), 200))
        sql = """
            SELECT notification_id, user_id, type, title, body, payload, read_at, created_at
            FROM notification
            WHERE user_id = %s
        """
        params: list[Any] = [user_id]
        if unread_only:
            sql += " AND read_at IS NULL"
        sql += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        rows = self.execute(sql, tuple(params), fetch="all")
        return [dict(r) for r in rows or []]

    def unread_count(self, user_id: int) -> int:
        user_id = require_positive_id(user_id, "User ID")
        row = self.execute(
            "SELECT COUNT(*) AS n FROM notification WHERE user_id = %s AND read_at IS NULL",
            (user_id,),
            fetch="one",
        )
        return int((row or {}).get("n") or 0)

    def mark_read(self, notification_id: int, user_id: int) -> int:
        notification_id = require_positive_id(notification_id, "Notification ID")
        user_id = require_positive_id(user_id, "User ID")
        return int(
            self.execute(
                """
                UPDATE notification
                SET read_at = NOW()
                WHERE notification_id = %s AND user_id = %s AND read_at IS NULL
                """,
                (notification_id, user_id),
            )
        )

    def mark_all_read(self, user_id: int) -> int:
        user_id = require_positive_id(user_id, "User ID")
        return int(
            self.execute(
                """
                UPDATE notification
                SET read_at = NOW()
                WHERE user_id = %s AND read_at IS NULL
                """,
                (user_id,),
            )
        )
