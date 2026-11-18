"""User-side repository: users, employees, roles, desk profiles."""

from __future__ import annotations

from typing import Any, Optional

from dao.audience_insight_analyst_dao import AudienceInsightAnalystDAO
from dao.content_adaptation_editor_dao import ContentAdaptationEditorDAO
from dao.editor_dao import EditorDAO
from dao.employee_dao import EmployeeDAO
from dao.journalist_dao import JournalistDAO
from dao.newsroom_manager_dao import NewsroomManagerDAO
from dao.publisher_dao import PublisherDAO
from dao.role_dao import RoleDAO
from dao.user_dao import UserDAO
from entities.employee import Employee
from entities.user import User
from utils.errors import NotFoundError


class UserRepository:
    def __init__(self) -> None:
        self.users = UserDAO()
        self.employees = EmployeeDAO()
        self.roles = RoleDAO()
        self.journalists = JournalistDAO()
        self.editors = EditorDAO()
        self.analysts = AudienceInsightAnalystDAO()
        self.adapters = ContentAdaptationEditorDAO()
        self.publishers = PublisherDAO()
        self.managers = NewsroomManagerDAO()

    def ensure_demo_user(self, username: str = "journalist") -> dict[str, Any]:
        existing = self.users.read_by_username(username)
        if existing:
            return existing
        raise NotFoundError(f"User '{username}' missing — run python app.py --init-db")

    def get_profile_ids(self, user_id: int) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, row in (
            ("aia_id", self.analysts.read_by_user_id(user_id)),
            ("editor_id", self.editors.read_by_user_id(user_id)),
            ("journalist_id", self.journalists.read_by_user_id(user_id)),
            ("cae_id", self.adapters.read_by_user_id(user_id)),
            ("publisher_id", self.publishers.read_by_user_id(user_id)),
            ("newsroom_manager_id", self.managers.read_by_user_id(user_id)),
        ):
            if row:
                out[key] = int(row[key])
        return out

    def ensure_desk(self, user_id: int, role_code: str) -> None:
        if role_code == "audience_insight_analyst":
            self.analysts.ensure_for_user(user_id)
        elif role_code == "editor":
            self.editors.ensure_for_user(user_id)
        elif role_code == "journalist":
            self.journalists.ensure_for_user(user_id)
        elif role_code == "content_adaptation_editor":
            self.adapters.ensure_for_user(user_id)
        elif role_code == "publisher":
            self.publishers.ensure_for_user(user_id)
        elif role_code == "newsroom_manager":
            self.managers.ensure_for_user(user_id)

    def create_employee(self, employee: Employee) -> int:
        return self.employees.create(employee)

    def create_user(self, user: User) -> int:
        return self.users.create(user)

    def find_by_username(self, username: str) -> Optional[dict[str, Any]]:
        return self.users.read_by_username(username)

    def role_id_by_code(self, role_code: str) -> Optional[int]:
        return self.roles.get_id_by_code(role_code)
