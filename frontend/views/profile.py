"""Profile page — employee details + editable fields + password."""

from __future__ import annotations

import re

import streamlit as st

from core import api, session, ui

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def render() -> None:
    user = session.user()
    if user is None:
        st.info("Sign in to manage your profile.")
        return

    ui.header("Profile", "Your employee record and account settings.")

    # Connectivity check
    me = api.get("/auth/me", _cache=False)
    if not me:
        ui.card(
            "Could not load profile",
            body="Check that the API is running and your session is valid, then refresh.",
        )
        return

    name = f"{me.get('first_name') or ''} {me.get('last_name') or ''}".strip() or me.get("username")
    ui.card(
        name or "Employee",
        status=me.get("employment_status") or me.get("account_status"),
        meta=[
            f"Username · {me.get('username')}",
            f"Role · {me.get('role_name') or me.get('role_code')}",
            f"Code · {me.get('employee_code') or '—'}",
        ],
    )

    ui.section("Employee details")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Department**  \n{me.get('department') or '—'}")
        st.markdown(f"**Designation**  \n{me.get('designation') or '—'}")
        st.markdown(f"**Employment status**  \n{me.get('employment_status') or '—'}")
    with c2:
        st.markdown(f"**Account status**  \n{me.get('account_status') or '—'}")
        st.markdown(f"**Joined**  \n{me.get('joining_date') or '—'}")
        st.markdown(f"**Email**  \n{me.get('email') or '—'}")

    ui.section(
        "Update contact details",
        "You can edit name, email, mobile, and location. Department and role are managed by admin.",
    )
    with st.form("profile_edit"):
        a, b = st.columns(2)
        first = a.text_input("First name", value=me.get("first_name") or "", max_chars=128)
        last = b.text_input("Last name", value=me.get("last_name") or "", max_chars=128)
        email = a.text_input("Email", value=me.get("email") or "", max_chars=255)
        mobile = b.text_input("Mobile", value=me.get("mobile_number") or "", max_chars=32)
        location = st.text_input("Location", value=me.get("location") or "", max_chars=128)
        submitted = st.form_submit_button("Save changes", type="primary")

    if submitted:
        errors = []
        if not first.strip():
            errors.append("First name is required.")
        if not last.strip():
            errors.append("Last name is required.")
        if not email.strip() or not _EMAIL_RE.match(email.strip()):
            errors.append("Enter a valid email address.")
        if mobile.strip() and not re.fullmatch(r"[0-9+\-\s()]{7,32}", mobile.strip()):
            errors.append("Mobile number looks invalid.")
        if errors:
            for e in errors:
                st.error(e)
        else:
            res = api.put(
                "/auth/me",
                {
                    "first_name": first.strip(),
                    "last_name": last.strip(),
                    "email": email.strip(),
                    "mobile_number": mobile.strip() or None,
                    "location": location.strip() or None,
                },
                success="Profile updated.",
            )
            if res:
                st.rerun()

    ui.section("Change password")
    with st.form("pw_profile", clear_on_submit=True):
        current = st.text_input("Current password", type="password")
        new = st.text_input(
            "New password",
            type="password",
            help="Min 10 characters with upper, lower, digit and special character.",
        )
        confirm = st.text_input("Confirm new password", type="password")
        if st.form_submit_button("Update password", type="primary"):
            if not current or not new:
                st.error("Enter current and new passwords.")
            elif new != confirm:
                st.error("New passwords do not match.")
            elif len(new) < 10:
                st.error("New password must be at least 10 characters.")
            else:
                api.post(
                    "/auth/change-password",
                    {"current_password": current, "new_password": new},
                    success="Password changed.",
                )


def render_inline() -> None:
    """Back-compat stub."""
    render()
