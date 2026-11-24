"""Render every view against a fake backend (no server / DB needed).

Run from the frontend folder:  pytest test -q
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]

CAPS = {
    "journalist": ["journalist_tools"],
    "editor": ["pitch_review", "content_review", "assign", "analytics"],
    "publisher": ["publish"],
    "manager": ["pitch_review", "content_review", "assign", "adapt", "publish",
                "analytics", "manage_users"],
    "admin": ["admin", "pipeline", "manage_users", "pitch_review", "content_review",
              "assign", "adapt", "publish", "analytics", "journalist_tools"],
}
CONTENT = [{"content_id": 1, "title": "Flood hits city", "status": "submitted",
            "content_kind": "news", "summary": "City flooding"}]
DRAFT = {"id": 7, "platform": "WEBSITE", "version_number": 1, "adapted_title": "T",
         "adapted_content": "C", "model_version": "m", "status": "pending",
         "generation_parameters": {}, "validation_flags": {}}

GET_ROUTES = {
    "/journalist/dashboard": {
        "actor": "j",
        "metrics": {"drafts": 1, "submitted": 0, "rework": 0, "approved": 0,
                    "published": 0, "open_assignments": 1, "unread_notifications": 1},
        "assignments": [{"key": 1, "title": "Assigned brief", "status": "draft",
                         "assigned_by": "Ed Editor", "deadline": "2026-12-01T17:00:00",
                         "summary": "Write it", "note": "", "brief_from_pitch": "Pitch"}],
        "upcoming_deadlines": [],
        "notifications": [{"key": 9, "title": "New assignment", "body": "Due soon",
                           "unread": True, "created_at": "2026-11-24"}],
    },
    "/journalist/assignments": {"assignments": []},
    "/journalist/notifications": {"notifications": [], "unread_count": 0},
    "/journalist/content/1/evidence": {"items": [{"title": "Doc", "evidence_type": "document"}]},
    "/journalist/content/1": {"actor": "a", "content": {"title": "Flood", "status": "draft",
                                                       "content_body": "x" * 50}},
    "/journalist/content": {"actor": "a", "items": CONTENT},
    "/aia/story-pitches/top": {"pitches": []},
    "/aia/story-pitches": {"pitches": [{"title": "P", "status": "submitted", "priority": "high",
                                       "summary": "s", "source_type": "AI_GENERATED"}]},
    "/aia/performance": {"publication_by_status": {"published": 2}, "content_by_status": {"draft": 3},
                         "pitch_outcomes": [], "pitches_by_source": {}, "recent_published": [],
                         "insights": ["All good"]},
    "/editor/queue": {"tasks": [{"title": "Task", "task_type": "pitch", "status": "submitted",
                                 "urgency": "high", "summary": "s"}],
                      "pitch_count": 1, "content_count": 1},
    "/editor/pitches": {"pitches": [{"story_pitch_id": 3, "title": "P", "status": "approved",
                                    "summary": "s", "priority": "high"}]},
    "/editor/content": {"items": CONTENT},
    "/cae/adaptations/5": {"id": 5, "original_title": "O", "original_content": "OC",
                           "status": "open", "drafts": [DRAFT]},
    "/publisher/articles": {"articles": [{"content_id": 1, "title": "A"}]},
    "/publisher/templates": {"templates": [{"code": "web_standard", "name": "Web"}]},
    "/publisher/articles/1/preview": {"content_id": 1, "template": {"name": "Web"},
                                      "preview_html": "<p>hi</p>", "publication_status": "ready"},
    "/publisher/analytics": {"approved_content": 1, "publications_by_status": {"ready": 1},
                             "published": 0, "scheduled": 0, "ready": 1, "approved": 1},
    "/manager/overview": {"submitted_pitches": 1, "submitted_content": 2, "approved_content": 3,
                          "publication": {"ready": 1}},
    "/manager/bottlenecks": {"content_stages": [{"stage": "submitted"}], "pitch_stages": [],
                             "publication_stages": [], "adaptation_stages": [],
                             "hotspots": [{"stage": "submitted", "item_count": 2}]},
    "/manager/workload": {"journalists": [{"name": "J", "open": 2}], "total_open_items": 2},
    "/manager/deadline-risk": {"thresholds_hours": {}, "content_at_risk": [], "pitches_at_risk": [],
                               "at_risk_count": 0},
    "/manager/resources": {"desks": [{"desk": "x"}], "utilization": {}, "overloaded": [],
                           "underutilized": []},
    "/manager/analytics": {"pipeline": {"a": 1}, "ops": {}, "bottleneck_hotspots": [],
                           "totals": {"content": 5}},
    "/manager/queue": {"tasks": [{"title": "T"}], "pitch_count": 1, "content_count": 1},
    "/manager/pitches": {"pitches": [{"story_pitch_id": 3, "title": "P", "status": "approved",
                                     "summary": "s"}]},
    "/manager/content": {"items": CONTENT},
    "/admin/raw-ingest": {"counts": {"pending": 2}, "items": [{"headline": "Row", "status": "pending"}]},
    "/auth/me": {
        "user_id": 1, "username": "journalist", "role_code": "journalist", "role_name": "Journalist",
        "account_status": "active", "employee_code": "J001", "first_name": "Jordan", "last_name": "Journalist",
        "email": "jordan@newsroom.local", "mobile_number": "", "department": "News", "designation": "Reporter",
        "location": "City", "employment_status": "active", "joining_date": "2024-01-01",
    },
}


def fake_request(self, method, url, json=None, params=None, headers=None, **_):
    path = url.split("://", 1)[1].split("/", 1)[1]
    path = "/" + path
    req = httpx.Request(method, url)
    if path == "/auth/login":
        user = json["username"]
        if json["password"] != "pw" or user not in CAPS:
            return httpx.Response(401, json={"detail": "Invalid credentials"}, request=req)
        return httpx.Response(200, request=req, json={
            "session_token": "t", "user_id": 1, "username": user, "role_code": user,
            "capabilities": CAPS[user]})
    if method == "GET" and path in GET_ROUTES:
        return httpx.Response(200, json=GET_ROUTES[path], request=req)
    if method != "GET":
        return httpx.Response(200, json={"message": "ok", "result": {}, "content_id": 99,
                                         "ok": True, "matches": [], "errors": [],
                                         "suggestions": [{"user_id": 2, "full_name": "Jordan",
                                                          "primary_specialization": "city",
                                                          "score": 0.9, "availability_status": "available",
                                                          "open_workload": 1, "reason": "match"}]},
                              request=req)
    return httpx.Response(404, json={"detail": f"no route {path}"}, request=req)


@pytest.fixture(autouse=True)
def _backend():
    with patch.object(httpx.Client, "request", fake_request):
        yield


def _view_script(module: str, role: str = "admin", render: str = "render") -> str:
    return f"""
import sys
sys.path.insert(0, {str(ROOT)!r})
import streamlit as st
from core import session
st.session_state["api_url"] = "http://fake"
session.sign_in({{"session_token": "t", "user_id": 1, "username": "{role}",
                 "role_code": "{role}", "capabilities": {CAPS[role]!r}}})
from views import {module}
{module}.{render}()
"""


@pytest.mark.parametrize("module,render", [
    ("journalist_dashboard", "render"),
    ("journalist_create", "render"),
    ("journalist_library", "render"),
    ("audience", "render_dashboard"),
    ("audience", "render_generate_pitch"),
    ("audience", "render_pitches"),
    ("audience", "render_scores"),
    ("editor", "render_dashboard"),
    ("editor", "render_pitches"),
    ("editor", "render_content"),
    ("editor", "render_assign"),
    ("publisher", "render_dashboard"),
    ("publisher", "render_queue"),
    ("manager", "render_dashboard"),
    ("manager", "render_review"),
    ("manager", "render_ops"),
    ("admin", "render_dashboard"),
    ("admin", "render_pipeline"),
    ("admin", "render_users"),
    ("admin", "render_categories"),
    ("profile", "render"),
    ("account", "render"),
])
def test_view_renders(module, render):
    at = AppTest.from_string(_view_script(module, render=render), default_timeout=40).run()
    assert not at.exception, at.exception
    assert not at.error, [e.value for e in at.error]


def test_adaptation_review_renders_drafts():
    at = AppTest.from_string(
        _view_script("adaptation", render="render_review"), default_timeout=30
    ).run()
    assert not at.exception
    at.number_input(key="adapt_manual").set_value(5).run()
    assert not at.exception, at.exception


def test_adaptation_new_renders():
    at = AppTest.from_string(
        _view_script("adaptation", render="render_new"), default_timeout=30
    ).run()
    assert not at.exception, at.exception


@pytest.mark.parametrize("role,landing", [
    ("journalist", "Dashboard"),
    ("publisher", "Dashboard"),
    ("manager", "Dashboard"),
])
def test_login_lands_on_first_allowed_page(role, landing):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40).run()
    at.text_input[0].set_value(role)
    at.text_input[1].set_value("pw")
    at.button[0].click().run()
    assert not at.exception, at.exception
    page_text = " ".join(s.value for s in at.markdown) + " ".join(t.value for t in at.title)
    assert landing in page_text
    assert any(b.label == "Log out" for b in at.sidebar.button)


def test_journalist_has_no_pipeline_nav():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40).run()
    at.text_input[0].set_value("journalist")
    at.text_input[1].set_value("pw")
    at.button[0].click().run()
    assert not at.exception, at.exception
    page_text = " ".join(s.value for s in at.markdown) + " ".join(t.value for t in at.title)
    assert "Dashboard" in page_text
    nav = str(at.sidebar)
    assert "Pipeline" not in nav
    assert any(b.label == "Log out" for b in at.sidebar.button)


def test_bad_login_shows_error():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    at.text_input[0].set_value("nobody")
    at.text_input[1].set_value("bad")
    at.button[0].click().run()
    assert any("Invalid credentials" in e.value for e in at.error)
