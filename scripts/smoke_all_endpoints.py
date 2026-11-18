"""Live smoke test: login each demo role and hit its endpoints."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.constants import DEMO_PASSWORDS  # noqa: E402

BASE = "http://127.0.0.1:8000"
SAMPLE_BODY = (
    "The city council approved a housing plan covering several wards after public review. "
    "Officials said funding will begin next quarter for the first phase."
)


def login(client: httpx.Client, username: str) -> str:
    r = client.post(
        "/auth/login",
        json={"username": username, "password": DEMO_PASSWORDS[username]},
    )
    r.raise_for_status()
    return r.json()["session_token"]


def call(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    token: str | None = None,
    json_body: dict[str, Any] | None = None,
    expect: set[int] | None = None,
) -> tuple[str, int, str]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = client.request(method, path, headers=headers, json=json_body)
    ok_codes = expect or {200}
    status = "PASS" if r.status_code in ok_codes else "FAIL"
    detail = ""
    if status == "FAIL":
        detail = (r.text or "")[:180].replace("\n", " ")
    return f"{method} {path}", r.status_code, f"{status}{(' | ' + detail) if detail else ''}"


def run() -> int:
    results: list[tuple[str, str, int, str]] = []
    with httpx.Client(base_url=BASE, timeout=60.0) as client:
        # Health / docs
        for method, path in (("GET", "/docs"), ("GET", "/openapi.json")):
            name, code, status = call(client, method, path)
            results.append(("public", name, code, status))

        openapi = client.get("/openapi.json").json()
        paths = sorted(openapi.get("paths") or {})

        # ---- auth ----
        token_admin = login(client, "admin")
        for item in (
            call(client, "GET", "/auth/me", token=token_admin),
            call(
                client,
                "POST",
                "/auth/change-password",
                token=token_admin,
                json_body={
                    "current_password": DEMO_PASSWORDS["admin"],
                    "new_password": DEMO_PASSWORDS["admin"],
                },
                expect={200, 400, 422},
            ),
        ):
            results.append(("admin/auth", *item))

        # ---- journalist ----
        j = login(client, "journalist")
        news = client.post(
            "/journalist/news",
            headers={"Authorization": f"Bearer {j}"},
            json={
                "title": "Smoke test housing plan advances",
                "body": SAMPLE_BODY,
                "summary": "Council housing update",
                "status": "draft",
                "evidence": [
                    {
                        "title": "Council memo",
                        "evidence_type": "link",
                        "source_url": "https://example.com/housing",
                        "text": "Funding approved",
                    }
                ],
            },
        )
        results.append(("journalist", "POST /journalist/news", news.status_code, "PASS" if news.status_code == 200 else f"FAIL | {news.text[:160]}"))
        content_id = int((news.json() or {}).get("content_id") or 0) if news.status_code == 200 else 0

        article = client.post(
            "/journalist/articles",
            headers={"Authorization": f"Bearer {j}"},
            json={
                "title": "Smoke feature on civic housing reform",
                "body": SAMPLE_BODY,
                "article_type": "feature",
                "status": "draft",
            },
        )
        results.append(("journalist", "POST /journalist/articles", article.status_code, "PASS" if article.status_code == 200 else f"FAIL | {article.text[:160]}"))
        article_id = int((article.json() or {}).get("content_id") or 0) if article.status_code == 200 else content_id

        for item in (
            call(client, "GET", "/journalist/content?limit=10", token=j),
            call(client, "GET", f"/journalist/content/{content_id or 1}", token=j, expect={200, 404}),
            call(client, "GET", "/journalist/news?limit=10", token=j),
            call(client, "GET", "/journalist/raw-ingest?limit=10", token=j),
            call(
                client,
                "POST",
                "/journalist/research",
                token=j,
                json_body={"query": "housing plan", "limit": 5},
            ),
            call(
                client,
                "POST",
                "/journalist/evidence-search",
                token=j,
                json_body={"query": "housing funding", "limit": 5},
            ),
            call(
                client,
                "POST",
                "/journalist/metadata",
                token=j,
                json_body={"text": SAMPLE_BODY},
            ),
            call(
                client,
                "POST",
                "/journalist/duplicates",
                token=j,
                json_body={
                    "documents": [
                        {"id": "a", "title": "Housing plan", "text": SAMPLE_BODY},
                        {"id": "b", "title": "Housing plan update", "text": SAMPLE_BODY},
                    ]
                },
            ),
            call(
                client,
                "POST",
                "/journalist/credibility",
                token=j,
                json_body={"text": SAMPLE_BODY, "limit": 3},
            ),
            call(
                client,
                "POST",
                "/journalist/patents",
                token=j,
                json_body={"query": "housing construction materials", "limit": 3},
            ),
            call(
                client,
                "POST",
                "/journalist/validate",
                token=j,
                json_body={"title": "Long enough headline for validation", "text": SAMPLE_BODY, "status": "draft"},
            ),
            call(
                client,
                "POST",
                "/journalist/related-content",
                token=j,
                json_body={"title": "Housing plan advances in council", "text": SAMPLE_BODY, "limit": 5},
            ),
            call(
                client,
                "PUT",
                f"/journalist/content/{content_id or 1}/status",
                token=j,
                json_body={"status": "submitted"},
                expect={200, 404},
            ),
            call(
                client,
                "POST",
                "/journalist/evidence",
                token=j,
                json_body={
                    "content_id": content_id or article_id or 1,
                    "title": "Smoke evidence doc",
                    "evidence_type": "link",
                    "source_url": "https://example.com/housing",
                },
                expect={200, 404, 422},
            ),
            # forbidden desk
            call(client, "GET", "/aia/performance", token=j, expect={403}),
        ):
            results.append(("journalist", *item))

        # ---- analyst / AIA ----
        a = login(client, "analyst")
        for item in (
            call(
                client,
                "POST",
                "/aia/analyze-engagement",
                token=a,
                json_body={"views": 500, "likes": 40, "shares": 12, "comments": 8},
            ),
            call(
                client,
                "POST",
                "/aia/analyze-interest",
                token=a,
                json_body={"views": 500, "likes": 40, "shares": 12, "comments": 8},
            ),
            call(
                client,
                "POST",
                "/aia/analyze-trends",
                token=a,
                json_body={"title": "Sports finals draw record TV audience", "summary": "Ratings surge overnight"},
            ),
            call(
                client,
                "POST",
                "/aia/generate-story-pitch",
                token=a,
                json_body={
                    "title": "Smoke AIA pitch on civic sports funding",
                    "summary": "City may expand youth sports programs next year.",
                    "category": "Sports",
                    "trend_score": 70,
                    "audience_interest_score": 65,
                    "coverage_gap_score": 40,
                },
            ),
            call(client, "GET", "/aia/story-pitches", token=a),
            call(client, "GET", "/aia/story-pitches/top", token=a),
            call(client, "GET", "/aia/performance", token=a),
            call(client, "GET", "/editor/queue", token=a, expect={403}),
        ):
            results.append(("analyst", *item))

        # ---- editor ----
        e = login(client, "editor")
        for item in (
            call(client, "GET", "/editor/queue", token=e),
            call(
                client,
                "POST",
                "/editor/queue/score",
                token=e,
                json_body={
                    "title": "BREAKING plant fire halts production",
                    "summary": "Emergency shutdown after a factory fire.",
                },
            ),
            call(client, "GET", "/editor/pitches", token=e),
            call(
                client,
                "POST",
                "/editor/pitches/duplicates",
                token=e,
                json_body={"title": "Smoke AIA pitch on civic sports funding"},
            ),
            call(
                client,
                "POST",
                "/editor/assign/suggest",
                token=e,
                json_body={"topic": "Sports city funding", "title": "Youth sports budget"},
            ),
            call(client, "GET", "/editor/content?status=submitted", token=e),
        ):
            results.append(("editor", *item))

        # content approve/rework if we have submitted content
        if content_id:
            rework = call(
                client,
                "PUT",
                f"/editor/content/{content_id}/rework",
                token=e,
                json_body={"remarks": "Add one more source"},
            )
            results.append(("editor", *rework))
            # journalist resubmit
            resub = call(
                client,
                "PUT",
                f"/journalist/content/{content_id}/status",
                token=j,
                json_body={"status": "submitted"},
            )
            results.append(("journalist", *resub))
            appr = call(client, "PUT", f"/editor/content/{content_id}/approve", token=e)
            results.append(("editor", *appr))

        # ---- CAE / adapter ----
        c = login(client, "adapter")
        adapt_body = {
            "original_title": "Smoke feature on civic housing reform",
            "original_content": SAMPLE_BODY,
            "target_platforms": ["SOCIAL_MEDIA", "WEBSITE"],
        }
        created = client.post(
            "/cae/adaptations",
            headers={"Authorization": f"Bearer {c}"},
            json=adapt_body,
        )
        results.append(
            (
                "adapter",
                "POST /cae/adaptations",
                created.status_code,
                "PASS" if created.status_code in {200, 201} else f"FAIL | {created.text[:180]}",
            )
        )
        draft_id = None
        adaptation_id = None
        if created.status_code in {200, 201}:
            payload = created.json()
            adaptation_id = payload.get("id")
            drafts = payload.get("drafts") or []
            if drafts:
                draft_id = drafts[0].get("id")

        for item in (
            call(
                client,
                "GET",
                f"/cae/adaptations/{adaptation_id or 1}",
                token=c,
                expect={200, 404},
            ),
            call(client, "GET", f"/cae/adaptation-drafts/{draft_id or 1}", token=c, expect={200, 404}),
        ):
            results.append(("adapter", *item))
        if draft_id:
            for item in (
                call(
                    client,
                    "POST",
                    f"/cae/adaptation-drafts/{draft_id}/regenerate",
                    token=c,
                    json_body={"remarks": "Try a shorter social cut"},
                    expect={200, 201},
                ),
                call(
                    client,
                    "POST",
                    f"/cae/adaptation-drafts/{draft_id}/approve",
                    token=c,
                    json_body={"remarks": "Looks good"},
                    expect={200, 400, 422},
                ),
                call(
                    client,
                    "GET",
                    f"/cae/adaptation-drafts/{draft_id}/versions",
                    token=c,
                ),
            ):
                results.append(("adapter", *item))

        # ---- publisher ----
        p = login(client, "publisher")
        for item in (
            call(client, "GET", "/publisher/articles", token=p),
            call(client, "GET", "/publisher/analytics", token=p),
        ):
            results.append(("publisher", *item))
        if content_id:
            for item in (
                call(
                    client,
                    "PUT",
                    f"/publisher/articles/{content_id}/template",
                    token=p,
                    json_body={"template_code": "web_standard"},
                    expect={200, 404, 400},
                ),
                call(client, "GET", f"/publisher/articles/{content_id}/preview", token=p, expect={200, 404, 400}),
                call(client, "POST", f"/publisher/articles/{content_id}/publish", token=p, expect={200, 404, 400}),
            ):
                results.append(("publisher", *item))

        # ---- manager ----
        m = login(client, "manager")
        for item in (
            call(client, "GET", "/manager/overview", token=m),
            call(client, "GET", "/manager/queue", token=m),
            call(client, "GET", "/manager/bottlenecks", token=m),
            call(client, "GET", "/manager/analytics", token=m),
            call(client, "GET", "/manager/workload", token=m),
            call(client, "GET", "/manager/deadline-risk", token=m),
            call(client, "GET", "/manager/resources", token=m),
            call(client, "GET", "/manager/pitches", token=m),
            call(client, "GET", "/manager/content?status=submitted", token=m),
            call(
                client,
                "POST",
                "/admin/users",
                token=m,
                json_body={
                    "username": "smoke_mgr_user",
                    "password": "TempPass@NewsMind2026!",
                    "first_name": "Smoke",
                    "last_name": "Manager",
                    "email": "smoke.mgr.user@newsmind.local",
                    "role_code": "journalist",
                },
                expect={200, 400, 422},
            ),
        ):
            results.append(("manager", *item))

        # ---- admin can hit every desk + admin pipeline ----
        for item in (
            call(client, "GET", "/admin/csv-files", token=token_admin),
            call(client, "GET", "/aia/performance", token=token_admin),
            call(client, "GET", "/editor/queue", token=token_admin),
            call(client, "GET", "/cae/adaptations/1", token=token_admin, expect={200, 404}),
            call(client, "GET", "/publisher/articles", token=token_admin),
            call(client, "GET", "/manager/overview", token=token_admin),
            call(
                client,
                "POST",
                "/journalist/related-content",
                token=token_admin,
                json_body={"title": "Admin related check", "text": SAMPLE_BODY, "limit": 3},
            ),
            call(
                client,
                "POST",
                "/admin/categories",
                token=token_admin,
                json_body={"name": "SmokeCat", "description": "smoke"},
                expect={200, 400, 422},
            ),
        ):
            results.append(("admin-all", *item))

        # logout
        results.append(("admin/auth", *call(client, "POST", "/auth/logout", token=token_admin)))

    # Print report
    failed = [r for r in results if r[3].startswith("FAIL")]
    print(f"OpenAPI path count: {len(paths)}")
    print(f"Checked calls: {len(results)}  PASS={len(results)-len(failed)}  FAIL={len(failed)}")
    print("-" * 80)
    by_role: dict[str, list] = {}
    for role, name, code, status in results:
        by_role.setdefault(role, []).append((name, code, status))
    for role, rows in by_role.items():
        print(f"\n## {role}")
        for name, code, status in rows:
            mark = "OK" if status.startswith("PASS") else "X "
            print(f"  {mark} {code:>3}  {name}  {'' if status=='PASS' else status}")

    out = ROOT / "scripts" / "smoke_report.json"
    out.write_text(
        json.dumps(
            [{"role": r, "endpoint": n, "status_code": c, "result": s} for r, n, c, s in results],
            indent=2,
        ),
        encoding="utf-8",
    )
    print("\nWrote", out)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
