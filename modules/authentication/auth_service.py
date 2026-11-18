"""Login / logout / session resolve.

Login: **username** + password (email on employee only).
Sessions are application-layer (no user_session table in your ERD).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from config.constants import SESSION_TTL_HOURS
from dao.user_dao import UserDAO
from modules.authentication.security import generate_session_token, hash_password, verify_password
from repository.user_repository import UserRepository
from services.permission_service import capabilities_for_role
from utils.errors import ValidationError
from utils.helpers import project_path
from utils.validators import require_password, require_username

SESSION_FILE = project_path("logs", ".session_token")

# API sessions: token → {user_id, expires_at} (simple in-memory store)
_API_SESSIONS: dict[str, dict[str, Any]] = {}


class AuthenticationError(Exception):
    pass


def _expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)


def _parse_expires(expires_raw: str) -> Optional[datetime]:
    if not expires_raw:
        return None
    expires = datetime.fromisoformat(expires_raw)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires


def _is_expired(expires: Optional[datetime]) -> bool:
    if expires is None:
        return True
    return expires <= datetime.now(timezone.utc)


def _save_session(user_id: int, token: str) -> None:
    """CLI file session (single active console user) + API token map."""
    expires = _expires_at()
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(
        json.dumps(
            {
                "user_id": user_id,
                "token": token,
                "expires_at": expires.isoformat(),
            }
        ),
        encoding="utf-8",
    )
    _API_SESSIONS[token] = {"user_id": user_id, "expires_at": expires.isoformat()}


def _load_session() -> Optional[dict[str, Any]]:
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    expires = _parse_expires(str(data.get("expires_at") or ""))
    if _is_expired(expires):
        return None
    return data


def _load_api_session(token: str) -> Optional[dict[str, Any]]:
    data = _API_SESSIONS.get(token)
    if not data:
        # Fall back to CLI file if token matches
        file_data = _load_session()
        if file_data and file_data.get("token") == token:
            return file_data
        return None
    expires = _parse_expires(str(data.get("expires_at") or ""))
    if _is_expired(expires):
        _API_SESSIONS.pop(token, None)
        return None
    return data


def _clear_session() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
    _API_SESSIONS.clear()


def _user_payload(user: dict[str, Any]) -> dict[str, Any]:
    role_code = str(user.get("role_code") or "")
    profiles = UserRepository().get_profile_ids(int(user["user_id"]))
    return {
        "user_id": int(user["user_id"]),
        "username": user["username"],
        "email": user.get("email"),
        "full_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
        "role_code": role_code,
        "role_name": user.get("role_name"),
        "capabilities": list(capabilities_for_role(role_code)),
        "profiles": profiles,
    }


def authenticate(
    username: str,
    password: str,
    *,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict[str, Any]:
    del ip_address, user_agent  # reserved for future audit; no DB session row
    username = (username or "").strip()
    if not username or not password:
        raise AuthenticationError("Username and password are required.")

    users = UserDAO()
    user = users.read_by_username(username)
    if user is None:
        raise AuthenticationError("Invalid username or password.")

    if user.get("account_status") != "active":
        raise AuthenticationError("This account is inactive.")

    if not verify_password(password, user["password_hash"]):
        raise AuthenticationError("Invalid username or password.")

    users.record_login_success(int(user["user_id"]))
    token = generate_session_token()
    _save_session(int(user["user_id"]), token)
    payload = _user_payload(user)
    payload["session_token"] = token
    return payload


def resolve_session(session_token: str | None = None) -> dict[str, Any]:
    if session_token:
        data = _load_api_session(session_token)
    else:
        data = _load_session()
    if not data:
        raise AuthenticationError("Invalid or expired session.")
    user = UserDAO().read_by_id(int(data["user_id"]))
    if not user or user.get("account_status") != "active":
        raise AuthenticationError("Invalid or expired session.")
    return _user_payload(user)


def logout(session_token: str | None = None) -> None:
    if session_token:
        _API_SESSIONS.pop(session_token, None)
        file_data = _load_session()
        if file_data and file_data.get("token") == session_token:
            if SESSION_FILE.exists():
                SESSION_FILE.unlink()
        return
    _clear_session()


def change_password(user_id: int, current_password: str, new_password: str) -> None:
    """Logged-in user changes their own password (must know current password)."""
    if not current_password:
        raise ValidationError("Current password cannot be empty.")
    new_password = require_password(new_password)
    if current_password == new_password:
        raise ValidationError("New password must be different from the current password.")

    users = UserDAO()
    user = users.require(int(user_id))
    if not verify_password(current_password, user["password_hash"]):
        raise AuthenticationError("Current password is incorrect.")
    users.update_password_hash(int(user["user_id"]), hash_password(new_password))


def admin_reset_password(username: str, new_password: str) -> dict[str, Any]:
    """Administrator sets a new password for any user (no old password required)."""
    username = require_username(username)
    new_password = require_password(new_password)
    users = UserDAO()
    user = users.read_by_username(username)
    if user is None:
        raise AuthenticationError(f"User '{username}' was not found.")
    users.update_password_hash(int(user["user_id"]), hash_password(new_password))
    return {"user_id": int(user["user_id"]), "username": user["username"]}
