"""Role-scoped sidebar: desks must not leak across shared capabilities."""

from __future__ import annotations

from core import nav
from core.session import User


def _user(role: str, caps: list[str]) -> User:
    return User(1, role, role, frozenset(caps))


def test_nav_sections_by_role():
    expected = {
        "journalist": ["Journalist", "Account"],
        "editor": ["Editor", "Account"],
        "audience_insight_analyst": ["Audience", "Account"],
        "content_adaptation_editor": ["Adaptation", "Account"],
        "publisher": ["Publisher", "Account"],
        "newsroom_manager": ["Manager", "Account"],
        "administrator": ["flat"],
        "unknown_role": ["Account"],
    }
    for role, sections in expected.items():
        is_admin = role == "administrator"
        assert nav.nav_section_titles(role, is_admin=is_admin) == sections


def test_editor_menu_excludes_other_desks():
    u = _user("editor", ["pitch_review", "content_review", "assign", "analytics"])
    assert nav.menu_section_names(u) == ["Editor", "Account"]
    counts = nav.menu_page_counts(u)
    # Dashboard, Approval queue, Pitches, Content, Adapted, Create, Assign
    assert counts == {"Editor": 7, "Account": 1}


def test_manager_menu_is_manager_only():
    u = _user(
        "newsroom_manager",
        [
            "pitch_review",
            "content_review",
            "assign",
            "adapt",
            "publish",
            "analytics",
            "manage_users",
        ],
    )
    assert nav.menu_section_names(u) == ["Manager", "Account"]
    counts = nav.menu_page_counts(u)
    assert counts["Manager"] == 4  # Dashboard, Review, Operations, Users
    assert counts["Account"] == 1


def test_analyst_menu_is_audience_only():
    u = _user("audience_insight_analyst", ["analytics", "clean", "ingest"])
    assert nav.menu_section_names(u) == ["Audience", "Account"]
    assert nav.menu_page_counts(u) == {"Audience": 4, "Account": 1}


def test_all_demo_role_menus():
    cases = {
        "journalist": (["journalist_tools"], ["Journalist", "Account"], {"Journalist": 3, "Account": 1}),
        "editor": (
            ["pitch_review", "content_review", "assign", "analytics"],
            ["Editor", "Account"],
            {"Editor": 7, "Account": 1},
        ),
        "audience_insight_analyst": (
            ["analytics", "clean", "ingest"],
            ["Audience", "Account"],
            {"Audience": 4, "Account": 1},
        ),
        "content_adaptation_editor": (
            ["adapt"],
            ["Adaptation", "Account"],
            {"Adaptation": 3, "Account": 1},
        ),
        "publisher": (
            ["publish"],
            ["Publisher", "Account"],
            {"Publisher": 2, "Account": 1},
        ),
        "newsroom_manager": (
            [
                "pitch_review",
                "content_review",
                "assign",
                "adapt",
                "publish",
                "analytics",
                "manage_users",
            ],
            ["Manager", "Account"],
            {"Manager": 4, "Account": 1},
        ),
    }
    for role, (caps, sections, counts) in cases.items():
        u = _user(role, caps)
        assert nav.menu_section_names(u) == sections, role
        assert nav.menu_page_counts(u) == counts, role


def test_admin_is_flat():
    u = _user(
        "administrator",
        [
            "admin",
            "pipeline",
            "manage_users",
            "pitch_review",
            "content_review",
            "assign",
            "adapt",
            "publish",
            "analytics",
            "journalist_tools",
        ],
    )
    assert nav.menu_section_names(u) == ["flat"]
    assert isinstance(nav.menu_page_counts(u), int)
    assert nav.menu_page_counts(u) >= 20
