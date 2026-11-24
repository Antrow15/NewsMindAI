"""CAE desk — ML sentence adaptation queue + review."""

from __future__ import annotations

import streamlit as st

from core import api, config, ui

_RECENT = "adapt_recent"


def render_dashboard() -> None:
    ui.header(
        "Dashboard",
        "Adaptation desk load — you create platform drafts; the editor approves them.",
    )
    queue = api.get("/cae/queue", limit=50, _cache=False)
    recent = api.get("/cae/requests", limit=12, _cache=False)
    if not queue and not recent:
        return

    pending = (queue or {}).get("pending_count") or 0
    manual = (queue or {}).get("manual_count") or 0
    total = (queue or {}).get("total") or 0
    reqs = (recent or {}).get("requests") or []

    ui.kpi_row(
        {
            "Pending review": pending,
            "Needs manual": manual,
            "Open drafts": total,
            "Recent requests": len(reqs),
        },
        hints={
            "Pending review": "PENDING_REVIEW",
            "Needs manual": "Fact-check flags failed",
            "Open drafts": "In the review queue",
            "Recent requests": "Latest adaptation jobs",
        },
        icons={
            "Pending review": "⏳",
            "Needs manual": "⚠",
            "Open drafts": "📄",
            "Recent requests": "🔁",
        },
    )
    left, right = st.columns([1.15, 1])
    with left:
        ui.bar(
            {
                "Pending": pending,
                "Manual": manual,
                "Open drafts": total,
                "Requests": len(reqs),
            },
            caption="Adaptation desk load",
        )
    with right:
        denom = max(total, 1)
        ui.score_meters(
            {
                "Pending share": round(100 * pending / denom),
                "Manual share": round(100 * manual / denom),
                "Queue pressure": min(100, round(20 * total)),
            },
            scale="100",
        )

    items = (queue or {}).get("items") or []
    if not items:
        st.caption("No open drafts. Create an adaptation from an approved story.")
    else:
        ui.section("Awaiting editor approval")
        st.caption(
            "These drafts sit with the editor for approve/reject. "
            "Open **My drafts** to regenerate or finalize after feedback."
        )
        for row in items:
            platform = str(row.get("platform") or "").replace("_", " ").title()
            ui.card(
                row.get("adapted_title") or row.get("original_title") or "Draft",
                status=row.get("draft_status"),
                meta=[
                    f"{platform} · v{row.get('version_number') or 1}",
                    f"Model · {row.get('model_version') or '—'}",
                    f"From · {row.get('original_title') or '—'}",
                ],
                body=(row.get("adapted_content") or "")[:220],
            )

    if reqs:
        ui.section("Recent requests")
        for r in reqs:
            ui.card(
                r.get("original_title") or f"Request {r.get('id')}",
                status=r.get("status"),
                meta=[
                    f"Drafts · {r.get('draft_count') or 0}",
                    f"Still open · {r.get('pending_count') or 0}",
                ],
                body=(r.get("original_content") or "")[:160],
            )
            rid = int(r.get("id") or 0)
            if rid and st.button("Open drafts", key=f"adapt_open_{rid}"):
                st.session_state["adapt_current"] = rid
                st.session_state.setdefault(_RECENT, [])
                if rid not in st.session_state[_RECENT]:
                    st.session_state[_RECENT] = [rid, *st.session_state[_RECENT]][:10]
                st.info("Open **My drafts** in the sidebar.")


def _show_adaptation_result(res: dict) -> None:
    """Inline model output after a successful run."""
    rid = int(res.get("id") or 0)
    drafts = res.get("drafts") or []
    st.session_state.setdefault(_RECENT, [])
    if rid:
        st.session_state[_RECENT] = [rid, *[x for x in st.session_state[_RECENT] if x != rid]][:10]
        st.session_state["adapt_current"] = rid
        st.session_state["adapt_last_result"] = res

    st.success(
        f"Model finished — {len(drafts)} platform draft(s) for request #{rid or '—'}."
    )
    ui.section("Model output")
    if not drafts:
        st.caption("No drafts returned.")
        return
    tabs = st.tabs(
        [
            f"{str(d.get('platform') or 'Platform').replace('_', ' ').title()} · v{d.get('version_number') or 1}"
            for d in drafts
        ]
    )
    for tab, draft in zip(tabs, drafts):
        with tab:
            params = draft.get("generation_parameters") or {}
            flags = draft.get("validation_flags") or {}
            ui.card(
                draft.get("adapted_title") or "Adapted draft",
                status=draft.get("status"),
                meta=[
                    f"Model · {draft.get('model_version') or '—'}",
                    f"Threshold · {params.get('threshold', '—')}",
                    f"Sentences · {params.get('selected_sentence_indexes') or '—'}",
                ],
                body=draft.get("adapted_content"),
            )
            passed = bool(flags.get("passed", True)) if isinstance(flags, dict) else True
            sent = params.get("selected_sentence_indexes") or []
            sent_n = len(sent) if isinstance(sent, list) else 0
            ui.score_meters(
                {
                    "Threshold": params.get("threshold"),
                    "Sentences kept": min(100, sent_n * 20) if sent_n else None,
                    "Fact-check": 100 if passed else 25,
                }
            )
            if isinstance(flags, dict) and not flags.get("passed", True):
                st.warning(f"Validation flags: {flags}")


def render_new() -> None:
    ui.header(
        "New adaptation",
        "Select an approved desk story, review it, then run the sentence model per platform.",
    )

    sources = api.get("/cae/sources", limit=50, _cache=False) or {}
    articles = list(sources.get("articles") or [])
    by_id: dict[int, dict] = {}
    labels: list[str] = []
    label_to_id: dict[str, int] = {}
    for a in articles:
        cid = int(a.get("content_id") or 0)
        if not cid:
            continue
        by_id[cid] = a
        label = f"#{cid} — {a.get('title') or 'Untitled'} ({(a.get('status') or '').title()})"
        labels.append(label)
        label_to_id[label] = cid

    mode = st.radio(
        "Source",
        ["Desk story", "Paste manually"],
        horizontal=True,
        key="adapt_src_mode",
        disabled=not labels,
        help="Only approved desk stories — not drafts, queue, or already published.",
    )
    if not labels:
        st.info(
            "No approved stories ready to adapt yet. "
            "Approve a story in the editor desk, or paste content below."
        )
        mode = "Paste manually"

    title = ""
    content = ""
    selected: dict | None = None

    if mode == "Desk story" and labels:
        pick = st.selectbox("Story", labels, key="adapt_src_pick")
        selected = by_id.get(label_to_id.get(pick, 0))
        if selected:
            title = str(selected.get("title") or "")
            content = str(selected.get("body") or selected.get("summary") or "")
            ui.section("Selected story")
            ui.card(
                title or "Story",
                status=selected.get("status"),
                meta=[
                    f"Content · #{selected.get('content_id')}",
                    f"Updated · {selected.get('updated_at') or '—'}",
                ],
                body=selected.get("summary") or (content[:220] + ("…" if len(content) > 220 else "")),
            )
            with st.expander("Full article body", expanded=True):
                st.markdown(content or "_No body._")
    else:
        ui.section("Paste story")
        title = st.text_input("Title", key="adapt_paste_title", help="Minimum 5 characters.")
        content = st.text_area(
            "Article body",
            key="adapt_paste_body",
            height=220,
            help="Minimum 20 characters.",
        )

    ui.section("Run model")
    platforms = st.multiselect(
        "Target platforms",
        config.PLATFORMS,
        default=config.PLATFORMS[:2],
        key="adapt_platforms",
        help="Each platform gets its own adapted draft.",
    )
    can_run = bool(title.strip()) and len(content.strip()) >= 20 and bool(platforms)
    ran_now = False
    if st.button(
        "Run adaptation model",
        type="primary",
        key="adapt_run",
        disabled=not can_run,
    ):
        with st.spinner("Running sentence model…"):
            res = api.post(
                "/cae/adaptations",
                {
                    "original_title": title.strip(),
                    "original_content": content.strip(),
                    "target_platforms": platforms,
                },
            )
        if res:
            ran_now = True
            _show_adaptation_result(res)

    last = st.session_state.get("adapt_last_result")
    if last and not ran_now:
        with st.expander(
            f"Last model output · request #{last.get('id')}",
            expanded=True,
        ):
            drafts = last.get("drafts") or []
            if not drafts:
                st.caption("No drafts stored.")
            else:
                for d in drafts:
                    ui.card(
                        d.get("adapted_title") or d.get("platform"),
                        status=d.get("status"),
                        meta=[
                            str(d.get("platform") or "").replace("_", " ").title(),
                            f"Model · {d.get('model_version') or '—'}",
                        ],
                        body=d.get("adapted_content"),
                    )


def render_review() -> None:
    ui.header(
        "My drafts",
        "Regenerate or finalize after the editor reviews. Approve/reject is on the editor desk.",
    )
    recent = st.session_state.get(_RECENT, [])
    current = st.session_state.get("adapt_current")
    if current and current not in recent:
        recent = [current, *recent]

    listed = api.get("/cae/requests", limit=20) or {}
    for r in listed.get("requests") or []:
        rid = int(r.get("id") or 0)
        if rid and rid not in recent:
            recent.append(rid)

    options = {f"Request #{i}": i for i in recent if i}
    manual = st.number_input("Or open by request number", 0, step=1, key="adapt_manual")
    request_id = int(manual) or (list(options.values())[0] if options else None)
    if options:
        pick = st.selectbox("Request", list(options), key="adapt_sel")
        if not manual:
            request_id = options[pick]
    if not request_id:
        st.caption("Create an adaptation first, or enter a request number.")
        return

    res = api.get(f"/cae/adaptations/{request_id}")
    if not res:
        return
    ui.card(
        res.get("original_title") or "Adaptation",
        status=res.get("status"),
        body=res.get("original_content"),
    )
    drafts = res.get("drafts") or []
    if not drafts:
        st.caption("No drafts.")
        return
    tabs = st.tabs(
        [f"{d['platform'].replace('_', ' ').title()} · v{d['version_number']}" for d in drafts]
    )
    for tab, draft in zip(tabs, drafts):
        with tab:
            _draft_panel(draft)


def _draft_panel(d: dict) -> None:
    did = d["id"]
    params = d.get("generation_parameters") or {}
    ui.card(
        d.get("adapted_title") or "Draft",
        status=d.get("status"),
        meta=[
            f"Model · {d.get('model_version') or '—'}",
            f"Threshold · {params.get('threshold', '—')}",
            f"Sentences · {params.get('selected_sentence_indexes') or '—'}",
        ],
        body=d.get("adapted_content"),
    )
    sent = params.get("selected_sentence_indexes") or []
    sent_n = len(sent) if isinstance(sent, list) else 0
    flags_all = d.get("validation_flags") or {}
    passed = bool(flags_all.get("passed", True)) if isinstance(flags_all, dict) else True
    left, right = st.columns(2)
    with left:
        ui.score_meters(
            {
                "Threshold": params.get("threshold"),
                "Sentences kept": min(100, sent_n * 20) if sent_n else None,
                "Fact-check": 100 if passed else 25,
            }
        )
    with right:
        ui.scores_chart(
            {
                "Threshold": params.get("threshold"),
                "Sentences": min(1.0, sent_n / 5.0) if sent_n else 0,
                "Fact-check": 1.0 if passed else 0.25,
            },
            title="Adaptation model signals",
            height=160,
        )
    flags = {k: v for k, v in (flags_all.items() if isinstance(flags_all, dict) else []) if v and k != "passed"}
    if flags:
        st.warning(f"Validation flags: {flags}")

    remarks = st.text_input(
        "Remarks",
        key=f"rm{did}",
        help="Required for regenerate. Editor handles approve/reject.",
    )
    st.caption("Editor signs off on adapted drafts. You can regenerate or finalize here.")
    a, b = st.columns(2)
    if a.button("Regenerate", key=f"rg{did}", type="primary", width="stretch"):
        api.post(
            f"/cae/adaptation-drafts/{did}/regenerate",
            {"remarks": remarks},
            success="New version generated.",
        )
    if b.button("History", key=f"vs{did}", width="stretch"):
        ui.table(api.get(f"/cae/adaptation-drafts/{did}/versions"), key=f"vt{did}")

    with st.expander("Edit & finalize"):
        ft = st.text_input("Final title", d["adapted_title"], key=f"ft{did}")
        fc = st.text_area("Final content", d["adapted_content"], height=160, key=f"fc{did}")
        if st.button("Save final version", key=f"fn{did}"):
            api.put(
                f"/cae/adaptation-drafts/{did}/final",
                {"final_title": ft, "final_content": fc, "remarks": remarks or None},
                success="Final version saved.",
            )


def render() -> None:
    render_dashboard()
