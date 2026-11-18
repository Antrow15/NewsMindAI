"""Article DAO — table article."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.content.article import Article
from utils.errors import NotFoundError, ValidationError
from utils.validators import (
    require_article_type,
    require_optional_positive_id,
    require_positive_id,
    require_read_time,
)


class ArticleDAO(BaseDAO):
    table = "article"

    def create(self, article: Article) -> int:
        content_id = require_positive_id(article.content_id, "Content ID")
        article_type = require_article_type(article.article_type or "feature")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO article (content_id, story_pitch_id, article_type, estimated_read_time)
                VALUES (%s, %s, %s, %s)
                RETURNING article_id
                """,
                (
                    content_id,
                    require_optional_positive_id(article.story_pitch_id, "Story pitch ID"),
                    article_type,
                    require_read_time(article.estimated_read_time),
                ),
            )
            return int(cur.fetchone()["article_id"])

    def read(self, article_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id("article_id", require_positive_id(article_id, "Article ID"))

    def require(self, article_id: int) -> dict[str, Any]:
        row = self.read(article_id)
        if not row:
            raise NotFoundError(f"Article ID {article_id} was not found.")
        return row

    def update(self, article_id: int, **fields: Any) -> int:
        self.require(article_id)
        allowed = {"story_pitch_id", "article_type", "estimated_read_time"}
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "article_type" in cols:
            cols["article_type"] = require_article_type(cols["article_type"])
        if "estimated_read_time" in cols:
            cols["estimated_read_time"] = require_read_time(cols["estimated_read_time"])
        if "story_pitch_id" in cols:
            cols["story_pitch_id"] = require_optional_positive_id(cols["story_pitch_id"], "Story pitch ID")
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE article SET {sets} WHERE article_id = %s",
                (*cols.values(), article_id),
            )
        )

    def delete(self, article_id: int) -> int:
        self.require(article_id)
        return self.delete_by_id("article_id", article_id)
