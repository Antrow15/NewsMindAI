"""Integration: CAE, publisher, editor, manager APIs."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from api.main import app
from config.constants import DEMO_PASSWORDS
from modules.authentication import logout
from services.content.content_service import ContentService


SAMPLE_ARTICLE = (
    "The city council approved a new housing plan covering 10 wards. "
    "Officials said funding will begin next quarter after a public review. "
    "Residents welcomed the announcement during a town hall meeting. "
    "However, some activists asked for clearer timelines and budget figures. "
    "The mayor confirmed that construction may start once permits are issued."
)

_DEMO_EVIDENCE = [
    {
        "title": "Source notes for article",
        "evidence_type": "document",
        "source_url": "https://example.com/source",
        "text": "Attached source for this article only",
    }
]


@pytest.fixture
def client(db_ready):
    logout()
    with TestClient(app) as test_client:
        yield test_client
    logout()


def _login(client: TestClient, username: str) -> str:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": DEMO_PASSWORDS[username]},
    )
    assert response.status_code == 200, response.text
    return response.json()["session_token"]


def test_openapi_includes_new_desks(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/cae/adaptations" in paths
    assert "/publisher/articles" in paths
    assert "/editor/pitches" in paths
    assert "/editor/queue" in paths
    assert "/editor/queue/score" in paths
    assert "/editor/event-groups" not in paths
    assert "/editor/pitches/duplicates" in paths
    assert "/editor/assign/suggest" in paths
    assert "/editor/content/{content_id}/rework" in paths
    assert "/manager/overview" in paths
    assert "/manager/queue" in paths
    assert "/manager/bottlenecks" in paths
    assert "/manager/analytics" in paths
    assert "/manager/workload" in paths
    assert "/manager/deadline-risk" in paths
    assert "/manager/resources" in paths
    assert "/manager/event-groups" not in paths
    assert "/aia/performance" in paths
    assert "/aia/predict-priority" not in paths
    assert "/journalist/suggest-category" not in paths
    assert "/journalist/related-content" in paths
    assert "/journalist/dashboard" in paths
    assert "/journalist/assignments" in paths
    assert "/journalist/notifications" in paths
    assert "/editor/pitches/{story_pitch_id}/assign" in paths
    assert "/manager/pitches/{story_pitch_id}/assign" in paths
    assert "/admin/users" in paths
    assert "/admin/ingest" in paths


def test_cae_create_approve_and_versions(client):
    from pathlib import Path

    model_path = (
        Path(__file__).resolve().parents[1] / "artifacts" / "models" / "cae" / "model.joblib"
    )
    if not model_path.exists():
        pytest.skip("CAE model not trained yet (artifacts/models/cae empty)")

    token = _login(client, "adapter")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/cae/adaptations",
        headers=headers,
        json={
            "original_title": "City housing plan advances",
            "original_content": SAMPLE_ARTICLE,
            "target_platforms": ["SOCIAL_MEDIA", "WEBSITE"],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "COMPLETED"
    assert len(body["drafts"]) == 2
    draft_id = body["drafts"][0]["id"]

    # Adapter cannot approve — editorial sign-off only.
    denied = client.post(
        f"/cae/adaptation-drafts/{draft_id}/approve",
        headers=headers,
        json={"remarks": "Looks good"},
    )
    assert denied.status_code in (401, 403), denied.text

    editor_headers = {"Authorization": f"Bearer {_login(client, 'editor')}"}
    approved = client.post(
        f"/cae/adaptation-drafts/{draft_id}/approve",
        headers=editor_headers,
        json={"remarks": "Looks good"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"

    versions = client.get(
        f"/cae/adaptation-drafts/{draft_id}/versions",
        headers=headers,
    )
    assert versions.status_code == 200
    assert len(versions.json()) >= 1


def test_editor_priority_queue_and_score(client, db_ready):
    editor_token = _login(client, "editor")
    headers = {"Authorization": f"Bearer {editor_token}"}

    scored = client.post(
        "/editor/queue/score",
        headers=headers,
        json={
            "title": "BREAKING plant fire halts production in Asia",
            "summary": "Emergency shutdown after a critical factory fire.",
        },
    )
    assert scored.status_code == 200, scored.text
    assert scored.json()["urgency"] in {"low", "medium", "high", "urgent"}
    assert scored.json()["source"] in {"model", "fallback"}

    ContentService().add_article(
        title="Low-key bakery contest coverage for weekend",
        body="A local bakery contest drew a small crowd downtown.",
        summary="Community feature",
        status="submitted",
        evidence=_DEMO_EVIDENCE,
    )
    ContentService().add_article(
        title="BREAKING emergency bridge collapse blocks interstate traffic",
        body="Rescue crews responded after a critical bridge failure overnight.",
        summary="Urgent transport incident",
        status="submitted",
        evidence=_DEMO_EVIDENCE,
    )

    queue = client.get("/editor/queue", headers=headers)
    assert queue.status_code == 200, queue.text
    body = queue.json()
    assert body["content_count"] >= 2
    urgencies = [str(t.get("urgency") or "medium") for t in body["tasks"] if t.get("task_type") == "content"]
    rank = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    assert urgencies == sorted(urgencies, key=lambda p: rank.get(p, 4))


def test_editor_and_publisher_flow(client, db_ready):
    editor_token = _login(client, "editor")
    publisher_token = _login(client, "publisher")
    editor_headers = {"Authorization": f"Bearer {editor_token}"}
    publisher_headers = {"Authorization": f"Bearer {publisher_token}"}

    created = ContentService().add_article(
        title="Ready for publication desk review",
        body=SAMPLE_ARTICLE,
        summary="Housing plan story",
        status="submitted",
        evidence=_DEMO_EVIDENCE,
    )
    content_id = int(created["content_id"])

    listed = client.get("/editor/content?status=submitted", headers=editor_headers)
    assert listed.status_code == 200
    assert any(row.get("content_id") == content_id for row in listed.json()["items"])
    assert any("editor_queue_urgency" in row for row in listed.json()["items"])

    rework = client.put(
        f"/editor/content/{content_id}/rework",
        headers=editor_headers,
        json={"remarks": "Add more sources"},
    )
    assert rework.status_code == 200, rework.text
    assert rework.json()["status"] == "rework"

    journalist_token = _login(client, "journalist")
    j_headers = {"Authorization": f"Bearer {journalist_token}"}
    rework_list = client.get("/journalist/content?status=rework", headers=j_headers)
    assert rework_list.status_code == 200
    # May or may not include this id if author differs; status filter must work
    assert "items" in rework_list.json()

    resubmit = client.put(
        f"/journalist/content/{content_id}/status",
        headers=j_headers,
        json={"status": "submitted"},
    )
    assert resubmit.status_code == 200, resubmit.text
    assert resubmit.json()["status"] == "submitted"

    approved = client.put(
        f"/editor/content/{content_id}/approve",
        headers=editor_headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    queue = client.get("/publisher/articles", headers=publisher_headers)
    assert queue.status_code == 200
    assert any(row.get("content_id") == content_id for row in queue.json()["articles"])

    templated = client.put(
        f"/publisher/articles/{content_id}/template",
        headers=publisher_headers,
        json={"template_code": "web_standard"},
    )
    assert templated.status_code == 200, templated.text

    preview = client.get(
        f"/publisher/articles/{content_id}/preview",
        headers=publisher_headers,
    )
    assert preview.status_code == 200
    assert "preview_html" in preview.json()

    published = client.post(
        f"/publisher/articles/{content_id}/publish",
        headers=publisher_headers,
    )
    assert published.status_code == 200, published.text
    assert published.json()["publication"]["status"] == "published"


def test_manager_overview_and_forbidden_roles(client):
    manager_token = _login(client, "manager")
    headers = {"Authorization": f"Bearer {manager_token}"}
    overview = client.get("/manager/overview", headers=headers)
    assert overview.status_code == 200
    body = overview.json()
    assert "submitted_pitches" in body
    assert "publication" in body

    bottlenecks = client.get("/manager/bottlenecks", headers=headers)
    assert bottlenecks.status_code == 200, bottlenecks.text
    assert "content_stages" in bottlenecks.json()
    assert "hotspots" in bottlenecks.json()

    analytics = client.get("/manager/analytics", headers=headers)
    assert analytics.status_code == 200, analytics.text
    assert "pipeline" in analytics.json()
    assert "ops" in analytics.json()
    assert "totals" in analytics.json()
    assert "workload_summary" in analytics.json()

    workload = client.get("/manager/workload", headers=headers)
    assert workload.status_code == 200, workload.text
    assert "journalists" in workload.json()

    risk = client.get("/manager/deadline-risk", headers=headers)
    assert risk.status_code == 200, risk.text
    assert "at_risk_count" in risk.json()

    resources = client.get("/manager/resources", headers=headers)
    assert resources.status_code == 200, resources.text
    assert "utilization" in resources.json()

    suggest = client.post(
        "/editor/assign/suggest",
        headers=headers,
        json={"topic": "Politics city council", "title": "Budget debate"},
    )
    assert suggest.status_code == 200, suggest.text
    assert "suggestions" in suggest.json()

    dups = client.post(
        "/editor/pitches/duplicates",
        headers=headers,
        json={"title": "AIA API pitch for civic coverage"},
    )
    assert dups.status_code == 200, dups.text

    journalist_token = _login(client, "journalist")
    denied = client.get(
        "/publisher/articles",
        headers={"Authorization": f"Bearer {journalist_token}"},
    )
    assert denied.status_code == 403


def test_publisher_schedule_requires_future(client, db_ready):
    editor_token = _login(client, "editor")
    publisher_token = _login(client, "publisher")
    editor_headers = {"Authorization": f"Bearer {editor_token}"}
    publisher_headers = {"Authorization": f"Bearer {publisher_token}"}

    created = ContentService().add_article(
        title="Schedule me for next week desk",
        body=SAMPLE_ARTICLE,
        status="submitted",
        evidence=_DEMO_EVIDENCE,
    )
    content_id = int(created["content_id"])
    client.put(f"/editor/content/{content_id}/approve", headers=editor_headers)
    client.put(
        f"/publisher/articles/{content_id}/template",
        headers=publisher_headers,
        json={"template_code": "newsletter"},
    )

    when = (datetime.utcnow() + timedelta(days=2)).isoformat()
    scheduled = client.post(
        f"/publisher/articles/{content_id}/schedule",
        headers=publisher_headers,
        json={"scheduled_at": when},
    )
    assert scheduled.status_code == 200, scheduled.text
    assert scheduled.json()["publication"]["status"] == "scheduled"
