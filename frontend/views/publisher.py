from __future__ import annotations

from datetime import datetime, time

import streamlit as st
import streamlit.components.v1 as components

from core import api, ui


def render_dashboard() -> None:
    ui.header("Dashboard", "Publication pipeline health.")
    res = api.get("/publisher/analytics")
    if not res:
        return
    approved = res.get("approved") or 0
    ready = res.get("ready") or 0
    scheduled = res.get("scheduled") or 0
    published = res.get("published") or 0
    ui.kpi_row(
        {
            "Approved": approved,
            "Ready": ready,
            "Scheduled": scheduled,
            "Published": published,
        },
        hints={
            "Approved": "Cleared for publishing",
            "Ready": "Template applied",
            "Scheduled": "On the calendar",
            "Published": "Live",
        },
        icons={
            "Approved": "✅",
            "Ready": "📦",
            "Scheduled": "📅",
            "Published": "🚀",
        },
    )
    left, right = st.columns([1.15, 1])
    with left:
        ui.bar(res.get("publications_by_status") or {
            "approved": approved,
            "ready": ready,
            "scheduled": scheduled,
            "published": published,
        }, caption="Publication pipeline")
    with right:
        pipeline = max(approved + ready + scheduled + published, 1)
        ui.score_meters(
            {
                "Approved share": round(100 * approved / pipeline),
                "Ready share": round(100 * ready / pipeline),
                "Scheduled share": round(100 * scheduled / pipeline),
                "Live share": round(100 * published / pipeline),
            },
            scale="100",
        )


def render_queue() -> None:
    ui.header("Publication queue", "Approve, template, schedule and publish.")
    articles = ui.as_rows(api.get("/publisher/articles"), "articles")
    if not articles:
        st.caption("No articles are ready.")
        return
    labels = {a.get("title") or "Article": a for a in articles}
    pick = st.selectbox("Article", list(labels), key="p_pick")
    row = labels[pick]
    cid = int(row.get("content_id") or row.get("id") or 0)
    if not cid:
        return
    status = str(row.get("publication_status") or row.get("status") or "").lower()
    ui.card(row.get("title") or "Article", status=status or None)
    stage = {
        "approved": 35,
        "ready": 55,
        "scheduled": 75,
        "published": 100,
        "draft": 10,
        "submitted": 25,
    }.get(status, 40)
    ui.score_meters({"Pipeline stage": stage}, scale="100")

    step1, step2, step3 = st.tabs(["Approve & template", "Preview", "Publish"])
    with step1:
        if st.button("Approve for publication", key="p_ap"):
            api.put(f"/publisher/articles/{cid}/approve", success="Approved for publication.")
        templates = ui.as_rows(api.get("/publisher/templates"), "templates")
        codes = {f"{t.get('name', t['code'])}": t["code"] for t in templates}
        if codes:
            label = st.selectbox("Template", list(codes), key="p_tpl")
            if st.button("Assign template", key="p_tpl_b"):
                api.put(
                    f"/publisher/articles/{cid}/template",
                    {"template_code": codes[label]},
                    success="Template assigned.",
                )
    with step2:
        preview = api.get(f"/publisher/articles/{cid}/preview")
        if preview:
            st.caption(f"Template · {preview.get('template', {}).get('name', '—')}")
            components.html(preview["preview_html"], height=420, scrolling=True)
    with step3:
        c1, c2, c3 = st.columns([2, 2, 1])
        day = c1.date_input("Date", key="p_day")
        hour = c2.time_input("Time", time(9, 0), key="p_time")
        c3.write("")
        if c3.button("Schedule", key="p_sch", width="stretch"):
            api.post(
                f"/publisher/articles/{cid}/schedule",
                {"scheduled_at": datetime.combine(day, hour).isoformat()},
                success="Scheduled.",
            )
        if st.button("Publish now", type="primary", key="p_pub"):
            api.post(f"/publisher/articles/{cid}/publish", success="Published.")


def render_analytics() -> None:
    render_dashboard()


def render() -> None:
    render_dashboard()
