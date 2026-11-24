"""NewsMind — Streamlit frontend entrypoint.

Run from the project root:   streamlit run frontend/app.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="NewsMind", page_icon="📰", layout="wide")

from core import chrome, config, nav, persist, session, ui  # noqa: E402
from views import login, profile  # noqa: E402

# Always prefer current config so port moves (e.g. 8001) take effect after refresh.
st.session_state["api_url"] = config.API_URL


def main() -> None:
    ui.inject_chrome()

    auth = persist.try_restore()
    if auth == "waiting":
        st.caption("Restoring session…")
        st.stop()

    user = session.user()
    if user is None:
        st.navigation(
            [st.Page(login.render, title="Login", url_path="login")],
            position="hidden",
        ).run()
        return

    if not st.session_state.get("_nm_auth_cookie_ok"):
        payload = session.auth_payload()
        if payload:
            persist.save(payload)
            st.session_state["_nm_auth_cookie_ok"] = True

    menu = nav.build_menu(user)
    if not menu:
        st.error("This account has no desks assigned.")
        chrome.render_sidebar_footer(user)
        return

    # expanded=True removes Streamlit's "View more / View less" — sidebar just scrolls.
    pg = st.navigation(menu, expanded=True)

    # Top-right "Open profile" → Profile page
    if st.session_state.pop("_nm_goto_profile", None):
        try:
            st.switch_page("profile")
        except Exception:
            chrome.render_top_bar(user)
            with st.sidebar:
                chrome.render_sidebar_footer(user)
            profile.render()
            return

    chrome.render_top_bar(user)
    with st.sidebar:
        chrome.render_sidebar_footer(user)
    try:
        pg.run()
    except Exception as exc:
        st.error("This page hit an error. Try another nav item or refresh.")
        st.caption(str(exc))
        with st.expander("Technical details"):
            st.exception(exc)


main()
