"""Integration: AIA (Audience Insight Analyst) API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from config.constants import DEMO_PASSWORDS
from modules.authentication import logout


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


def test_aia_paths_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/aia/analyze-engagement" in paths
    assert "/aia/predict-category" not in paths
    assert "/aia/generate-story-pitch" in paths
    assert "/aia/story-pitches" in paths
    assert "/auth/change-password" in paths


def test_journalist_forbidden_on_aia(client):
    token = _login(client, "journalist")
    response = client.post(
        "/aia/analyze-engagement",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_analyst_can_generate_and_list_pitch(client):
    token = _login(client, "analyst")
    headers = {"Authorization": f"Bearer {token}"}

    engagement = client.post(
        "/aia/analyze-engagement",
        headers=headers,
        json={"views": 200, "likes": 40, "shares": 12, "comments": 6},
    )
    assert engagement.status_code == 200, engagement.text
    assert engagement.json()["engagement_score"] >= 0
    assert engagement.json()["source"] in {"heuristic", "fallback", "model"}

    scores = client.post(
        "/aia/analyze-trends",
        headers=headers,
        json={"title": "New technology tools reshape newsrooms", "summary": "AI tools expand."},
    )
    assert scores.status_code == 200
    assert "trend_score" in scores.json()

    # Priority model is Editor-owned; AIA uses formula for pitch priority.
    # Category is manual entry (no category model endpoint).
    created = client.post(
        "/aia/generate-story-pitch",
        headers=headers,
        json={
            "title": "AIA API pitch for civic coverage",
            "summary": "Audience interest is rising around local council budgets this week.",
            "category": "City",
            "trend_score": 90,
            "audience_interest_score": 90,
            "coverage_gap_score": 80,
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["story_pitch_id"] > 0
    assert body["pitch_importance"] == "high"
    assert body.get("importance_source") == "formula"
    assert body.get("source_type") == "AI_GENERATED"
    assert body.get("created_by_desk") == "AIA"

    listed = client.get("/aia/story-pitches", headers=headers)
    assert listed.status_code == 200
    assert any(
        row.get("story_pitch_id") == body["story_pitch_id"]
        and row.get("created_by_desk") == "AIA"
        for row in listed.json().get("pitches") or []
    )

    performance = client.get("/aia/performance", headers=headers)
    assert performance.status_code == 200, performance.text
    assert "insights" in performance.json()
    assert "publication_by_status" in performance.json()
