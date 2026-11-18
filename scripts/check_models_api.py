"""Quick check that trained models answer via API."""

from __future__ import annotations

import httpx

from config.constants import DEMO_PASSWORDS

BASE = "http://127.0.0.1:8000"


def login(client: httpx.Client, username: str) -> dict[str, str]:
    token = client.post(
        "/auth/login",
        json={"username": username, "password": DEMO_PASSWORDS[username]},
    ).json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=60.0) as client:
        eh = login(client, "editor")
        r1 = client.post(
            "/editor/queue/score",
            headers=eh,
            json={
                "title": "BREAKING plant fire halts production",
                "summary": "Emergency crews on scene after critical factory fire",
            },
        )
        print("EDITOR  POST /editor/queue/score", r1.status_code, r1.json())

        jh = login(client, "journalist")
        r2 = client.post(
            "/journalist/related-content",
            headers=jh,
            json={
                "title": "Housing plan advances in council",
                "text": "Council housing funding update for city wards",
                "limit": 5,
            },
        )
        print("JOURN   POST /journalist/related-content", r2.status_code, r2.json())

        ah = login(client, "adapter")
        r3 = client.post(
            "/cae/adaptations",
            headers=ah,
            json={
                "original_title": "City housing plan advances",
                "original_content": (
                    "The city council approved a housing plan. "
                    "Officials said funding will begin next quarter. "
                    "Neighbors asked for more transit links."
                ),
                "target_platforms": ["SOCIAL_MEDIA"],
            },
        )
        print("CAE     POST /cae/adaptations", r3.status_code, r3.json() if r3.headers.get("content-type", "").startswith("application/json") else r3.text)


if __name__ == "__main__":
    main()
