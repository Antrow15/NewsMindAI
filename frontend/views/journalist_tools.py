"""Journalist — AI assist (validate, related, credibility, duplicates)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import api, ui


def render() -> None:
    ui.header("AI assist", "Validate drafts, find related content, assess credibility, scan duplicates.")
    val, rel, cred, dup = st.tabs(["Validate", "Related", "Credibility", "Duplicates"])

    with val:
        title = st.text_input("Title", key="jt_v_t")
        text = st.text_area("Text", key="jt_v_x", height=140)
        if st.button("Validate", key="jt_v_b"):
            res = api.post("/journalist/validate", {"title": title, "text": text})
            if res:
                (st.success if res.get("ok") else st.error)(
                    "Valid" if res.get("ok") else "Issues found"
                )
                for err in res.get("errors") or []:
                    st.write("•", err)
                ui.metrics(
                    {
                        "Relevancy": res.get("relevancy"),
                        "Score": res.get("relevancy_score"),
                    }
                )
                ui.table(res.get("relevancy_matches"), key="jt_v_m")

    with rel:
        title = st.text_input("Title", key="jt_r_t")
        text = st.text_area("Text", key="jt_r_x", height=140)
        if st.button("Find related", key="jt_r_b"):
            res = api.post("/journalist/related-content", {"title": title, "text": text})
            if res:
                ui.metrics(
                    {
                        "Relevancy": res.get("relevancy"),
                        "Best score": round(res.get("best_score", 0), 3),
                        "Corpus size": res.get("corpus_size"),
                    }
                )
                ui.table(res.get("matches"), key="jt_r_m")

    with cred:
        cid = st.number_input("Content ID", 0, step=1, key="jt_c_id")
        if st.button("Assess", key="jt_c_b", disabled=not cid):
            res = api.post("/journalist/credibility", {"content_id": int(cid)})
            if res:
                ui.metrics({"Evidence items": res.get("evidence_count")})
                st.write(res.get("summary") or "")
                ui.table(res.get("claims"), key="jt_claims")

    with dup:
        docs = st.data_editor(
            pd.DataFrame({"id": [1, 2], "title": ["", ""], "text": ["", ""]}),
            num_rows="dynamic",
            hide_index=True,
            key="jt_d_docs",
        )
        c1, c2 = st.columns(2)
        threshold = c1.slider("Threshold", 0.0, 1.0, 0.5, 0.05, key="jt_d_th")
        limit = c2.number_input("Max pairs", 1, 100, 20, key="jt_d_lim")
        if st.button("Find duplicates", key="jt_d_b"):
            items = [
                {
                    "id": int(r["id"]),
                    "title": str(r["title"]),
                    "text": str(r["text"]),
                }
                for r in docs.dropna(subset=["id"]).to_dict("records")
                if str(r["text"]).strip()
            ]
            res = api.post(
                "/journalist/duplicates",
                {"documents": items, "threshold": threshold, "limit": int(limit)},
            )
            if res:
                ui.table(res.get("pairs"), key="jt_d_p", empty="No duplicate pairs found.")
