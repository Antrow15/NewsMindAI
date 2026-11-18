"""Integration: FastAPI auth + journalist endpoints (Swagger-backed)."""

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


def _login(client: TestClient, username: str = "journalist") -> str:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": DEMO_PASSWORDS[username]},
    )
    assert response.status_code == 200, response.text
    token = response.json()["session_token"]
    assert token
    return token


def test_swagger_docs_available(client):
    docs = client.get("/docs")
    assert docs.status_code == 200
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    paths = openapi.json()["paths"]
    assert "/auth/login" in paths
    assert "/journalist/related-content" in paths
    assert "/journalist/research" not in paths
    assert "/journalist/metadata" not in paths
    assert "/journalist/patents" not in paths


def test_journalist_requires_bearer(client):
    response = client.post(
        "/journalist/related-content",
        json={"title": "budget", "text": "parliament debate"},
    )
    assert response.status_code == 401


def test_publisher_forbidden_on_journalist(client):
    token = _login(client, "publisher")
    response = client.post(
        "/journalist/related-content",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "budget", "text": "parliament debate"},
    )
    assert response.status_code == 403


def test_journalist_related_and_validate(client):
    token = _login(client, "journalist")
    headers = {"Authorization": f"Bearer {token}"}

    validate = client.post(
        "/journalist/validate",
        headers=headers,
        json={
            "title": "Long enough headline for validation",
            "text": "This body is long enough to pass the minimum content body length rule.",
            "status": "draft",
        },
    )
    assert validate.status_code == 200
    assert validate.json()["ok"] is True

    related = client.post(
        "/journalist/related-content",
        headers=headers,
        json={
            "title": "Parliament debates new budget bill today",
            "text": "Politics coverage from the capital about the budget bill.",
            "limit": 5,
        },
    )
    assert related.status_code == 200, related.text
    assert related.json()["source"] == "content"
    assert related.json().get("method") == "tfidf_cosine"
    assert "matches" in related.json()

    logout_resp = client.post("/auth/logout", headers=headers)
    assert logout_resp.status_code == 200


def test_journalist_desk_content_endpoints(client):
    token = _login(client, "journalist")
    headers = {"Authorization": f"Bearer {token}"}
    body_text = (
        "The city council approved a housing plan covering several wards after a public review. "
        "Officials said funding will begin next quarter."
    )

    news = client.post(
        "/journalist/news",
        headers=headers,
        json={
            "title": "Housing plan advances in council",
            "body": body_text,
            "summary": "Council housing update",
            "status": "draft",
            "evidence": [
                {
                    "title": "Council memo",
                    "evidence_type": "link",
                    "source_url": "https://example.com/housing",
                    "text": "Funding note",
                }
            ],
        },
    )
    assert news.status_code == 200, news.text
    news_body = news.json()
    content_id = news_body["content_id"]
    assert news_body["news_id"] > 0
    assert news_body.get("evidence_ids")

    article = client.post(
        "/journalist/articles",
        headers=headers,
        json={
            "title": "Feature on civic housing reform",
            "body": body_text,
            "article_type": "feature",
            "status": "draft",
            "evidence": [
                {
                    "title": "Interview notes",
                    "evidence_type": "document",
                    "source_url": "",
                    "text": "Official confirmed timeline",
                }
            ],
        },
    )
    assert article.status_code == 200, article.text
    assert article.json()["article_id"] > 0
    assert article.json().get("evidence_ids")
    article_id_content = article.json()["content_id"]
    listed_evidence = client.get(
        f"/journalist/content/{article_id_content}/evidence",
        headers=headers,
    )
    assert listed_evidence.status_code == 200, listed_evidence.text
    assert len(listed_evidence.json()["items"]) >= 1

    listed = client.get("/journalist/content?limit=20", headers=headers)
    assert listed.status_code == 200
    assert any(row.get("content_id") == content_id for row in listed.json()["items"])

    viewed = client.get(f"/journalist/content/{content_id}", headers=headers)
    assert viewed.status_code == 200
    assert viewed.json()["content"]["content_id"] == content_id

    submitted = client.put(
        f"/journalist/content/{content_id}/status",
        headers=headers,
        json={"status": "submitted"},
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"

    evidence = client.post(
        "/journalist/evidence",
        headers=headers,
        json={
            "content_id": content_id,
            "title": "Council meeting minutes evidence",
            "evidence_type": "document",
        },
    )
    assert evidence.status_code == 200, evidence.text
    assert evidence.json()["evidence_id"] > 0

    news_list = client.get("/journalist/news", headers=headers)
    assert news_list.status_code == 200
    assert isinstance(news_list.json()["items"], list)

    assert client.get("/journalist/raw-ingest", headers=headers).status_code == 404

    paths = client.get("/openapi.json").json()["paths"]
    assert "/journalist/raw-ingest" not in paths
    assert "/admin/raw-ingest" in paths
    for path in (
        "/journalist/news",
        "/journalist/articles",
        "/journalist/content",
        "/journalist/content/{content_id}",
        "/journalist/content/{content_id}/status",
        "/journalist/evidence",
        "/journalist/content/{content_id}/evidence",
    ):
        assert path in paths
