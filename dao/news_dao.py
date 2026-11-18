"""News DAO — table news."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.content.news import News
from utils.errors import NotFoundError, ValidationError
from utils.validators import (
    require_nonempty,
    require_optional_str,
    require_positive_id,
    require_severity,
)


class NewsDAO(BaseDAO):
    table = "news"

    def create(self, news: News) -> int:
        content_id = require_positive_id(news.content_id, "Content ID")
        severity = require_severity(news.severity or "low")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO news (
                    content_id, event_title, event_type, event_location,
                    event_date, breaking_news_flag, severity
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING news_id
                """,
                (
                    content_id,
                    require_optional_str(news.event_title, "Event title", max_len=512),
                    require_optional_str(news.event_type, "Event type", max_len=128) or "city",
                    require_optional_str(news.event_location, "Event location", max_len=255),
                    news.event_date,
                    bool(news.breaking_news_flag),
                    severity,
                ),
            )
            return int(cur.fetchone()["news_id"])

    def read(self, news_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id("news_id", require_positive_id(news_id, "News ID"))

    def require(self, news_id: int) -> dict[str, Any]:
        row = self.read(news_id)
        if not row:
            raise NotFoundError(f"News ID {news_id} was not found.")
        return row

    def update(self, news_id: int, **fields: Any) -> int:
        self.require(news_id)
        allowed = {
            "event_title",
            "event_type",
            "event_location",
            "event_date",
            "breaking_news_flag",
            "severity",
        }
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "severity" in cols:
            cols["severity"] = require_severity(cols["severity"])
        if "event_type" in cols:
            cols["event_type"] = require_nonempty(cols["event_type"], "Event type")
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE news SET {sets} WHERE news_id = %s",
                (*cols.values(), news_id),
            )
        )

    def delete(self, news_id: int) -> int:
        self.require(news_id)
        return self.delete_by_id("news_id", news_id)
