"""End-to-end cross-desk workflow: AIA → Editor assign → Journalist → Editor → Publisher (+ Manager/Admin/CAE/Profile)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from config.constants import DEMO_PASSWORDS
from modules.authentication import logout

SAMPLE = (
    "The city council approved a new housing plan covering 10 wards. "
    "Officials said funding will begin next quarter after a public review. "
    "Residents welcomed the announcement during a town hall meeting. "
    "However, some activists asked for clearer timelines and budget figures. "
    "The mayor confirmed that construction may start once permits are issued."
)

EVIDENCE = [
    {
        "title": "Workflow source notes",
        "evidence_type": "document",
        "source_url": "https://example.com/workflow-source",
        "text": "Source attached for cross-role workflow article",
    }
]


@pytest.fixture
def client(db_ready):
    logout()
    with TestClient(app) as test_client:
        yield test_client
    logout()


def _login(client: TestClient, username: str) -> tuple[str, dict]:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": DEMO_PASSWORDS[username]},
    )
    assert response.status_code == 200, f"{username}: {response.text}"
    body = response.json()
    token = body["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    return token, {**body, **me.json(), "_headers": headers}


def _h(user: dict) -> dict:
    return user["_headers"]


def test_full_newsroom_workflow(client):
    """AIA pitch → editor assign → journalist notified → submit → approve → publish."""
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    _, analyst = _login(client, "analyst")
    _, editor = _login(client, "editor")
    _, journalist = _login(client, "journalist")
    _, publisher = _login(client, "publisher")
    _, manager = _login(client, "manager")
    _, adapter = _login(client, "adapter")
    _, admin = _login(client, "admin")

    journalist_user_id = int(journalist["user_id"])

    # ── 1. AIA generates a pitch editors can act on ──
    pitch = client.post(
        "/aia/generate-story-pitch",
        headers=_h(analyst),
        json={
            "title": f"Workflow civic housing brief {stamp}",
            "summary": "Audience interest rising around local housing approvals this week.",
            "category": "City",
            "trend_score": 88,
            "audience_interest_score": 84,
            "coverage_gap_score": 76,
        },
    )
    assert pitch.status_code == 200, pitch.text
    pitch_id = int(pitch.json()["story_pitch_id"])
    assert pitch_id > 0

    listed = client.get("/editor/pitches", headers=_h(editor), params={"status": "submitted"})
    assert listed.status_code == 200, listed.text
    pitches = listed.json().get("pitches") or []
    assert any(int(p.get("story_pitch_id") or 0) == pitch_id for p in pitches)

    # ── 2. Editor suggests match + assigns pitch → creates content + notification ──
    suggest = client.post(
        "/editor/assign/suggest",
        headers=_h(editor),
        json={"topic": "City housing", "title": f"Workflow civic housing brief {stamp}"},
    )
    assert suggest.status_code == 200, suggest.text
    assert "suggestions" in suggest.json()

    due = (datetime.utcnow() + timedelta(days=3)).isoformat()
    assigned = client.post(
        f"/editor/pitches/{pitch_id}/assign",
        headers=_h(editor),
        json={
            "assignee_user_id": journalist_user_id,
            "note": "Cover the housing vote angle",
            "due_at": due,
            "auto_approve": True,
        },
    )
    assert assigned.status_code == 200, assigned.text
    assign_body = assigned.json()
    content_id = int(
        assign_body.get("content_id")
        or (assign_body.get("content") or {}).get("content_id")
        or 0
    )
    assert content_id > 0, assign_body

    # ── 3. Journalist sees assignment + notification on dashboard ──
    dash = client.get("/journalist/dashboard", headers=_h(journalist))
    assert dash.status_code == 200, dash.text
    dash_body = dash.json()
    assert "metrics" in dash_body
    assignments = dash_body.get("assignments") or []
    assert any(
        int(a.get("key") or a.get("content_id") or 0) == content_id for a in assignments
    ), assignments

    notifs = client.get(
        "/journalist/notifications",
        headers=_h(journalist),
        params={"unread_only": False, "limit": 20},
    )
    assert notifs.status_code == 200, notifs.text
    notif_body = notifs.json()
    assert int(notif_body.get("unread_count") or 0) >= 1
    notes = notif_body.get("notifications") or []
    assert notes, "Expected at least one notification after assign"

    # ── 4. Journalist validates tools + submits the assigned draft ──
    item = client.get(f"/journalist/content/{content_id}", headers=_h(journalist))
    assert item.status_code == 200, item.text

    validate = client.post(
        "/journalist/validate",
        headers=_h(journalist),
        json={
            "title": f"Housing plan advances after council vote {stamp}",
            "text": SAMPLE,
            "status": "submitted",
        },
    )
    assert validate.status_code == 200, validate.text
    assert validate.json()["ok"] is True

    related = client.post(
        "/journalist/related-content",
        headers=_h(journalist),
        json={
            "title": f"Housing plan advances after council vote {stamp}",
            "text": SAMPLE,
            "limit": 5,
        },
    )
    assert related.status_code == 200, related.text

    submitted = client.put(
        f"/journalist/content/{content_id}/status",
        headers=_h(journalist),
        json={"status": "submitted"},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "submitted"

    # ── 5. Editor queue sees it; approve for publishing ──
    queue = client.get("/editor/queue", headers=_h(editor))
    assert queue.status_code == 200, queue.text
    assert int(queue.json().get("content_count") or 0) >= 1

    approved = client.put(
        f"/editor/content/{content_id}/approve",
        headers=_h(editor),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    # ── 6. Manager overview / ops still healthy and can see approved content path ──
    overview = client.get("/manager/overview", headers=_h(manager))
    assert overview.status_code == 200, overview.text
    assert "submitted_pitches" in overview.json()

    workload = client.get("/manager/workload", headers=_h(manager))
    assert workload.status_code == 200, workload.text

    # ── 7. Publisher templates + publishes ──
    articles = client.get("/publisher/articles", headers=_h(publisher))
    assert articles.status_code == 200, articles.text
    assert any(
        int(a.get("content_id") or 0) == content_id
        for a in (articles.json().get("articles") or [])
    )

    templated = client.put(
        f"/publisher/articles/{content_id}/template",
        headers=_h(publisher),
        json={"template_code": "web_standard"},
    )
    assert templated.status_code == 200, templated.text

    published = client.post(
        f"/publisher/articles/{content_id}/publish",
        headers=_h(publisher),
    )
    assert published.status_code == 200, published.text
    assert published.json()["publication"]["status"] == "published"

    # ── 8. AIA performance loop can read published signal ──
    perf = client.get("/aia/performance", headers=_h(analyst))
    assert perf.status_code == 200, perf.text

    # ── 9. CAE adaptation (skip if model missing) ──
    model_path = (
        Path(__file__).resolve().parents[1] / "artifacts" / "models" / "cae" / "model.joblib"
    )
    if model_path.exists():
        adapted = client.post(
            "/cae/adaptations",
            headers=_h(adapter),
            json={
                "original_title": f"Housing plan advances after council vote {stamp}",
                "original_content": SAMPLE,
                "target_platforms": ["SOCIAL_MEDIA", "WEBSITE"],
            },
        )
        assert adapted.status_code == 201, adapted.text
        drafts = adapted.json().get("drafts") or []
        assert drafts
        draft_id = drafts[0]["id"]
        denied = client.post(
            f"/cae/adaptation-drafts/{draft_id}/approve",
            headers=_h(adapter),
            json={"remarks": "Ship social cut"},
        )
        assert denied.status_code in (401, 403), denied.text
        ok = client.post(
            f"/cae/adaptation-drafts/{draft_id}/approve",
            headers=_h(editor),
            json={"remarks": "Ship social cut"},
        )
        assert ok.status_code == 200, ok.text

    # ── 10. Admin + profile endpoints ──
    lookup = client.get("/admin/users/journalist", headers=_h(admin))
    assert lookup.status_code == 200, lookup.text

    raw = client.get("/admin/raw-ingest", headers=_h(admin), params={"limit": 5})
    assert raw.status_code == 200, raw.text

    csvs = client.get("/admin/csv-files", headers=_h(admin))
    assert csvs.status_code == 200, csvs.text

    profile = client.get("/auth/me", headers=_h(journalist))
    assert profile.status_code == 200, profile.text
    assert profile.json().get("username") == "journalist"

    # ── 11. RBAC fences still hold ──
    denied = client.get("/admin/users/journalist", headers=_h(journalist))
    assert denied.status_code == 403

    denied_pub = client.get("/publisher/articles", headers=_h(journalist))
    assert denied_pub.status_code == 403

    denied_aia = client.post(
        "/aia/analyze-engagement",
        headers=_h(journalist),
        json={"views": 10, "likes": 1, "shares": 0, "comments": 0},
    )
    assert denied_aia.status_code == 403
