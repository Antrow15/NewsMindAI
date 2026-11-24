"""AIA desk — ML scores story ideas; pitches go to the editor queue."""

from __future__ import annotations

import streamlit as st

from core import api, ui


def render_dashboard() -> None:
    ui.header("Dashboard", "Audience performance at a glance.")
    res = api.get("/aia/performance")
    if not res:
        return

    by_status = res.get("content_by_status") or {}
    pub = res.get("publication_by_status") or {}
    recent = res.get("recent_published") or []
    ui.kpi_row(
        {
            "Published": pub.get("published") or len(recent) or 0,
            "In review": by_status.get("submitted") or by_status.get("Submitted") or 0,
            "Drafts": by_status.get("draft") or by_status.get("Draft") or 0,
            "Outcomes": len(res.get("pitch_outcomes") or []),
        },
        hints={
            "Published": "Live pieces",
            "In review": "Awaiting editorial",
            "Drafts": "Still in progress",
            "Outcomes": "Pitch result rows",
        },
        icons={
            "Published": "📢",
            "In review": "🔎",
            "Drafts": "📝",
            "Outcomes": "📊",
        },
    )

    for line in res.get("insights") or []:
        st.write("•", line)
    c1, c2 = st.columns(2)
    with c1:
        ui.bar(res.get("content_by_status"), caption="Content by status")
    with c2:
        ui.bar(res.get("publication_by_status"), caption="Publications by status")
    pub_map = res.get("publication_by_status") or {}
    content_map = res.get("content_by_status") or {}
    if pub_map or content_map:
        merged = {**{f"Content · {k}": v for k, v in content_map.items() if isinstance(v, (int, float))},
                  **{f"Pub · {k}": v for k, v in pub_map.items() if isinstance(v, (int, float))}}
        total = max(sum(merged.values()), 1)
        ui.score_meters(
            {k: round(100 * float(v) / total) for k, v in list(merged.items())[:6]},
            scale="100",
        )
    ui.section("Recently published")
    for row in res.get("recent_published") or []:
        ui.card(
            row.get("title") or "Story",
            status=row.get("status") or "published",
            meta=[row.get("published_at") or ""],
        )
    ui.section("Pitch outcomes")
    ui.table(res.get("pitch_outcomes"), key="a_outcomes")


def render_generate_pitch() -> None:
    ui.header(
        "Generate pitch",
        "You supply the story idea · ML fills trend / interest scores and pitch importance for editors.",
    )
    st.info(
        "Pitches are **not** invented end-to-end by ML. "
        "Enter a title, summary, and category; leave scores at 0 so the audience models compute them. "
        "The pitch is then submitted to the editor approval queue."
    )

    title = st.text_input("Story idea (title)", key="a_pitch_title", help="What should the newsroom cover?")
    summary = st.text_area(
        "Brief / angle",
        key="a_pitch_summary",
        height=100,
        help="Short context the trend model uses.",
    )
    category = st.text_input("Category (manual)", value="City", key="a_pitch_cat")

    ui.section("Audience signals (optional)")
    st.caption("Used when interest score is left to ML. Defaults are fine for a first pass.")
    c = st.columns(4)
    metrics = {
        "views": c[0].number_input("Views", 0.0, value=120.0, key="a_v"),
        "likes": c[1].number_input("Likes", 0.0, value=25.0, key="a_l"),
        "shares": c[2].number_input("Shares", 0.0, value=8.0, key="a_s"),
        "comments": c[3].number_input("Comments", 0.0, value=4.0, key="a_c"),
    }

    with st.expander("Override scores manually (optional)"):
        st.caption("Leave at 0 so create-pitch lets ML fill trend / interest (gap defaults to 40).")
        oc = st.columns(3)
        trend_override = oc[0].number_input("Trend override", 0.0, 100.0, 0.0, key="a_to")
        interest_override = oc[1].number_input("Interest override", 0.0, 100.0, 0.0, key="a_io")
        gap_override = oc[2].number_input("Coverage gap override", 0.0, 100.0, 0.0, key="a_go")

    preview = st.session_state.get("a_pitch_preview")
    a, b = st.columns(2)
    if a.button("1 · Run ML scores", type="secondary", width="stretch"):
        if not (title or "").strip() or not (summary or "").strip():
            st.warning("Add a title and brief first.")
        else:
            trend = api.post("/aia/analyze-trends", {"title": title, "summary": summary})
            interest = api.post("/aia/analyze-interest", metrics)
            engagement = api.post("/aia/analyze-engagement", metrics)
            if trend or interest or engagement:
                st.session_state["a_pitch_preview"] = {
                    "trend": trend,
                    "interest": interest,
                    "engagement": engagement,
                }
                preview = st.session_state["a_pitch_preview"]

    if preview:
        t = preview.get("trend") or {}
        i = preview.get("interest") or {}
        e = preview.get("engagement") or {}
        ui.kpi_row(
            {
                "Trend": t.get("trend_score"),
                "Interest": i.get("audience_interest_score"),
                "Engagement": e.get("engagement_score"),
                "Segment": i.get("segment") or "—",
            },
            hints={
                "Trend": f"Source · {t.get('source') or 'model'}",
                "Interest": f"Source · {i.get('source') or 'model'}",
                "Engagement": f"Source · {e.get('source') or 'model'}",
                "Segment": "Audience segment",
            },
            icons={
                "Trend": "📈",
                "Interest": "🎯",
                "Engagement": "💬",
                "Segment": "👥",
            },
        )
        left, right = st.columns([1.1, 1])
        with left:
            ui.score_meters(
                {
                    "Trend": t.get("trend_score"),
                    "Interest": i.get("audience_interest_score"),
                    "Engagement": e.get("engagement_score"),
                }
            )
        with right:
            ui.scores_chart(
                {
                    "Trend": t.get("trend_score"),
                    "Interest": i.get("audience_interest_score"),
                    "Engagement": e.get("engagement_score"),
                },
                title="ML score profile",
                height=180,
            )

    if b.button("2 · Create pitch for editors", type="primary", width="stretch"):
        payload = {
            "title": title,
            "summary": summary,
            "category": category,
            "trend_score": trend_override,
            "audience_interest_score": interest_override,
            "coverage_gap_score": gap_override,
            "views": metrics["views"],
            "likes": metrics["likes"],
            "shares": metrics["shares"],
            "comments": metrics["comments"],
        }
        res = api.post("/aia/generate-story-pitch", payload)
        if res:
            st.success("Pitch created with ML importance and sent to the editor queue.")
            ui.kpi_row(
                {
                    "Importance": res.get("pitch_importance"),
                    "Trend": res.get("trend_score"),
                    "Interest": res.get("audience_interest_score"),
                    "Gap": res.get("coverage_gap_score"),
                },
                hints={
                    "Importance": f"Formula · {res.get('importance_source') or '—'}",
                    "Trend": "Stored on pitch",
                    "Interest": "Stored on pitch",
                    "Gap": "Default 40 if unset",
                },
            )
            ui.scores_chart(
                {
                    "Importance": res.get("pitch_importance"),
                    "Trend": res.get("trend_score"),
                    "Interest": res.get("audience_interest_score"),
                    "Gap": res.get("coverage_gap_score"),
                },
                title="Pitch scores for editors",
            )


def render_pitches() -> None:
    ui.header("Pitches", "Story pitches already scored and waiting on (or past) editorial.")
    which = st.radio("Show", ["All", "Top"], horizontal=True)
    res = api.get("/aia/story-pitches/top" if which == "Top" else "/aia/story-pitches")
    pitches = ui.as_rows(res, "pitches")
    if not pitches:
        st.caption("No pitches yet — create one with ML scores.")
        return
    for p in pitches:
        ui.card(
            p.get("title") or "Pitch",
            status=p.get("priority") or p.get("status"),
            meta=[
                f"Priority · {p.get('priority') or '—'}",
                f"Source · {p.get('source_type') or '—'} · {p.get('created_by_desk') or ''}",
            ],
            body=p.get("summary"),
        )
        ui.score_meters(
            {
                "Trend": p.get("trend_score"),
                "Interest": p.get("audience_interest_score"),
                "Gap": p.get("coverage_gap_score"),
                "Importance": p.get("pitch_importance"),
            }
        )
        st.divider()


def render_scores() -> None:
    ui.header("Scores", "Run audience ML without creating a pitch.")
    c = st.columns(4)
    metrics = {
        "views": c[0].number_input("Views", 0.0, value=120.0, key="as_v"),
        "likes": c[1].number_input("Likes", 0.0, value=25.0, key="as_l"),
        "shares": c[2].number_input("Shares", 0.0, value=8.0, key="as_s"),
        "comments": c[3].number_input("Comments", 0.0, value=4.0, key="as_c"),
    }
    a, b = st.columns(2)
    if a.button("Analyze engagement", width="stretch"):
        res = api.post("/aia/analyze-engagement", metrics)
        if res:
            ui.kpi_row(
                {
                    "Engagement score": res.get("engagement_score"),
                    "Source": res.get("source"),
                }
            )
            ui.score_meters({"Engagement": res.get("engagement_score")})
    if b.button("Analyze interest", width="stretch"):
        res = api.post("/aia/analyze-interest", metrics)
        if res:
            ui.kpi_row(
                {
                    "Interest score": res.get("audience_interest_score"),
                    "Segment": res.get("segment"),
                }
            )
            ui.score_meters({"Interest": res.get("audience_interest_score")})
    st.divider()
    title = st.text_input("Title", key="as_t")
    summary = st.text_area("Summary", key="as_sum", height=80)
    if st.button("Analyze trend"):
        res = api.post("/aia/analyze-trends", {"title": title, "summary": summary})
        if res:
            ui.kpi_row(
                {
                    "Trend score": res.get("trend_score"),
                    "Category hint": res.get("category") or "—",
                    "Confidence": res.get("category_confidence"),
                }
            )
            left, right = st.columns(2)
            with left:
                ui.score_meters(
                    {
                        "Trend": res.get("trend_score"),
                        "Category confidence": res.get("category_confidence"),
                    }
                )
            with right:
                ui.scores_chart(
                    {
                        "Trend": res.get("trend_score"),
                        "Confidence": res.get("category_confidence"),
                    },
                    title="Trend model",
                    height=160,
                )


def render_performance() -> None:
    render_dashboard()


def render() -> None:
    render_dashboard()
