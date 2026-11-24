from __future__ import annotations

import streamlit as st

from core import api, session


def render() -> None:
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.title("📰 NewsMind")
        st.caption("Newsroom workflow console")

        if flash := session.pop_flash():
            st.warning(flash)

        with st.form("login"):
            username = st.text_input("Username", max_chars=64)
            password = st.text_input("Password", type="password", max_chars=128)
            submitted = st.form_submit_button("Log in", type="primary", width="stretch")

        with st.expander("Connection"):
            api_url = st.text_input("API URL", key="api_url")
            if st.button("Test connection", key="login_ping"):
                url = (api_url or st.session_state.get("api_url") or "").rstrip("/")
                if not url.startswith(("http://", "https://")):
                    st.error("API URL must start with http:// or https://")
                else:
                    try:
                        # Any authenticated-or-not probe: login with empty fails validation → server is up
                        api.request("POST", "/auth/login", json={"username": "_", "password": "_"})
                        st.success("API reachable (got a response).")
                    except api.ApiError as exc:
                        if exc.status in {401, 422, 400}:
                            st.success(f"API reachable at {url}")
                        elif exc.status == 0:
                            st.error(exc.detail)
                        else:
                            st.warning(f"API responded with HTTP {exc.status}: {exc.detail}")

        if submitted:
            if not (username or "").strip():
                st.error("Username is required.")
                return
            if not password:
                st.error("Password is required.")
                return
            url = str(st.session_state.get("api_url") or "").rstrip("/")
            if url and not url.startswith(("http://", "https://")):
                st.error("Fix the API URL under Connection before logging in.")
                return
            payload = api.post(
                "/auth/login",
                {"username": username.strip(), "password": password},
            )
            if payload:
                try:
                    st.cache_data.clear()
                except Exception:
                    pass
                session.sign_in(payload)
                st.rerun()
