"""User domain service — employee/user/desk creation with validation."""

from __future__ import annotations

from typing import Any

from config.constants import CAP_MANAGE_USERS, ROLE_ADMIN, ROLE_NEWSROOM_MANAGER
from entities.employee import Employee
from entities.user import User
from modules.authentication.auth_service import admin_reset_password
from modules.authentication.security import hash_password
from repository.user_repository import UserRepository
from services.access import require_capability_session
from utils.errors import NotFoundError, ValidationError
from utils.validators import (
    require_email,
    require_nonempty,
    require_password,
    require_role_code,
    require_username,
)


class UserService:
    def __init__(self, repo: UserRepository | None = None) -> None:
        self.repo = repo or UserRepository()

    def add_user(
        self,
        *,
        username: str,
        password: str,
        first_name: str,
        last_name: str,
        email: str,
        role_code: str = "journalist",
        employee_code: str | None = None,
        session_token: str | None = None,
    ) -> dict[str, Any]:
        actor = require_capability_session(CAP_MANAGE_USERS, session_token)
        username = require_username(username)
        password = require_password(password)
        first_name = require_nonempty(first_name, "First name")
        last_name = require_nonempty(last_name, "Last name")
        email = require_email(email)
        role_code = require_role_code(role_code)
        if actor["role_code"] == ROLE_NEWSROOM_MANAGER and role_code == ROLE_ADMIN:
            raise ValidationError("Newsroom managers cannot create administrator accounts.")

        if self.repo.find_by_username(username):
            raise ValidationError(f"Username '{username}' already exists.")

        role_id = self.repo.role_id_by_code(role_code)
        if role_id is None:
            raise ValidationError(f"Unknown role code: {role_code}")

        code = (employee_code or f"EMP-{username.upper()}").strip()
        emp_id = self.repo.create_employee(
            Employee(
                employee_code=code,
                first_name=first_name,
                last_name=last_name,
                email=email,
                department="Newsroom",
                designation=role_code,
            )
        )
        user_id = self.repo.create_user(
            User(
                employee_id=emp_id,
                role_id=role_id,
                username=username,
                password_hash=hash_password(password),
                account_status="active",
            )
        )
        self.repo.ensure_desk(user_id, role_code)
        return {"user_id": user_id, "username": username, "role_code": role_code}

    def find_user(self, username: str) -> dict[str, Any]:
        username = require_username(username)
        user = self.repo.find_by_username(username)
        if not user:
            raise NotFoundError(f"User '{username}' was not found.")
        return user

    def reset_password(
        self,
        username: str,
        new_password: str,
        *,
        session_token: str | None = None,
    ) -> dict[str, Any]:
        """Password reset for another account (manage_users capability)."""
        require_capability_session(CAP_MANAGE_USERS, session_token)
        return admin_reset_password(username, new_password)
