"""Role-scoped left navigation.

Shared capabilities (e.g. editor also has analytics) must not open other desks.
Admin keeps a flat list of every desk page.
"""

from __future__ import annotations

import streamlit as st

from core import config, session
from views import (
    adaptation,
    admin,
    audience,
    editor,
    journalist_create,
    journalist_dashboard,
    journalist_library,
    manager,
    profile,
    publisher,
)

# Desk nav is role-scoped.
ROLE_NAV_SECTIONS: dict[str, tuple[str, ...]] = {
    "journalist": ("Journalist", "Account"),
    "editor": ("Editor", "Account"),
    "audience_insight_analyst": ("Audience", "Account"),
    "content_adaptation_editor": ("Adaptation", "Account"),
    "publisher": ("Publisher", "Account"),
    "newsroom_manager": ("Manager", "Account"),
}


def _page(fn, title: str, icon: str, path: str) -> st.Page:
    return st.Page(fn, title=title, icon=icon, url_path=path)


def _pick(pages: list[tuple[bool, st.Page]]) -> list[st.Page]:
    return [p for ok, p in pages if ok]


def _journalist_pages(user: session.User, *, labels: str = "short") -> list[st.Page]:
    c = config
    if labels == "flat":
        return _pick(
            [
                (user.can(c.CAP_JOURNALIST), _page(journalist_dashboard.render, "Journalist desk", "📰", "journalist-dashboard")),
                (user.can(c.CAP_JOURNALIST), _page(journalist_create.render, "Create story", "✍️", "create-story")),
                (user.can(c.CAP_JOURNALIST), _page(journalist_library.render, "My content", "📚", "my-content")),
            ]
        )
    return _pick(
        [
            (user.can(c.CAP_JOURNALIST), _page(journalist_dashboard.render, "Dashboard", "📰", "journalist-dashboard")),
            (user.can(c.CAP_JOURNALIST), _page(journalist_create.render, "Create", "✍️", "create-story")),
            (user.can(c.CAP_JOURNALIST), _page(journalist_library.render, "My content", "📚", "my-content")),
        ]
    )


def _audience_pages(user: session.User, *, labels: str = "short") -> list[st.Page]:
    c = config
    if labels == "flat":
        return _pick(
            [
                (user.can(c.CAP_ANALYTICS), _page(audience.render_dashboard, "Audience dashboard", "📊", "audience-dashboard")),
                (user.can(c.CAP_ANALYTICS), _page(audience.render_scores, "Audience scores", "📈", "audience-scores")),
                (user.can(c.CAP_ANALYTICS), _page(audience.render_generate_pitch, "ML pitch", "💡", "generate-pitch")),
                (user.can(c.CAP_ANALYTICS), _page(audience.render_pitches, "Audience pitches", "🗂️", "audience-pitches")),
            ]
        )
    return _pick(
        [
            (user.can(c.CAP_ANALYTICS), _page(audience.render_dashboard, "Dashboard", "📊", "audience-dashboard")),
            (user.can(c.CAP_ANALYTICS), _page(audience.render_scores, "Scores", "📈", "audience-scores")),
            (user.can(c.CAP_ANALYTICS), _page(audience.render_generate_pitch, "ML pitch", "💡", "generate-pitch")),
            (user.can(c.CAP_ANALYTICS), _page(audience.render_pitches, "Pitches", "🗂️", "audience-pitches")),
        ]
    )


def _editor_pages(user: session.User, *, labels: str = "short") -> list[st.Page]:
    c = config
    if labels == "flat":
        return _pick(
            [
                (
                    user.can(c.CAP_PITCH_REVIEW, c.CAP_CONTENT_REVIEW),
                    _page(editor.render_dashboard, "Editor dashboard", "🧭", "editor-dashboard"),
                ),
                (
                    user.can(c.CAP_PITCH_REVIEW, c.CAP_CONTENT_REVIEW),
                    _page(editor.render_queue, "Approval queue", "🧐", "editor-queue"),
                ),
                (user.can(c.CAP_PITCH_REVIEW), _page(editor.render_pitches, "Editor pitches", "📝", "editor-pitches")),
                (user.can(c.CAP_CONTENT_REVIEW), _page(editor.render_content, "Editor content", "📄", "editor-content")),
                (
                    user.can(c.CAP_CONTENT_REVIEW),
                    _page(editor.render_adaptations, "Adapted content", "✅", "editor-adapted"),
                ),
                (user.can(c.CAP_ASSIGN), _page(editor.render_create, "Create & assign", "✍️", "editor-create")),
                (user.can(c.CAP_ASSIGN), _page(editor.render_assign, "Assign work", "🤝", "editor-assign")),
            ]
        )
    return _pick(
        [
            (
                user.can(c.CAP_PITCH_REVIEW, c.CAP_CONTENT_REVIEW),
                _page(editor.render_dashboard, "Dashboard", "🧭", "editor-dashboard"),
            ),
            (
                user.can(c.CAP_PITCH_REVIEW, c.CAP_CONTENT_REVIEW),
                _page(editor.render_queue, "Approval queue", "🧐", "editor-queue"),
            ),
            (user.can(c.CAP_PITCH_REVIEW), _page(editor.render_pitches, "Pitches", "📝", "editor-pitches")),
            (user.can(c.CAP_CONTENT_REVIEW), _page(editor.render_content, "Content", "📄", "editor-content")),
            (
                user.can(c.CAP_CONTENT_REVIEW),
                _page(editor.render_adaptations, "Adapted", "✅", "editor-adapted"),
            ),
            (user.can(c.CAP_ASSIGN), _page(editor.render_create, "Create", "✍️", "editor-create")),
            (user.can(c.CAP_ASSIGN), _page(editor.render_assign, "Assign", "🤝", "editor-assign")),
        ]
    )


def _adaptation_pages(user: session.User, *, labels: str = "short") -> list[st.Page]:
    c = config
    if labels == "flat":
        return _pick(
            [
                (user.can(c.CAP_ADAPT), _page(adaptation.render_dashboard, "Adaptation dashboard", "🧭", "adaptation-dashboard")),
                (user.can(c.CAP_ADAPT), _page(adaptation.render_new, "New adaptation", "✨", "new-adaptation")),
                (user.can(c.CAP_ADAPT), _page(adaptation.render_review, "Adaptation drafts", "🔁", "review-drafts")),
            ]
        )
    return _pick(
        [
            (user.can(c.CAP_ADAPT), _page(adaptation.render_dashboard, "Dashboard", "🧭", "adaptation-dashboard")),
            (user.can(c.CAP_ADAPT), _page(adaptation.render_new, "New adaptation", "✨", "new-adaptation")),
            (user.can(c.CAP_ADAPT), _page(adaptation.render_review, "My drafts", "🔁", "review-drafts")),
        ]
    )


def _publisher_pages(user: session.User, *, labels: str = "short") -> list[st.Page]:
    c = config
    if labels == "flat":
        return _pick(
            [
                (user.can(c.CAP_PUBLISH), _page(publisher.render_dashboard, "Publisher dashboard", "📉", "publisher-dashboard")),
                (user.can(c.CAP_PUBLISH), _page(publisher.render_queue, "Publication queue", "🚀", "publication-queue")),
            ]
        )
    return _pick(
        [
            (user.can(c.CAP_PUBLISH), _page(publisher.render_dashboard, "Dashboard", "📉", "publisher-dashboard")),
            (user.can(c.CAP_PUBLISH), _page(publisher.render_queue, "Publication queue", "🚀", "publication-queue")),
        ]
    )


def _manager_pages(user: session.User, *, labels: str = "short") -> list[st.Page]:
    c = config
    if labels == "flat":
        pages = _pick(
            [
                (
                    user.can(c.CAP_PITCH_REVIEW, c.CAP_ANALYTICS),
                    _page(manager.render_dashboard, "Manager overview", "🧭", "manager-dashboard"),
                ),
                (
                    user.can(c.CAP_PITCH_REVIEW, c.CAP_CONTENT_REVIEW, c.CAP_ASSIGN),
                    _page(manager.render_review, "Manager review", "📥", "manager-review"),
                ),
                (user.can(c.CAP_ANALYTICS), _page(manager.render_ops, "Operations", "⚙️", "manager-ops")),
            ]
        )
    else:
        pages = _pick(
            [
                (
                    user.can(c.CAP_PITCH_REVIEW, c.CAP_ANALYTICS),
                    _page(manager.render_dashboard, "Dashboard", "🧭", "manager-dashboard"),
                ),
                (
                    user.can(c.CAP_PITCH_REVIEW, c.CAP_CONTENT_REVIEW, c.CAP_ASSIGN),
                    _page(manager.render_review, "Review", "📥", "manager-review"),
                ),
                (user.can(c.CAP_ANALYTICS), _page(manager.render_ops, "Operations", "⚙️", "manager-ops")),
            ]
        )
    if user.can(c.CAP_MANAGE_USERS) and labels != "flat":
        pages = pages + [_page(admin.render_users, "Users", "👥", "users")]
    return pages


def _admin_pages(user: session.User) -> list[st.Page]:
    c = config
    return _pick(
        [
            (user.can(c.CAP_ADMIN), _page(admin.render_dashboard, "Dashboard", "🛡️", "admin-dashboard")),
            (user.can(c.CAP_ADMIN, c.CAP_PIPELINE), _page(admin.render_pipeline, "Pipeline", "🧪", "pipeline")),
            (user.can(c.CAP_MANAGE_USERS), _page(admin.render_users, "Users", "👥", "users")),
            (user.can(c.CAP_ADMIN), _page(admin.render_categories, "Categories", "🏷️", "categories")),
        ]
    )


def _account_pages() -> list[st.Page]:
    return [_page(profile.render, "Profile", "👤", "profile")]


def _admin_flat_menu(user: session.User) -> list[st.Page]:
    """Administrator: one flat list of every desk they can open."""
    return (
        _admin_pages(user)
        + _journalist_pages(user, labels="flat")
        + _audience_pages(user, labels="flat")
        + _editor_pages(user, labels="flat")
        + _adaptation_pages(user, labels="flat")
        + _publisher_pages(user, labels="flat")
        + _manager_pages(user, labels="flat")
        + _account_pages()
    )


def _section_pages(section: str, user: session.User) -> list[st.Page]:
    if section == "Journalist":
        return _journalist_pages(user)
    if section == "Audience":
        return _audience_pages(user)
    if section == "Editor":
        return _editor_pages(user)
    if section == "Adaptation":
        return _adaptation_pages(user)
    if section == "Publisher":
        return _publisher_pages(user)
    if section == "Manager":
        return _manager_pages(user)
    if section == "Account":
        return _account_pages()
    return []


def nav_section_titles(role_code: str, *, is_admin: bool) -> list[str]:
    """Expected sidebar section titles (for tests / debugging)."""
    if is_admin:
        return ["flat"]
    return list(ROLE_NAV_SECTIONS.get(role_code, ("Account",)))


def build_menu(user: session.User) -> dict[str, list[st.Page]] | list[st.Page]:
    if user.can(config.CAP_ADMIN) or user.role_code == "administrator":
        return _admin_flat_menu(user)
    sections = ROLE_NAV_SECTIONS.get(user.role_code, ("Account",))
    menu: dict[str, list[st.Page]] = {}
    for name in sections:
        pages = _section_pages(name, user)
        if pages:
            menu[name] = pages
    if "Account" not in menu:
        menu["Account"] = _account_pages()
    return menu


def menu_section_names(user: session.User) -> list[str]:
    """Sidebar section labels for the user (or ['flat'] for admin)."""
    menu = build_menu(user)
    if isinstance(menu, list):
        return ["flat"]
    return list(menu.keys())


def menu_page_counts(user: session.User) -> dict[str, int] | int:
    """Page counts per section (or total count for admin flat nav)."""
    menu = build_menu(user)
    if isinstance(menu, list):
        return len(menu)
    return {sec: len(pages) for sec, pages in menu.items()}
