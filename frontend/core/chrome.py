"""App chrome: fixed top bar, round account avatar, sidebar logout."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from core import api, config, session, ui

# Keep the fixed NewsMind bar aligned to the main column as the sidebar resizes.
_TOPBAR_PIN = """
<script>
(function () {
  const doc = window.parent.document;
  const KEY = "__nmTopbarPin";
  if (window.parent[KEY]) return;
  window.parent[KEY] = true;

  function bar() {
    return doc.querySelector('[data-testid="stLayoutWrapper"]:has(.nm-brand)');
  }
  function main() {
    return doc.querySelector('[data-testid="stMain"]');
  }
  function pin() {
    const b = bar();
    const m = main();
    if (!b || !m) return;
    const r = m.getBoundingClientRect();
    b.style.position = "fixed";
    b.style.top = "0px";
    b.style.left = r.left + "px";
    b.style.width = r.width + "px";
    b.style.right = "auto";
    b.style.zIndex = "1000";
    /* Keep out of main-column flex flow / gap */
    b.style.height = "0px";
    b.style.minHeight = "0px";
    b.style.margin = "0";
    b.style.padding = "0";
    b.style.overflow = "visible";
    b.style.border = "none";
    b.style.background = "transparent";
  }
  pin();
  window.parent.addEventListener("resize", pin);
  const obs = new ResizeObserver(pin);
  const m = main();
  if (m) obs.observe(m);
  const side = doc.querySelector('[data-testid="stSidebar"]');
  if (side) obs.observe(side);
  new MutationObserver(pin).observe(doc.body, {
    subtree: true,
    attributes: true,
    attributeFilter: ["data-collapsed", "style", "class"],
  });
})();
</script>
"""


def render_top_bar(user: session.User) -> None:
    """Fixed brand bar; Alerts + round avatar (opens Profile only)."""
    ui.inject_chrome()
    st.markdown(
        '<div class="nm-topbar-marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    left, right = st.columns([4.6, 2.4], gap="small")
    with left:
        st.markdown(
            "<div class='nm-brand'>NewsMind</div>",
            unsafe_allow_html=True,
        )
    with right:
        alerts_col, avatar_col = st.columns([3.2, 1.0], gap="small")
        with alerts_col:
            _notifications_menu(user)
        with avatar_col:
            initial = (user.username or "?").strip()[:1].upper() or "?"
            # No help= — Streamlit renders a floating "Account" chip above the avatar.
            with st.popover(initial):
                st.caption(user.role_label)
                if st.button(
                    "Open profile",
                    type="primary",
                    width="stretch",
                    key="nm_open_profile",
                ):
                    st.session_state["_nm_goto_profile"] = True
                    st.rerun()
    # Pin script only — clearance is CSS padding-top on the main block (no spacer band).
    components.html(_TOPBAR_PIN, height=0, width=0)


def _logout() -> None:
    """End API session, wipe local auth/cache, show login (no cookie resurrect)."""
    try:
        api.request("POST", "/auth/logout")
    except Exception:
        pass
    session.sign_out()
    st.rerun()


def _notifications_menu(user: session.User) -> None:
    unread = 0
    items: list[dict] = []
    if user.can(config.CAP_JOURNALIST):
        try:
            data = api.get(
                "/journalist/notifications",
                unread_only=False,
                limit=12,
                _cache=False,
            )
        except Exception:
            data = None
        if data:
            unread = int(data.get("unread_count") or 0)
            items = data.get("notifications") or []
    label = f"Alerts · {unread}" if unread else "Alerts"
    with st.popover(label):
        if not user.can(config.CAP_JOURNALIST):
            st.caption("No desk alerts for this role.")
            return
        if st.button("Mark all read", key="nm_mark_all", width="stretch"):
            api.post("/journalist/notifications/read-all", success="Alerts cleared.")
            st.rerun()
        if not items:
            st.caption("You're all caught up.")
            return
        for n in items:
            ui.card(
                n.get("title") or "Update",
                status="unread" if n.get("unread") else "read",
                meta=[str(n.get("created_at") or "")],
                body=n.get("body"),
            )
            if n.get("unread") and n.get("key"):
                if st.button("Mark read", key=f"nm_nr_{n['key']}", width="stretch"):
                    api.post(f"/journalist/notifications/{n['key']}/read")
                    st.rerun()


def render_sidebar_footer(_user: session.User | None = None) -> None:
    """Log out control — stays inside the sidebar rail."""
    st.markdown(
        '<div class="nm-logout-anchor" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    if st.button("Log out", width="stretch", key="nm_logout", type="secondary"):
        _logout()
