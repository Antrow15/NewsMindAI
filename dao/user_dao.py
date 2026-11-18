"""User DAO — ERD USER / physical table users."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.user import User
from utils.errors import NotFoundError, ValidationError
from utils.validators import (
    require_account_status,
    require_nonempty,
    require_positive_id,
    require_username,
)


class UserDAO(BaseDAO):
    table = "users"

    def create(self, user: User) -> int:
        employee_id = require_positive_id(user.employee_id, "Employee ID")
        role_id = require_positive_id(user.role_id, "Role ID")
        username = require_username(user.username)
        password_hash = require_nonempty(user.password_hash, "Password hash")
        status = require_account_status(user.account_status or "active")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (
                    employee_id, role_id, username, password_hash, account_status
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (username) DO UPDATE
                SET password_hash = EXCLUDED.password_hash,
                    account_status = EXCLUDED.account_status,
                    role_id = EXCLUDED.role_id,
                    updated_at = NOW()
                RETURNING user_id
                """,
                (employee_id, role_id, username, password_hash, status),
            )
            return int(cur.fetchone()["user_id"])

    def read(self, user_id: int) -> Optional[dict[str, Any]]:
        return self.read_by_id(user_id)

    def read_by_id(self, user_id: int) -> Optional[dict[str, Any]]:
        user_id = require_positive_id(user_id, "User ID")
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT u.*, e.email, e.first_name, e.last_name, r.role_code, r.role_name
                FROM users u
                JOIN employee e ON e.employee_id = u.employee_id
                JOIN role r ON r.role_id = u.role_id
                WHERE u.user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def require(self, user_id: int) -> dict[str, Any]:
        row = self.read_by_id(user_id)
        if not row:
            raise NotFoundError(f"User ID {user_id} was not found.")
        return row

    def read_by_username(self, username: str) -> Optional[dict[str, Any]]:
        username = require_username(username)
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT u.*, e.email, e.first_name, e.last_name, r.role_code, r.role_name
                FROM users u
                JOIN employee e ON e.employee_id = u.employee_id
                JOIN role r ON r.role_id = u.role_id
                WHERE u.username = %s
                """,
                (username,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def update(self, user_id: int, **fields: Any) -> int:
        self.require(user_id)
        allowed = {"role_id", "password_hash", "account_status"}
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "role_id" in cols:
            cols["role_id"] = require_positive_id(cols["role_id"], "Role ID")
        if "password_hash" in cols:
            cols["password_hash"] = require_nonempty(cols["password_hash"], "Password hash")
        if "account_status" in cols:
            cols["account_status"] = require_account_status(cols["account_status"])
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE users SET {sets}, updated_at = NOW() WHERE user_id = %s",
                (*cols.values(), user_id),
            )
        )

    def update_account_status(self, user_id: int, status: str) -> int:
        return self.update(user_id, account_status=require_account_status(status))

    def update_password_hash(self, user_id: int, password_hash: str) -> int:
        """Set a new password hash and stamp password_changed_at."""
        user_id = require_positive_id(user_id, "User ID")
        password_hash = require_nonempty(password_hash, "Password hash")
        self.require(user_id)
        return int(
            self.execute(
                """
                UPDATE users
                SET password_hash = %s,
                    password_changed_at = NOW(),
                    updated_at = NOW()
                WHERE user_id = %s
                """,
                (password_hash, user_id),
            )
        )

    def record_login_success(self, user_id: int) -> None:
        self.execute(
            "UPDATE users SET last_login = NOW(), updated_at = NOW() WHERE user_id = %s",
            (require_positive_id(user_id, "User ID"),),
        )

    def delete(self, user_id: int) -> int:
        self.require(user_id)
        return self.delete_by_id("user_id", user_id)
