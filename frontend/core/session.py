"""Authentication state kept in st.session_state (no API calls here)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import streamlit as st

_TOKEN = "_token"
_USER = "_user"
_FLASH = "_flash"
_REV = "_rev"
# Survives sign_out wipe — blocks cookie auto-restore until the next login.
_LOGOUT_LOCK = "_nm_logout_lock"
# Keys preserved across sign_out (connection + cookie manager widget).
_KEEP_ON_SIGNOUT = frozenset({"api_url", "_nm_cm", _LOGOUT_LOCK})


@dataclass(frozen=True)
class User:
    user_id: int
    username: str
    role_code: str
    capabilities: frozenset[str] = field(default_factory=frozenset)

    def can(self, *caps: str) -> bool:
        """True if the user holds at least one of the given capabilities."""
        return any(c in self.capabilities for c in caps)

    @property
    def role_label(self) -> str:
        return self.role_code.replace("_", " ").title()


def sign_in(payload: dict[str, Any], *, persist: bool = True) -> None:
    st.session_state.pop(_LOGOUT_LOCK, None)
    st.session_state.pop("_nm_auth_cookie_ok", None)
    st.session_state[_TOKEN] = payload["session_token"]
    st.session_state[_USER] = User(
        user_id=int(payload["user_id"]),
        username=str(payload["username"]),
        role_code=str(payload["role_code"]),
        capabilities=frozenset(payload.get("capabilities") or []),
    )
    if persist:
        try:
            from core import persist as auth_persist

            auth_persist.save(payload)
        except Exception:
            pass


def sign_out(reason: str | None = None) -> None:
    """Clear local auth. Cookie restore is blocked until the next sign_in."""
    try:
        from core import persist as auth_persist

        auth_persist.clear()
    except Exception:
        pass
    try:
        st.cache_data.clear()
    except Exception:
        pass
    for key in list(st.session_state.keys()):
        if key not in _KEEP_ON_SIGNOUT:
            del st.session_state[key]
    # st.context.cookies does not update mid-session after JS clears the cookie,
    # so block try_restore from resurrecting the previous account.
    st.session_state[_LOGOUT_LOCK] = True
    if reason:
        st.session_state[_FLASH] = reason


def logout_locked() -> bool:
    """True after an explicit logout until the next successful sign_in."""
    return bool(st.session_state.get(_LOGOUT_LOCK))


def token() -> str | None:
    return st.session_state.get(_TOKEN)


def user() -> User | None:
    return st.session_state.get(_USER) if token() else None


def pop_flash() -> str | None:
    return st.session_state.pop(_FLASH, None)


def revision() -> int:
    """Bumped after every successful write; used to reset table selections."""
    return int(st.session_state.get(_REV, 0))


def bump_revision() -> None:
    st.session_state[_REV] = revision() + 1


def auth_payload() -> dict[str, Any] | None:
    """Current auth dict for cookie persistence."""
    u = user()
    tok = token()
    if u is None or not tok:
        return None
    return {
        "session_token": tok,
        "user_id": u.user_id,
        "username": u.username,
        "role_code": u.role_code,
        "capabilities": sorted(u.capabilities),
    }
