"""Login / logout / JWT resolve.

Login: **username** + password (email on employee only).
Access tokens are signed JWTs (HS256). User/role are re-loaded from DB on each request.
Logout uses an in-memory jti denylist (process-local) plus clears the CLI token file.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

import jwt

from dao.user_dao import UserDAO
from modules.authentication.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from repository.user_repository import UserRepository
from services.permission_service import capabilities_for_role
from utils.errors import ValidationError
from utils.helpers import project_path
from utils.validators import require_password, require_username

SESSION_FILE = project_path("logs", ".session_token")

# jti values revoked before natural JWT expiry (logout). Process-local.
_REVOKED_JTI: dict[str, datetime] = {}


class AuthenticationError(Exception):
    pass


def _purge_expired_revocations() -> None:
    now = datetime.now(timezone.utc)
    expired = [jti for jti, exp in _REVOKED_JTI.items() if exp <= now]
    for jti in expired:
        _REVOKED_JTI.pop(jti, None)


def _revoke_jti(jti: str, expires_at: datetime) -> None:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    _REVOKED_JTI[jti] = expires_at


def _is_revoked(jti: str) -> bool:
    _purge_expired_revocations()
    exp = _REVOKED_JTI.get(jti)
    if exp is None:
        return False
    if exp <= datetime.now(timezone.utc):
        _REVOKED_JTI.pop(jti, None)
        return False
    return True


def _save_cli_token(user_id: int, token: str, expires_at: datetime) -> None:
    """CLI convenience: last login JWT so resolve_session() works without Bearer."""
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(
        json.dumps(
            {
                "user_id": user_id,
                "token": token,
                "expires_at": expires_at.isoformat(),
            }
        ),
        encoding="utf-8",
    )


def _load_cli_token() -> Optional[str]:
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    token = str(data.get("token") or "").strip()
    return token or None


def _clear_cli_token() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


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
    del ip_address, user_agent  # reserved for future audit
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
    token = create_access_token(
        user_id=int(user["user_id"]),
        username=str(user["username"]),
        role_code=str(user.get("role_code") or ""),
    )
    claims = decode_access_token(token)
    exp = claims.get("exp")
    if isinstance(exp, (int, float)):
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
    else:
        expires_at = datetime.now(timezone.utc)
    _save_cli_token(int(user["user_id"]), token, expires_at)

    payload = _user_payload(user)
    payload["session_token"] = token  # JWT; field name kept for API compatibility
    return payload


def resolve_session(session_token: str | None = None) -> dict[str, Any]:
    token = (session_token or "").strip() or (_load_cli_token() or "")
    if not token:
        raise AuthenticationError("Invalid or expired session.")

    try:
        claims = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Invalid or expired session.") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired session.") from exc

    jti = str(claims.get("jti") or "")
    if jti and _is_revoked(jti):
        raise AuthenticationError("Invalid or expired session.")

    user_id = claims.get("user_id") or claims.get("sub")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("Invalid or expired session.") from exc

    user = UserDAO().read_by_id(user_id_int)
    if not user or user.get("account_status") != "active":
        raise AuthenticationError("Invalid or expired session.")
    return _user_payload(user)


def logout(session_token: str | None = None) -> None:
    token = (session_token or "").strip()
    if token:
        try:
            claims = decode_access_token(token)
            jti = str(claims.get("jti") or "")
            exp = claims.get("exp")
            if jti and isinstance(exp, (int, float)):
                _revoke_jti(jti, datetime.fromtimestamp(exp, tz=timezone.utc))
        except jwt.PyJWTError:
            pass
        file_token = _load_cli_token()
        if file_token and file_token == token:
            _clear_cli_token()
        return

    # Console logout with no explicit token: revoke CLI JWT if present, clear file.
    file_token = _load_cli_token()
    if file_token:
        try:
            claims = decode_access_token(file_token)
            jti = str(claims.get("jti") or "")
            exp = claims.get("exp")
            if jti and isinstance(exp, (int, float)):
                _revoke_jti(jti, datetime.fromtimestamp(exp, tz=timezone.utc))
        except jwt.PyJWTError:
            pass
    _clear_cli_token()


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
