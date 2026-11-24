"""Editor desk — ML urgency queue + pitch/content approval + assign."""

from __future__ import annotations

from datetime import datetime, timedelta

import streamlit as st

from core import api, config, ui


def render_dashboard() -> None:
    """Read-only desk health — no approve buttons (those live on Approval queue / Adapted)."""
    ui.header(
        "Dashboard",
        "At-a-glance desk health. Take action on Approval queue, Adapted, or Assign.",
    )
    res = api.get("/editor/queue", _cache=False) or {}
    adapt = api.get("/cae/queue", limit=50, _cache=False, quiet=True) or {}

    pitches = int(res.get("pitch_count") or 0)
    content = int(res.get("content_count") or 0)
    tasks = list(res.get("tasks") or [])
    urgent = sum(
        1
        for t in tasks
        if str(t.get("urgency") or "").lower() in {"urgent", "high"}
    )
    pending_adapt = int(adapt.get("pending_count") or 0)
    manual_adapt = int(adapt.get("manual_count") or 0)
    adapt_total = int(adapt.get("total") or 0)
    queue_load = pitches + content

    ui.kpi_row(
        {
            "Queue load": queue_load,
            "High / urgent": urgent,
            "Adapted waiting": adapt_total,
            "Needs manual check": manual_adapt,
        },
        hints={
            "Queue load": "Pitches + stories open",
            "High / urgent": "ML-ranked priority",
            "Adapted waiting": "Open Adapted page",
            "Needs manual check": "Fact-check flags",
        },
        icons={
            "Queue load": "📥",
            "High / urgent": "⚡",
            "Adapted waiting": "✅",
            "Needs manual check": "⚠",
        },
    )

    left, right = st.columns([1.15, 1])
    with left:
        ui.bar(
            {
                "Pitches": pitches,
                "Stories": content,
                "Adapted pending": pending_adapt,
                "Adapted manual": manual_adapt,
            },
            caption="Where work is sitting",
        )
    with right:
        ui.scores_chart(
            {
                "Pitches": pitches / max(queue_load, 1),
                "Stories": content / max(queue_load, 1),
                "Urgency": min(1.0, urgent / max(queue_load, 1)),
                "Adapted": min(1.0, adapt_total / max(queue_load + adapt_total, 1)),
            },
            title="Desk mix (normalized)",
            height=180,
        )

    ui.section("Where to work")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.card(
            "Approval queue",
            meta=[f"{queue_load} open"],
            body="Approve / reject / rework pitches and stories.",
        )
    with c2:
        ui.card(
            "Create",
            meta=["News or article"],
            body="Draft a piece and assign a journalist in one step.",
        )
    with c3:
        ui.card(
            "Adapted",
            meta=[f"{adapt_total} draft(s)"],
            body="Sign off on CAE platform adaptations.",
        )
    with c4:
        ui.card(
            "Assign",
            meta=["Existing work"],
            body="Match pitches or stories to journalists by specialty.",
        )
    st.caption(
        "This page is metrics only — open **Approval queue** to decide on items, "
        "or **Create** to write and assign."
    )


def render_queue() -> None:
    """Action workbench — approve / reject / rework pitches and stories."""
    ui.header(
        "Approval queue",
        "Work the list: approve, reject, or send rework. Ranked by AIA importance and queue urgency.",
    )
    res = api.get("/editor/queue", _cache=False)
    if not res:
        return

    pitches = int(res.get("pitch_count") or 0)
    content = int(res.get("content_count") or 0)
    tasks = list(res.get("tasks") or [])

    st.caption(f"{pitches} pitch(es) · {content} stor(ies) · act below")

    filter_kind = st.radio(
        "Show",
        ["All", "Pitches only", "Content only"],
        horizontal=True,
        key="e_q_filter",
    )
    if filter_kind == "Pitches only":
        tasks = [t for t in tasks if t.get("task_type") == "pitch"]
    elif filter_kind == "Content only":
        tasks = [t for t in tasks if t.get("task_type") == "content"]

    if not tasks:
        st.caption("Queue is clear for this filter.")
        return

    ui.section("Decide now")
    for t in tasks:
        _queue_task(t)


def render_adaptations() -> None:
    """Editor-only sign-off on CAE platform drafts."""
    ui.header(
        "Adapted content",
        "Approve or reject platform drafts from the Adaptation desk. Adapters run the model; you sign off.",
    )
    queue = api.get("/cae/queue", limit=50, _cache=False)
    if not queue:
        return
    pending = queue.get("pending_count") or 0
    manual = queue.get("manual_count") or 0
    total = queue.get("total") or 0
    ui.kpi_row(
        {
            "Pending review": pending,
            "Needs manual": manual,
            "Open drafts": total,
        },
        hints={
            "Pending review": "PENDING_REVIEW",
            "Needs manual": "Fact-check flags",
            "Open drafts": "Waiting on editor",
        },
        icons={
            "Pending review": "⏳",
            "Needs manual": "⚠",
            "Open drafts": "📄",
        },
    )
    items = queue.get("items") or []
    if not items:
        st.caption("No adapted drafts waiting for editorial approval.")
        return
    ui.section("Needs your decision")
    for row in items:
        _adaptation_review_row(row)


def _adaptation_review_row(row: dict) -> None:
    did = int(row.get("draft_id") or 0)
    platform = str(row.get("platform") or "").replace("_", " ").title()
    flags = row.get("validation_flags") or {}
    if isinstance(flags, str):
        flags = {}
    params = row.get("generation_parameters") or {}
    if isinstance(params, str):
        params = {}

    ui.card(
        row.get("adapted_title") or row.get("original_title") or "Draft",
        status=row.get("draft_status"),
        meta=[
            f"{platform} · v{row.get('version_number') or 1}",
            f"Model · {row.get('model_version') or '—'}",
            f"Sentences · {params.get('selected_sentence_indexes') or '—'}",
            f"From · {row.get('original_title') or '—'}",
        ],
        body=row.get("adapted_content"),
    )
    thresh = params.get("threshold")
    sent = params.get("selected_sentence_indexes") or []
    sent_n = len(sent) if isinstance(sent, list) else 0
    ui.score_meters(
        {
            "Model threshold": thresh,
            "Sentences kept": min(100, sent_n * 20) if sent_n else None,
            "Fact-check": 100 if flags.get("passed", True) else 25,
        }
    )
    if flags and not flags.get("passed", True):
        st.warning(f"Validation flags: {flags}")

    remarks = st.text_input(
        "Remarks",
        key=f"e_ad_rm_{did}",
        placeholder="Required for reject",
    )
    a, b = st.columns(2)
    if a.button(
        "Approve adapted",
        key=f"e_ad_ap_{did}",
        type="primary",
        width="stretch",
        disabled=not did,
    ):
        api.post(
            f"/cae/adaptation-drafts/{did}/approve",
            {"remarks": remarks or None},
            success="Adapted draft approved.",
        )
        st.rerun()
    if b.button(
        "Reject adapted",
        key=f"e_ad_rj_{did}",
        width="stretch",
        disabled=not did,
    ):
        api.post(
            f"/cae/adaptation-drafts/{did}/reject",
            {"remarks": remarks},
            success="Adapted draft rejected.",
        )
        st.rerun()
    st.divider()


def _queue_task(t: dict) -> None:
    kind = str(t.get("task_type") or "item")
    item = t.get("item") or {}
    urgency = str(t.get("urgency") or "medium")
    urgency_kind = str(t.get("urgency_kind") or "")
    label = (
        "Pitch importance (AIA)"
        if urgency_kind == "pitch_importance"
        else "Queue urgency (ML)"
        if urgency_kind == "editor_queue_urgency"
        else "Priority"
    )
    conf = t.get("confidence")
    source = t.get("source") or item.get("urgency_source") or ""

    meta = [
        f"{kind.title()} · {(t.get('status') or '').title()}",
        f"{label} · {urgency.title()}"
        + (f" · {float(conf):.0%} conf" if isinstance(conf, (int, float)) else "")
        + (f" · {source}" if source else ""),
        f"From · {t.get('created_by_desk') or t.get('source_type') or '—'}",
    ]

    ui.card(
        t.get("title") or item.get("title") or "Untitled",
        status=urgency,
        meta=meta,
        body=t.get("summary") or item.get("summary"),
    )
    if kind == "pitch":
        ui.score_meters(
            {
                "Trend": item.get("trend_score"),
                "Interest": item.get("audience_interest_score"),
                "Coverage gap": item.get("coverage_gap_score"),
                "Importance": item.get("pitch_importance") or t.get("confidence"),
            },
            scale="auto",
        )
    else:
        ui.score_meters(
            {
                "Queue urgency": (
                    {"low": 25, "medium": 55, "high": 80, "urgent": 95}.get(
                        str(urgency).lower(), 50
                    )
                ),
                "Model confidence": conf if isinstance(conf, (int, float)) else None,
            },
            scale="auto",
        )

    if kind == "pitch":
        pid = int(t.get("task_id") or item.get("story_pitch_id") or 0)
        remarks = st.text_input("Reject remarks", key=f"e_q_pr_{pid}", placeholder="Optional")
        a, b, c = st.columns(3)
        if a.button("Approve pitch", key=f"e_q_pa_{pid}", type="primary", width="stretch", disabled=not pid):
            api.put(f"/editor/pitches/{pid}/approve", success="Pitch approved.")
            st.rerun()
        if b.button("Reject pitch", key=f"e_q_pj_{pid}", width="stretch", disabled=not pid):
            api.put(f"/editor/pitches/{pid}/reject", {"remarks": remarks}, success="Pitch rejected.")
            st.rerun()
        if c.button("Assign…", key=f"e_q_as_{pid}", width="stretch", disabled=not pid):
            st.session_state["e_assign_pitch_id"] = pid
            st.info("Open **Assign** in the sidebar — pitch is pre-selected.")
    else:
        cid = int(t.get("task_id") or item.get("content_id") or 0)
        remarks = st.text_input("Remarks", key=f"e_q_cr_{cid}", placeholder="Required for rework/reject")
        a, b, c = st.columns(3)
        if a.button("Approve story", key=f"e_q_ca_{cid}", type="primary", width="stretch", disabled=not cid):
            api.put(f"/editor/content/{cid}/approve", success="Story approved.")
            st.rerun()
        if b.button("Rework", key=f"e_q_cw_{cid}", width="stretch", disabled=not cid):
            api.put(f"/editor/content/{cid}/rework", {"remarks": remarks}, success="Sent for rework.")
            st.rerun()
        if c.button("Reject", key=f"e_q_cj_{cid}", width="stretch", disabled=not cid):
            api.put(f"/editor/content/{cid}/reject", {"remarks": remarks}, success="Rejected.")
            st.rerun()
    st.divider()


def render_pitches() -> None:
    ui.header("Pitches", "Browse by status · duplicates check uses similarity ML.")
    status = st.selectbox("Status", config.PITCH_STATUSES, key="e_pst")
    pitches = ui.as_rows(api.get("/editor/pitches", status=status), "pitches")
    if not pitches:
        st.caption("No pitches in this status.")
        return

    with st.expander("Check near-duplicate pitches"):
        probe = st.text_input("Title to compare", key="e_dup_t")
        if st.button("Find duplicates", key="e_dup_go"):
            res = api.post("/editor/pitches/duplicates", {"title": probe or ""})
            if res:
                ui.table(res.get("pairs") or res.get("matches") or [], key="e_dup_tbl", empty="No near-duplicates.")

    labels = {f"{p.get('title') or 'Pitch'} · {(p.get('status') or '').title()}": p for p in pitches}
    pick = st.selectbox("Select pitch", list(labels), key="e_ppick")
    pitch = labels[pick]
    pid = int(pitch.get("story_pitch_id") or pitch.get("id") or 0)
    ui.card(
        pitch.get("title") or "Pitch",
        status=pitch.get("priority") or pitch.get("status"),
        meta=[
            f"Priority · {pitch.get('priority') or '—'}",
            f"Source · {pitch.get('source_type') or '—'} · {pitch.get('created_by_desk') or ''}",
        ],
        body=pitch.get("summary"),
    )
    c_left, c_right = st.columns([1.1, 1])
    with c_left:
        ui.score_meters(
            {
                "Trend": pitch.get("trend_score"),
                "Interest": pitch.get("audience_interest_score"),
                "Coverage gap": pitch.get("coverage_gap_score"),
                "Importance": pitch.get("pitch_importance"),
            }
        )
    with c_right:
        ui.scores_chart(
            {
                "Trend": pitch.get("trend_score"),
                "Interest": pitch.get("audience_interest_score"),
                "Gap": pitch.get("coverage_gap_score"),
                "Importance": pitch.get("pitch_importance"),
            },
            title="AIA score profile",
            height=180,
        )
    remarks = st.text_input("Remarks (reject)", key="e_prem")
    a, b = st.columns(2)
    if a.button("Approve", key="e_pa", type="primary", width="stretch", disabled=not pid):
        api.put(f"/editor/pitches/{pid}/approve", success="Pitch approved.")
    if b.button("Reject", key="e_pr", width="stretch", disabled=not pid):
        api.put(f"/editor/pitches/{pid}/reject", {"remarks": remarks}, success="Pitch rejected.")


def render_content() -> None:
    ui.header("Content", "Submitted stories scored by the editor-queue urgency model.")
    status = st.selectbox("Status", config.CONTENT_STATUSES, index=1, key="e_cst")
    items = ui.as_rows(api.get("/editor/content", status=status), "items")
    if not items:
        st.caption("Nothing in this status.")
        return

    with st.expander("Score a headline with the urgency model"):
        ht = st.text_input("Headline", key="e_score_t")
        hs = st.text_input("Summary", key="e_score_s")
        if st.button("Score urgency", key="e_score_go"):
            scored = api.post("/editor/queue/score", {"title": ht, "summary": hs})
            if scored:
                ui.kpi_row(
                    {
                        "Urgency": scored.get("urgency"),
                        "Source": scored.get("source"),
                        "Confidence": (
                            f"{float(scored['confidence']):.0%}"
                            if isinstance(scored.get("confidence"), (int, float))
                            else "—"
                        ),
                    }
                )

    labels = {
        f"{r.get('title') or 'Story'} · "
        f"{(r.get('editor_queue_urgency') or r.get('status') or '').title()}": r
        for r in items
    }
    pick = st.selectbox("Select story", list(labels), key="e_cpick")
    row = labels[pick]
    cid = int(row.get("content_id") or row.get("id") or 0)
    ui.card(
        row.get("title") or "Story",
        status=row.get("editor_queue_urgency") or row.get("status"),
        meta=[
            f"Status · {row.get('status') or '—'}",
            f"Source · {row.get('urgency_source') or 'editor_queue_urgency'}",
        ],
        body=row.get("summary"),
    )
    urg = str(row.get("editor_queue_urgency") or "").lower()
    ui.score_meters(
        {
            "Queue urgency": {"low": 25, "medium": 55, "high": 80, "urgent": 95}.get(urg, 50),
            "Confidence": row.get("urgency_confidence"),
        }
    )
    remarks = st.text_input("Remarks", key="e_crem")
    a, b, c = st.columns(3)
    if a.button("Approve", key="e_ca", type="primary", width="stretch", disabled=not cid):
        api.put(f"/editor/content/{cid}/approve", success="Approved.")
    if b.button("Rework", key="e_cw", width="stretch", disabled=not cid):
        api.put(f"/editor/content/{cid}/rework", {"remarks": remarks}, success="Sent for rework.")
    if c.button("Reject", key="e_cr", width="stretch", disabled=not cid):
        api.put(f"/editor/content/{cid}/reject", {"remarks": remarks}, success="Rejected.")


def render_create() -> None:
    """Editor creates news/article and assigns a journalist in one step."""
    ui.header(
        "Create",
        "Write a news item or article, pick a journalist, and assign it to their desk.",
    )
    kind = st.radio("Type", ["News", "Article"], horizontal=True, key="e_cr_kind")
    title = st.text_input("Title", key="e_cr_title", help="Minimum 5 characters.")
    body = st.text_area("Body", height=200, key="e_cr_body", help="Minimum 40 characters.")
    summary = st.text_area("Summary", height=70, key="e_cr_summary")

    extra: dict = {}
    if kind == "News":
        c1, c2, c3 = st.columns(3)
        extra["event_type"] = c1.text_input("Event type", "city", key="e_cr_etype")
        extra["event_location"] = c2.text_input("Location", key="e_cr_eloc")
        extra["severity"] = c3.selectbox("Severity", config.SEVERITIES, index=1, key="e_cr_sev")
        extra["breaking"] = st.checkbox("Breaking news", key="e_cr_brk")
    else:
        c1, c2 = st.columns(2)
        extra["article_type"] = c1.selectbox("Article type", config.ARTICLE_TYPES, key="e_cr_atype")
        extra["read_time"] = int(c2.number_input("Read time (min)", 1, 120, 5, key="e_cr_rtime"))

    ui.section("Assign journalist")
    topic = st.text_input(
        "Topic for matching",
        value=title or "",
        key="e_cr_topic",
        help="Used to rank journalists by specialty.",
    )
    if st.button("Find top 3 journalists", key="e_cr_find", type="secondary"):
        res = api.post(
            "/editor/assign/suggest",
            {
                "topic": (topic or title or "general").strip(),
                "title": (title or topic or "").strip(),
                "limit": 3,
            },
        )
        if res:
            st.session_state["e_cr_matches"] = res.get("suggestions") or []
            scored = int(res.get("scored_count") or 0)
            if scored == 0:
                st.warning("No active journalist desks found to rank.")
            else:
                st.success(f"Ranked {scored} · showing top {len(res.get('suggestions') or [])}.")

    journalist_user_id = ui.pick_top_journalist(
        st.session_state.get("e_cr_matches") or [],
        key="e_cr_jpick",
    )
    due = st.date_input("Deadline date", value=datetime.utcnow().date() + timedelta(days=3), key="e_cr_due")
    due_time = st.time_input(
        "Deadline time",
        value=datetime.strptime("17:00", "%H:%M").time(),
        key="e_cr_due_t",
    )
    note = st.text_input("Note to journalist", key="e_cr_note")

    can_save = (
        bool((title or "").strip())
        and len((body or "").strip()) >= 40
        and bool(journalist_user_id)
    )
    if st.button("Create & assign", type="primary", key="e_cr_go", disabled=not can_save):
        payload = {
            "kind": kind.lower(),
            "title": title.strip(),
            "body": body.strip(),
            "summary": (summary or "").strip(),
            "assignee_user_id": journalist_user_id,
            "note": note or "",
            "due_at": datetime.combine(due, due_time).isoformat(),
            "evidence_title": f"Editor brief · {title.strip()[:80]}",
            **extra,
        }
        res = api.post(
            "/editor/content/create-assign",
            payload,
            success="Created and assigned to journalist.",
        )
        if res:
            ui.card(
                title.strip(),
                status="draft",
                meta=[
                    f"Content · #{res.get('content_id')}",
                    f"Kind · {res.get('kind')}",
                    f"Journalist user · {res.get('assignee_user_id')}",
                    f"Assigner · {res.get('assigner') or 'Editor'}",
                ],
                body=(summary or body)[:220],
            )


def render_assign() -> None:
    ui.header(
        "Assign",
        "Shortlist the top 3 journalists by specialty fit and open desk workload.",
    )
    mode = st.radio("Assign from", ["Story pitch", "Existing content"], horizontal=True)

    pitch = None
    pid = 0
    row = None
    cid = 0
    default_topic = ""

    if mode == "Story pitch":
        pitches = ui.as_rows(api.get("/editor/pitches", status="approved"), "pitches")
        if not pitches:
            pitches = ui.as_rows(api.get("/editor/pitches", status="submitted"), "pitches")
        if not pitches:
            st.caption("No pitches available.")
            return
        plabels = {p.get("title") or "Pitch": p for p in pitches}
        preselect = st.session_state.pop("e_assign_pitch_id", None)
        default_ix = 0
        if preselect:
            for i, (_label, p) in enumerate(plabels.items()):
                if int(p.get("story_pitch_id") or p.get("id") or 0) == int(preselect):
                    default_ix = i
                    break
        keys = list(plabels)
        ppick = st.selectbox("Pitch", keys, index=min(default_ix, len(keys) - 1), key="e_apitch")
        pitch = plabels[ppick]
        pid = int(pitch.get("story_pitch_id") or pitch.get("id") or 0)
        default_topic = str(pitch.get("title") or pitch.get("summary") or "")
    else:
        items = ui.as_rows(api.get("/editor/content", status="submitted"), "items")
        if not items:
            st.caption("No submitted content.")
            return
        clabels = {r.get("title") or "Story": r for r in items}
        cpick = st.selectbox("Story", list(clabels), key="e_acontent")
        row = clabels[cpick]
        cid = int(row.get("content_id") or row.get("id") or 0)
        default_topic = str(row.get("title") or row.get("summary") or "")

    tcol, bcol = st.columns([3.2, 1.2])
    with tcol:
        if "e_topic" not in st.session_state:
            st.session_state["e_topic"] = default_topic
        topic = st.text_input(
            "Topic for matching",
            key="e_topic",
            help="Edit freely — specialty matching uses this text.",
        )
    with bcol:
        st.write("")  # align with input
        st.write("")
        if st.button("Use story title", key="e_topic_fill", width="stretch"):
            st.session_state["e_topic"] = default_topic
            st.rerun()

    if st.button("Find top 3 journalists", type="primary"):
        res = api.post(
            "/editor/assign/suggest",
            {
                "topic": (topic or default_topic or "general").strip(),
                "title": (topic or default_topic or "").strip(),
                "limit": 3,
            },
        )
        if res:
            st.session_state["e_matches"] = res.get("suggestions") or []
            scored = int(res.get("scored_count") or 0)
            shown = len(res.get("suggestions") or [])
            if scored == 0:
                st.warning("No active journalist desks found to rank.")
            else:
                st.success(f"Ranked {scored} journalist{'s' if scored != 1 else ''} · showing top {shown}.")

    journalist_user_id = ui.pick_top_journalist(
        st.session_state.get("e_matches") or [],
        key="e_jpick",
    )

    due = st.date_input("Deadline date", value=datetime.utcnow().date() + timedelta(days=3))
    due_time = st.time_input("Deadline time", value=datetime.strptime("17:00", "%H:%M").time())
    due_at = datetime.combine(due, due_time).isoformat()
    note = st.text_input("Note to journalist", key="e_as_note")

    if mode == "Story pitch":
        if st.button("Assign pitch", type="primary", disabled=not (pid and journalist_user_id)):
            api.post(
                f"/editor/pitches/{pid}/assign",
                {
                    "assignee_user_id": journalist_user_id,
                    "note": note,
                    "due_at": due_at,
                    "auto_approve": True,
                },
                success="Pitch assigned — journalist notified.",
            )
    else:
        if st.button("Assign story", type="primary", disabled=not (cid and journalist_user_id)):
            api.put(
                f"/editor/content/{cid}/assign",
                {
                    "assignee_user_id": journalist_user_id,
                    "note": note,
                    "due_at": due_at,
                },
                success="Story assigned — journalist notified.",
            )


def render_tools() -> None:
    render_assign()


def render() -> None:
    render_dashboard()
