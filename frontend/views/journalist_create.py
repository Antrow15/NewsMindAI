"""Journalist — Create story with live similar cases while typing."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import api, config, ui

EVIDENCE_TEMPLATE = pd.DataFrame(
    {"title": [""], "evidence_type": ["document"], "source_url": [""], "text": [""]}
)


def _fingerprint(title: str, text: str) -> str:
    return f"{title.strip()}|{text.strip()[:800]}"


def _refresh_recommendations(title: str, draft_text: str, status: str) -> None:
    if not (title.strip() or draft_text.strip()):
        return
    if len(title.strip()) < 4 and len(draft_text.strip()) < 20:
        return
    related = api.post(
        "/journalist/related-content",
        {"title": title, "text": draft_text, "limit": 8},
    )
    if related:
        st.session_state["jc_recommendations"] = related
        matches = related.get("matches") or []
        best = float(related.get("best_score") or 0)
        if best >= 0.55 and matches:
            st.session_state["jc_duplicate_flag"] = {
                "best_score": best,
                "title": matches[0].get("title") or matches[0].get("headline"),
            }
        else:
            st.session_state.pop("jc_duplicate_flag", None)
    validation = api.post(
        "/journalist/validate",
        {"title": title, "text": draft_text, "status": status},
    )
    if validation:
        st.session_state["jc_validation"] = validation


def render() -> None:
    ui.header(
        "Create",
        "Write on the left — related published stories update on the right as you type.",
    )

    left, right = st.columns([1.15, 1.0], gap="medium")

    with left:
        ui.section("Compose")
        kind = st.radio("Type", ["News", "Article"], horizontal=True, key="jc_kind")
        title = st.text_input("Title", key="jc_title")
        body = st.text_area("Body", height=200, help="Minimum 40 characters.", key="jc_body")
        summary = st.text_area("Summary", height=70, key="jc_summary")

        extra: dict = {}
        if kind == "News":
            c1, c2, c3 = st.columns(3)
            extra["event_type"] = c1.text_input("Event type", "city", key="jc_etype")
            extra["event_location"] = c2.text_input("Location", key="jc_eloc")
            extra["severity"] = c3.selectbox("Severity", config.SEVERITIES, key="jc_sev")
            extra["breaking"] = st.checkbox("Breaking news", key="jc_brk")
        else:
            c1, c2 = st.columns(2)
            extra["article_type"] = c1.selectbox("Article type", config.ARTICLE_TYPES, key="jc_atype")
            extra["read_time"] = int(c2.number_input("Read time (min)", 1, 120, 3, key="jc_rtime"))

        ui.section("Evidence")
        st.caption("At least one source with a title.")
        evidence = st.data_editor(
            EVIDENCE_TEMPLATE,
            num_rows="dynamic",
            hide_index=True,
            key="jc_evidence",
            column_config={
                "title": "Title",
                "evidence_type": "Type",
                "source_url": "Source URL",
                "text": "Notes",
            },
        )
        status = st.radio("Save as", ["draft", "submitted"], horizontal=True, key="jc_status")

    draft_text = (body or summary or "").strip()
    title = (title or "").strip()
    fp = _fingerprint(title, draft_text)
    # Auto-refresh when draft changes enough (after Streamlit rerun from typing).
    if (
        fp
        and fp != st.session_state.get("jc_fp")
        and (len(title) >= 4 or len(draft_text) >= 20)
    ):
        st.session_state["jc_fp"] = fp
        with st.spinner("Finding related stories…"):
            try:
                _refresh_recommendations(title, draft_text, status)
            except Exception:
                st.session_state["jc_rec_error"] = True

    with right:
        ui.section("Similar cases")
        st.caption("Updates while you write — use these for reference or evidence.")
        if st.session_state.pop("jc_rec_error", None):
            st.caption("Could not refresh related stories right now.")

        dup = st.session_state.get("jc_duplicate_flag")
        if dup:
            st.error(
                f"Possible duplicate (score {dup['best_score']:.2f}) — "
                f"similar to “{dup.get('title') or 'an existing story'}”."
            )

        validation = st.session_state.get("jc_validation")
        if validation and not validation.get("ok"):
            st.warning("Draft needs attention before submit.")
            for err in validation.get("errors") or []:
                st.write("•", err)

        recommendations = st.session_state.get("jc_recommendations")
        if recommendations:
            best = float(recommendations.get("best_score") or 0)
            ui.kpi_row(
                {
                    "Match level": recommendations.get("relevancy") or "—",
                    "Best similarity": f"{best:.0%}" if best <= 1 else f"{best:.2f}",
                },
                hints={
                    "Match level": "Against published corpus",
                    "Best similarity": "Closest related story",
                },
                icons={"Match level": "🔎", "Best similarity": "📊"},
            )
            ui.score_meters({"Best similarity": best if best <= 1 else best / 100.0})
            for m in recommendations.get("matches") or []:
                score = m.get("score")
                ui.card(
                    m.get("title") or m.get("headline") or "Related story",
                    status=m.get("status") or "published",
                    meta=[m.get("summary") or ""],
                )
                if score is not None:
                    ui.score_meters({"Similarity": score})
        else:
            st.caption("Start typing a title or body — related stories will appear here.")

    st.divider()
    override = st.checkbox(
        "Submit even if validation failed / duplicate flagged",
        value=False,
        key="jc_override",
    )
    if st.button("Publish to my desk", type="primary", key="jc_submit"):
        items = [
            e
            for e in evidence.fillna("").to_dict("records")
            if str(e.get("title", "")).strip()
        ]
        if not title:
            st.error("Title is required.")
            return
        if len((body or "").strip()) < 40:
            st.error("Body must be at least 40 characters.")
            return
        if not items:
            st.error("Add at least one evidence row with a title.")
            return
        if st.session_state.get("jc_duplicate_flag") and not override:
            st.error("Possible duplicate flagged — revise the angle or check override.")
            return
        validation = st.session_state.get("jc_validation")
        if validation is not None and not validation.get("ok") and not override:
            st.error("Fix validation issues or check the override box.")
            return

        payload = {
            "title": title,
            "body": body,
            "summary": summary,
            "status": status,
            "evidence": items,
            **extra,
        }
        path = "/journalist/news" if kind == "News" else "/journalist/articles"
        res = api.post(path, payload)
        if res:
            st.success("Story saved to your desk.")
            for k in ("jc_validation", "jc_recommendations", "jc_duplicate_flag", "jc_fp"):
                st.session_state.pop(k, None)
