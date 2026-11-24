"""Journalist — My content library (author-scoped)."""

from __future__ import annotations

import streamlit as st

from core import api, config, ui


def render() -> None:
    ui.header("My content", "Stories you own — drafts, submissions, and published work.")
    c1, c2 = st.columns([2, 1])
    status = c1.selectbox("Status", ["all", *config.CONTENT_STATUSES], key="jl_status")
    limit = c2.number_input("Show", 1, 100, 20, key="jl_limit")
    data = api.get(
        "/journalist/content",
        limit=limit,
        status=None if status == "all" else status,
    )
    items = ui.as_rows(data, "items")
    if not items:
        st.caption("No stories yet. Create one or wait for an editor assignment.")
        return

    labels = {
        f"{r.get('title') or 'Untitled'} · {(r.get('status') or '').title()}": r for r in items
    }
    pick = st.selectbox("Open story", list(labels), key="jl_pick")
    row = labels[pick]
    cid = int(row.get("content_id") or row.get("id") or 0)
    if not cid:
        return

    ui.card(
        row.get("title") or "Untitled",
        status=row.get("status"),
        meta=[
            f"Type · {(row.get('content_kind') or 'story').title()}",
            f"Updated · {row.get('updated_at') or '—'}",
            f"Deadline · {row.get('due_at') or 'Not set'}" if row.get("due_at") else "",
        ],
        body=row.get("summary"),
    )

    detail = api.get(f"/journalist/content/{cid}")
    content = (detail or {}).get("content") or {}
    body = content.get("body") or content.get("text") or content.get("content_body")
    if body:
        with st.expander("Full body", expanded=False):
            st.write(body)

    ev_tab, status_tab, cred_tab = st.tabs(["Evidence", "Status", "Credibility"])
    with ev_tab:
        evidence = ui.as_rows(
            api.get(f"/journalist/content/{cid}/evidence"), "evidence", "items"
        )
        if evidence:
            for e in evidence:
                ui.card(
                    e.get("title") or "Evidence",
                    meta=[e.get("evidence_type") or "", e.get("source_url") or ""],
                    body=e.get("body_text") or e.get("ocr_text") or e.get("text"),
                )
        else:
            st.caption("No evidence attached yet.")
        with st.expander("Add evidence"):
            with st.form(f"jl_ev_{cid}", clear_on_submit=True):
                title = st.text_input("Title")
                c1, c2 = st.columns(2)
                etype = c1.text_input("Type", "document")
                url = c2.text_input("Source URL")
                text = st.text_area("Notes", height=100)
                if st.form_submit_button("Attach"):
                    api.post(
                        "/journalist/evidence",
                        {
                            "content_id": cid,
                            "title": title,
                            "evidence_type": etype,
                            "source_url": url,
                            "text": text,
                        },
                        success="Evidence added.",
                    )
    with status_tab:
        current = content.get("status") or row.get("status")
        options = config.CONTENT_STATUSES
        new_status = st.selectbox(
            "Set status",
            options,
            index=options.index(current) if current in options else 0,
            key=f"jl_st_{cid}",
        )
        if st.button("Update status", key=f"jl_stb_{cid}"):
            api.put(
                f"/journalist/content/{cid}/status",
                {"status": new_status},
                success=f"Marked as {new_status}.",
            )
    with cred_tab:
        if st.button("Assess credibility", key=f"jl_cr_{cid}"):
            res = api.post("/journalist/credibility", {"content_id": cid})
            if res:
                st.session_state[f"jl_cred_{cid}"] = res
        res = st.session_state.get(f"jl_cred_{cid}")
        if res:
            score = res.get("credibility_score") or res.get("score")
            ui.kpi_row(
                {
                    "Evidence items": res.get("evidence_count") or 0,
                    "Credibility": score if score is not None else "—",
                },
                hints={
                    "Evidence items": "Attached to this story",
                    "Credibility": res.get("summary") or "Model assessment",
                },
                icons={"Evidence items": "📎", "Credibility": "🛡️"},
            )
            if score is not None:
                left, right = st.columns(2)
                with left:
                    ui.score_meters({"Credibility": score})
                with right:
                    ui.scores_chart({"Credibility": score}, title="Credibility", height=140)
            elif res.get("summary"):
                st.write(res.get("summary"))
            ui.table(res.get("claims"), key=f"jl_claims_{cid}", hide_ids=True)
