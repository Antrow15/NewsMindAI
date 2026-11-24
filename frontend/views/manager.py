from __future__ import annotations

from datetime import datetime, timedelta

import streamlit as st

from core import api, config, ui


def render_dashboard() -> None:
    ui.header("Dashboard", "Newsroom health, risks, and hotspots.")
    overview = api.get("/manager/overview")
    if overview:
        ui.kpi_row(
            {
                "Submitted pitches": overview.get("submitted_pitches") or 0,
                "Submitted content": overview.get("submitted_content") or 0,
                "Approved content": overview.get("approved_content") or 0,
            },
            hints={
                "Submitted pitches": "Awaiting review",
                "Submitted content": "In editorial queue",
                "Approved content": "Ready for next stage",
            },
            icons={
                "Submitted pitches": "💡",
                "Submitted content": "📄",
                "Approved content": "✅",
            },
        )
        left, right = st.columns([1.15, 1])
        with left:
            ui.bar(overview.get("publication"), caption="Publication pipeline")
        with right:
            ui.score_meters(
                {
                    "Pitch backlog": min(
                        100, int(overview.get("submitted_pitches") or 0) * 12
                    ),
                    "Content backlog": min(
                        100, int(overview.get("submitted_content") or 0) * 12
                    ),
                    "Approved flow": min(
                        100, int(overview.get("approved_content") or 0) * 10
                    ),
                },
                scale="100",
            )

    risk = api.get("/manager/deadline-risk")
    if risk:
        ui.section("Deadline risk")
        at_risk = int(risk.get("at_risk_count") or 0)
        ui.kpi_row(
            {"At risk": at_risk},
            hints={"At risk": "Past or near deadline"},
            icons={"At risk": "⚠"},
        )
        ui.score_meters({"Risk pressure": min(100, at_risk * 20)}, scale="100")
        for row in (risk.get("content_at_risk") or [])[:5]:
            ui.card(
                row.get("title") or "Content",
                status="at risk",
                meta=[row.get("status") or ""],
            )

    bottlenecks = api.get("/manager/bottlenecks")
    if bottlenecks:
        ui.section("Hotspots")
        hotspot_bars = {}
        for h in bottlenecks.get("hotspots") or []:
            label = str(h.get("stage") or h.get("desk") or "Hotspot")
            count = int(h.get("item_count") or h.get("count") or 0)
            hotspot_bars[label] = count
            ui.card(
                label,
                meta=[f"Items · {count or '—'}"],
                body=h.get("note") or h.get("message"),
            )
        if hotspot_bars:
            ui.bar(hotspot_bars, caption="Items stuck by stage")


def render_review() -> None:
    ui.header("Review", "Approve pitches/content and assign journalists.")
    tab_p, tab_c, tab_a = st.tabs(["Pitches", "Content", "Assign"])
    with tab_p:
        status = st.selectbox("Pitch status", config.PITCH_STATUSES, key="mp_st")
        pitches = ui.as_rows(api.get("/manager/pitches", status=status), "pitches")
        for p in pitches[:15]:
            ui.card(
                p.get("title") or "Pitch",
                status=p.get("status"),
                body=p.get("summary"),
            )
            if any(
                p.get(k) is not None
                for k in (
                    "trend_score",
                    "audience_interest_score",
                    "coverage_gap_score",
                    "pitch_importance",
                )
            ):
                ui.score_meters(
                    {
                        "Trend": p.get("trend_score"),
                        "Interest": p.get("audience_interest_score"),
                        "Gap": p.get("coverage_gap_score"),
                        "Importance": p.get("pitch_importance"),
                    }
                )
        if pitches:
            labels = {p.get("title") or "Pitch": p for p in pitches}
            pick = st.selectbox("Act on pitch", list(labels), key="mp_pick")
            pid = int(labels[pick].get("story_pitch_id") or labels[pick].get("id") or 0)
            a, b = st.columns(2)
            if a.button("Approve", key="mp_a", type="primary", disabled=not pid):
                api.put(f"/manager/pitches/{pid}/approve", success="Approved.")
            if b.button("Reject", key="mp_r", disabled=not pid):
                api.put(f"/manager/pitches/{pid}/reject", {"remarks": ""}, success="Rejected.")
    with tab_c:
        status = st.selectbox(
            "Content status",
            config.CONTENT_STATUSES,
            index=config.CONTENT_STATUSES.index("submitted"),
            key="mc_st",
        )
        items = ui.as_rows(api.get("/manager/content", status=status), "items")
        for r in items[:15]:
            ui.card(r.get("title") or "Story", status=r.get("status"), body=r.get("summary"))
        if items:
            labels = {r.get("title") or "Story": r for r in items}
            pick = st.selectbox("Act on story", list(labels), key="mc_pick")
            cid = int(labels[pick].get("content_id") or labels[pick].get("id") or 0)
            a, b = st.columns(2)
            if a.button("Approve", key="mc_a", type="primary", disabled=not cid):
                api.put(f"/manager/content/{cid}/approve", success="Approved.")
            if b.button("Reject", key="mc_r", disabled=not cid):
                api.put(f"/manager/content/{cid}/reject", {"remarks": ""}, success="Rejected.")
    with tab_a:
        st.caption("Assign an approved pitch with deadline.")
        pitches = ui.as_rows(api.get("/manager/pitches", status="approved"), "pitches")
        if not pitches:
            pitches = ui.as_rows(api.get("/manager/pitches", status="submitted"), "pitches")
        if not pitches:
            st.caption("No pitches to assign.")
        else:
            plabels = {p.get("title") or "Pitch": p for p in pitches}
            ppick = st.selectbox("Pitch", list(plabels), key="ma_pitch")
            pid = int(plabels[ppick].get("story_pitch_id") or plabels[ppick].get("id") or 0)
            topic = plabels[ppick].get("title") or ""
            if st.button("Find top 3 journalists", key="ma_sug"):
                res = api.post(
                    "/editor/assign/suggest",
                    {"topic": topic, "title": topic, "limit": 3},
                )
                if res:
                    st.session_state["ma_matches"] = res.get("suggestions") or []
            uid = ui.pick_top_journalist(
                st.session_state.get("ma_matches") or [],
                key="ma_j",
            )
            due = st.date_input("Deadline", value=datetime.utcnow().date() + timedelta(days=3))
            note = st.text_input("Note", key="ma_note")
            if st.button("Assign", type="primary", disabled=not (pid and uid)):
                api.post(
                    f"/manager/pitches/{pid}/assign",
                    {
                        "assignee_user_id": uid,
                        "note": note,
                        "due_at": datetime.combine(due, datetime.strptime("17:00", "%H:%M").time()).isoformat(),
                        "auto_approve": True,
                    },
                    success="Assigned and notified.",
                )


def render_ops() -> None:
    ui.header("Operations", "Bottlenecks, workload, and resources.")
    b = api.get("/manager/bottlenecks")
    if b:
        ui.section("Bottlenecks")
        for key in ("content_stages", "pitch_stages", "publication_stages", "adaptation_stages"):
            rows = b.get(key) or []
            if rows:
                with st.expander(key.replace("_", " ").title()):
                    ui.table(rows, key=f"m_{key}")
    w = api.get("/manager/workload")
    if w:
        ui.section("Workload")
        ui.kpi_row(
            {"Open items": w.get("total_open_items") or 0},
            hints={"Open items": "Across desks"},
            icons={"Open items": "📥"},
        )
        workload_bars = {}
        for j in w.get("journalists") or []:
            name = (
                j.get("full_name")
                or j.get("name")
                or j.get("username")
                or "Journalist"
            )
            open_n = int(j.get("open") or j.get("open_items") or 0)
            workload_bars[name] = open_n
            ui.desk_capacity_card(
                name,
                open_n,
                specialty=j.get("primary_specialization"),
                availability=j.get("availability_status"),
            )
        if workload_bars:
            ui.bar(workload_bars, caption="Open items by journalist")
            st.caption(
                f"Soft full load ≈ {ui.DESK_CAPACITY_FULL} open items. "
                "A single story is light capacity, not full. "
                "Green capacity left = room on the desk; red desk load = overloaded."
            )
    r = api.get("/manager/resources")
    if r:
        ui.section("Resources")
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Overloaded")
            for row in r.get("overloaded") or []:
                ui.card(row.get("desk") or row.get("name") or "Desk", status="high")
        with c2:
            st.caption("Underutilized")
            for row in r.get("underutilized") or []:
                ui.card(row.get("desk") or row.get("name") or "Desk", status="ready")


def render_overview() -> None:
    render_dashboard()


def render_bottlenecks() -> None:
    render_ops()


def render_workload() -> None:
    render_ops()


def render_deadline() -> None:
    render_dashboard()


def render_resources() -> None:
    render_ops()


def render_analytics() -> None:
    render_dashboard()
    res = api.get("/manager/analytics")
    if res:
        totals = {
            k.replace("_", " ").title(): v
            for k, v in (res.get("totals") or {}).items()
            if isinstance(v, (int, float))
        }
        if totals:
            ui.kpi_row(totals)
            ui.bar(totals, caption="Newsroom totals")
            ui.scores_chart(
                {k: min(1.0, float(v) / 20.0) for k, v in totals.items()},
                title="Relative desk volume",
                height=180,
            )


def render_review_queue() -> None:
    render_review()


def render_pitches() -> None:
    render_review()


def render_content() -> None:
    render_review()


def render() -> None:
    render_dashboard()
