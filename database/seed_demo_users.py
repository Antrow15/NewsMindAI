"""Seed demo desks using usernames + passwords from config.constants.DEMO_PASSWORDS."""

from __future__ import annotations

from config.constants import DEMO_PASSWORDS, ROLE_DISPLAY_NAMES
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
from modules.authentication.security import hash_password
from utils.logger import get_logger

log = get_logger("seed_users")

DEMO_USERS = (
    ("admin", "administrator", "System", "Admin", "admin@newsroom.local", None),
    ("analyst", "audience_insight_analyst", "Asha", "Analyst", "analyst@newsroom.local", None),
    ("journalist", "journalist", "Jordan", "Journalist", "journalist@newsroom.local", "General"),
    ("journalist2", "journalist", "Riley", "City", "journalist2@newsroom.local", "City"),
    ("journalist3", "journalist", "Sam", "Politics", "journalist3@newsroom.local", "Politics"),
    ("editor", "editor", "Elena", "Editor", "editor@newsroom.local", None),
    ("adapter", "content_adaptation_editor", "Casey", "Adapter", "adapter@newsroom.local", None),
    ("publisher", "publisher", "Priya", "Publisher", "publisher@newsroom.local", None),
    ("manager", "newsroom_manager", "Morgan", "Manager", "manager@newsroom.local", None),
)


def _ensure_profile(user_id: int, role_code: str, specialty: str | None = None) -> None:
    if role_code == "audience_insight_analyst":
        AudienceInsightAnalystDAO().ensure_for_user(user_id)
    elif role_code == "editor":
        EditorDAO().ensure_for_user(user_id)
    elif role_code == "journalist":
        from entities.journalist import Journalist

        JournalistDAO().create(
            Journalist(
                user_id=user_id,
                primary_specialization=specialty or "General",
                availability_status="available",
            )
        )
    elif role_code == "content_adaptation_editor":
        ContentAdaptationEditorDAO().ensure_for_user(user_id)
    elif role_code == "publisher":
        PublisherDAO().ensure_for_user(user_id)
    elif role_code == "newsroom_manager":
        NewsroomManagerDAO().ensure_for_user(user_id)


def seed_demo_users() -> int:
    employees = EmployeeDAO()
    users = UserDAO()
    roles = RoleDAO()
    created = 0
    for username, role_code, first, last, email, specialty in DEMO_USERS:
        role_id = roles.get_id_by_code(role_code)
        if role_id is None:
            raise RuntimeError(f"Missing role {role_code} — run python app.py --init-db first")
        # Idempotent: skip usernames that already exist.
        if users.read_by_username(username):
            log.info("Skip existing user=%s", username)
            continue
        emp_id = employees.create(
            Employee(
                employee_code=f"NF-{username.upper()}",
                first_name=first,
                last_name=last,
                email=email,
                department="Newsroom",
                designation=ROLE_DISPLAY_NAMES.get(role_code, role_code),
            )
        )
        user_id = users.create(
            User(
                employee_id=emp_id,
                role_id=role_id,
                username=username,
                password_hash=hash_password(DEMO_PASSWORDS[username]),
                account_status="active",
            )
        )
        _ensure_profile(user_id, role_code, specialty)
        created += 1
        log.info("Seeded user=%s role=%s", username, role_code)
    return created
