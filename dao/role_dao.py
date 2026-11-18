"""Role DAO — table role."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.role import Role
from utils.errors import NotFoundError, ValidationError
from utils.validators import require_nonempty, require_optional_str, require_positive_id, require_role_code


class RoleDAO(BaseDAO):
    table = "role"

    def create(self, role: Role) -> int:
        code = require_role_code(role.role_code)
        name = require_nonempty(role.role_name, "Role name")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO role (role_code, role_name, role_description, is_active)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (role_code) DO UPDATE
                SET role_name = EXCLUDED.role_name,
                    role_description = EXCLUDED.role_description,
                    is_active = EXCLUDED.is_active
                RETURNING role_id
                """,
                (
                    code,
                    name,
                    require_optional_str(role.role_description, "Role description"),
                    bool(role.is_active),
                ),
            )
            return int(cur.fetchone()["role_id"])

    def get_id_by_code(self, role_code: str) -> Optional[int]:
        code = require_role_code(role_code)
        with db_cursor() as cur:
            cur.execute("SELECT role_id FROM role WHERE role_code = %s", (code,))
            row = cur.fetchone()
            return int(row["role_id"]) if row else None

    def read(self, role_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id("role_id", require_positive_id(role_id, "Role ID"))

    def require(self, role_id: int) -> dict[str, Any]:
        row = self.read(role_id)
        if not row:
            raise NotFoundError(f"Role ID {role_id} was not found.")
        return row

    def update(self, role_id: int, **fields: Any) -> int:
        self.require(role_id)
        allowed = {"role_name", "role_description", "is_active"}
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "role_name" in cols:
            cols["role_name"] = require_nonempty(cols["role_name"], "Role name")
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE role SET {sets}, updated_at = NOW() WHERE role_id = %s",
                (*cols.values(), role_id),
            )
        )

    def delete(self, role_id: int) -> int:
        self.require(role_id)
        return self.delete_by_id("role_id", role_id)
