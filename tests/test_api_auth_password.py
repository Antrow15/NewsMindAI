"""Auth password validation endpoints."""

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


def test_weak_password_rejected_on_change(client):
    token = _login(client, "journalist")
    response = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": DEMO_PASSWORDS["journalist"], "new_password": "short"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Validation failed"
    assert body["errors"]


def test_admin_reset_requires_strong_password(client):
    token = _login(client, "admin")
    weak = client.post(
        "/auth/admin/reset-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "publisher", "new_password": "weakpass"},
    )
    assert weak.status_code == 422

    strong = client.post(
        "/auth/admin/reset-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "publisher", "new_password": "PublisherReset@2026!!"},
    )
    assert strong.status_code == 200, strong.text

    # restore demo password
    restore = client.post(
        "/auth/admin/reset-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "publisher", "new_password": DEMO_PASSWORDS["publisher"]},
    )
    assert restore.status_code == 200
