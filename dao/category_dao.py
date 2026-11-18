"""Category DAO — table category."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.content.category import Category
from utils.errors import NotFoundError, ValidationError
from utils.validators import require_category_name, require_optional_str, require_positive_id


class CategoryDAO(BaseDAO):
    table = "category"

    def create(self, category: Category) -> int:
        name = require_category_name(category.category_name)
        description = require_optional_str(category.description, "Description")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO category (category_name, description, is_active)
                VALUES (%s, %s, %s)
                ON CONFLICT (category_name) DO UPDATE
                SET description = EXCLUDED.description, is_active = EXCLUDED.is_active
                RETURNING category_id
                """,
                (name, description, bool(category.is_active)),
            )
            return int(cur.fetchone()["category_id"])

    def read(self, category_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id("category_id", require_positive_id(category_id, "Category ID"))

    def require(self, category_id: int) -> dict[str, Any]:
        row = self.read(category_id)
        if not row:
            raise NotFoundError(f"Category ID {category_id} was not found.")
        return row

    def update(self, category_id: int, **fields: Any) -> int:
        self.require(category_id)
        allowed = {"category_name", "description", "is_active"}
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "category_name" in cols:
            cols["category_name"] = require_category_name(cols["category_name"])
        if "description" in cols:
            cols["description"] = require_optional_str(cols["description"], "Description")
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE category SET {sets}, updated_at = NOW() WHERE category_id = %s",
                (*cols.values(), category_id),
            )
        )

    def delete(self, category_id: int) -> int:
        self.require(category_id)
        return self.delete_by_id("category_id", category_id)
