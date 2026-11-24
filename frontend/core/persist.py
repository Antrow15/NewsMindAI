"""Persist login across browser refresh via cookies."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote, unquote

import streamlit as st
import streamlit.components.v1 as components

try:
    import extra_streamlit_components as stx
except ImportError:  # pragma: no cover
    stx = None

COOKIE_NAME = "newsmind_auth"


def _cookie_manager():
    if stx is None:
        return None
    if "_nm_cm" not in st.session_state:
        st.session_state["_nm_cm"] = stx.CookieManager(key="nm_cookie_manager")
    return st.session_state["_nm_cm"]


def _payload_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        {
            "session_token": payload["session_token"],
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "role_code": payload.get("role_code"),
            "capabilities": list(payload.get("capabilities") or []),
        },
        separators=(",", ":"),
    )


def _write_document_cookie(raw: str | None) -> None:
    """Write/clear cookie on the parent document (component iframe ≠ app origin)."""
    if raw is None:
        js = f"""
        (function () {{
          var d = window.parent && window.parent.document ? window.parent.document : document;
          var name = '{COOKIE_NAME}';
          d.cookie = name + '=; path=/; max-age=0; SameSite=Lax';
          d.cookie = name + '=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax';
          try {{ window.parent.localStorage.removeItem(name); }} catch (e) {{}}
        }})();
        """
    else:
        encoded = quote(raw, safe="")
        js = f"""
        (function () {{
          var d = window.parent && window.parent.document ? window.parent.document : document;
          d.cookie = '{COOKIE_NAME}={encoded}; path=/; max-age=43200; SameSite=Lax';
        }})();
        """
    components.html(f"<script>{js}</script>", height=0, width=0)


def save(payload: dict[str, Any]) -> None:
    """Persist auth payload after login."""
    if not payload.get("session_token"):
        return
    raw = _payload_json(payload)
    _write_document_cookie(raw)
    cm = _cookie_manager()
    if cm is not None:
        try:
            cm.set(COOKIE_NAME, raw, expires_at=datetime.now() + timedelta(hours=12))
        except Exception:
            pass


def clear() -> None:
    """Best-effort cookie wipe (JS + CookieManager)."""
    _write_document_cookie(None)
    cm = _cookie_manager()
    if cm is None:
        return
    try:
        cm.set(COOKIE_NAME, "", expires_at=datetime.now() - timedelta(days=1))
    except Exception:
        pass
    try:
        cm.delete(COOKIE_NAME)
    except Exception:
        pass


def _read_raw(*, allow_context: bool = True) -> str | None:
    # Prefer Streamlit's request cookies (reliable after full page reload).
    # Skip after explicit logout — st.context.cookies is stale until hard refresh.
    if allow_context:
        try:
            ctx = st.context.cookies
            raw = ctx.get(COOKIE_NAME) if ctx is not None else None
            if raw:
                return unquote(str(raw))
        except Exception:
            pass

    cm = _cookie_manager()
    if cm is None:
        return None
    try:
        cookies = cm.get_all()
    except Exception:
        return None
    if cookies is None:
        return None
    raw = cookies.get(COOKIE_NAME)
    if not raw:
        return None
    return unquote(str(raw)) if isinstance(raw, str) else raw


def try_restore() -> str:
    """
    Restore session from cookie if present.

    Returns:
      authenticated | waiting | anonymous
    """
    from core import session

    if session.user() is not None:
        _cookie_manager()
        return "authenticated"

    # Keep CookieManager mounted for set/delete on this run.
    cm = _cookie_manager()

    # Explicit logout: never resurrect the previous JWT from a stale cookie snapshot
    # (st.context.cookies stays frozen until a hard refresh).
    if session.logout_locked():
        return "anonymous"

    raw = _read_raw(allow_context=True)
    if raw is None and cm is not None:
        try:
            cookies = cm.get_all()
        except Exception:
            cookies = {}
        if cookies is None:
            waits = int(st.session_state.get("_nm_cm_waits", 0)) + 1
            st.session_state["_nm_cm_waits"] = waits
            if waits <= 2:
                return "waiting"
        return "anonymous"

    if not raw:
        return "anonymous"

    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, json.JSONDecodeError):
        return "anonymous"

    if not isinstance(data, dict) or not data.get("session_token"):
        return "anonymous"

    # Ignore empty / cleared cookie leftovers from CookieManager.
    tok = str(data.get("session_token") or "").strip()
    if not tok:
        return "anonymous"

    session.sign_in(data, persist=False)
    return "authenticated"
