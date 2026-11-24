from __future__ import annotations

import streamlit as st

from core import api, config, session, ui


def _quiet(path: str, **params):
    return api.get(path, _cache=False, quiet=True, **params) or {}


def render_dashboard() -> None:
    ui.header("Dashboard", "Newsroom control center — users, pipeline, and desk health.")
    user = session.user()

    # Optional desk snapshots — quiet so one missing route does not red-banner the page
    editor_q = _quiet("/editor/queue")
    manager = _quiet("/manager/overview")
    adapt_q = _quiet("/cae/queue", limit=50)
    pub = _quiet("/publisher/analytics")
    raw = _quiet("/admin/raw-ingest", limit=5)

    editor_load = (editor_q.get("pitch_count") or 0) + (editor_q.get("content_count") or 0)
    submitted = manager.get("submitted_pitches") or 0
    adapt_open = adapt_q.get("total") or 0
    published = pub.get("published") or 0
    ui.kpi_row(
        {
            "Editor queue": editor_load,
            "Submitted pitches": submitted,
            "Adaptation open": adapt_open,
            "Published": published,
        },
        hints={
            "Editor queue": "Pitches + content waiting",
            "Submitted pitches": "From manager overview",
            "Adaptation open": "Drafts needing review",
            "Published": "Live publications",
        },
        icons={
            "Editor queue": "📥",
            "Submitted pitches": "💡",
            "Adaptation open": "🔁",
            "Published": "🚀",
        },
    )
    left, right = st.columns([1.15, 1])
    with left:
        ui.bar(
            {
                "Editor queue": editor_load,
                "Pitches": submitted,
                "Adaptation": adapt_open,
                "Published": published,
            },
            caption="Desk health snapshot",
        )
    with right:
        ui.score_meters(
            {
                "Editor pressure": min(100, int(editor_load) * 10),
                "Pitch backlog": min(100, int(submitted) * 12),
                "Adaptation load": min(100, int(adapt_open) * 12),
                "Publish output": min(100, int(published) * 8),
            },
            scale="100",
        )

    c1, c2 = st.columns(2)
    with c1:
        ui.card(
            "Signed in",
            meta=[user.role_label if user else "", user.username if user else ""],
            body="Use the left nav for every desk function — Overview, Pipeline, Users, queues, and more.",
        )
        ui.card(
            "Pipeline",
            meta=["Ingest · clean · persist"],
            body="Open Pipeline to run CSV ingest from data/raw.",
        )
    with c2:
        ui.card(
            "People",
            meta=["Create accounts · reset passwords"],
            body="Open Users to provision desks or reset credentials.",
        )
        ui.card(
            "Taxonomy",
            meta=["Content categories"],
            body="Open Categories to add labels used across desks.",
        )

    counts = raw.get("counts") or {}
    if counts:
        ui.section("Raw ingest")
        titled = {str(k).title(): v for k, v in counts.items() if isinstance(v, (int, float))}
        ui.kpi_row(
            titled,
            hints={k: "Raw ingest tally" for k in titled},
        )
        left, right = st.columns([1.15, 1])
        with left:
            ui.bar(titled, caption="Ingest counts")
        with right:
            total = max(sum(titled.values()), 1)
            ui.score_meters(
                {k: round(100 * float(v) / total) for k, v in titled.items()},
                scale="100",
            )
        for row in (raw.get("items") or [])[:5]:
            ui.card(
                row.get("headline") or row.get("title") or "Ingest row",
                status=row.get("status"),
                meta=[row.get("source_file") or ""],
            )


def render_pipeline() -> None:
    ui.header("Pipeline", "Ingest CSVs from data/raw → clean → persist.")
    only_new = st.checkbox("Only new files", help="Skip files already ingested.")
    c = st.columns(4)
    if c[0].button("Ingest", width="stretch"):
        _report(api.post("/admin/ingest", {"only_new": only_new}))
    if c[1].button("Clean", width="stretch"):
        _report(api.post("/admin/clean", {}))
    if c[2].button("Persist", width="stretch"):
        _report(api.post("/admin/persist", {}))
    if c[3].button("Run full pipeline", type="primary", width="stretch"):
        _report(api.post("/admin/pipeline", {"only_new": only_new}))

    st.divider()
    ui.section("Single file & combined")
    source = st.text_input(
        "Source file (relative under data/raw)",
        placeholder="e.g. news_sample.csv",
        key="ad_src",
    )
    d1, d2 = st.columns(2)
    if d1.button("Ingest file", width="stretch", disabled=not source.strip()):
        _report(api.post("/admin/ingest-file", {"source_file": source.strip()}))
    if d2.button("Ingest and clean", width="stretch"):
        _report(api.post("/admin/ingest-and-clean", {"only_new": only_new}))

    with st.expander("Inspect data"):
        if st.button("List CSV files"):
            _report(api.get("/admin/csv-files", _cache=False))
        limit = st.number_input("Raw rows", 1, 500, 20)
        if st.button("Show raw ingest rows"):
            res = api.get("/admin/raw-ingest", limit=limit, _cache=False)
            if res:
                ui.metrics(res.get("counts") or {})
                ui.table(res.get("items"), key="ad_raw")


def render_users() -> None:
    ui.header("Users", "Create accounts and reset passwords.")
    with st.form("add_user", clear_on_submit=True):
        c1, c2 = st.columns(2)
        username = c1.text_input("Username")
        password = c2.text_input(
            "Password",
            type="password",
            help="Min 10 chars with upper, lower, digit, special.",
        )
        first = c1.text_input("First name")
        last = c2.text_input("Last name")
        email = c1.text_input("Email")
        role = c2.selectbox("Role", config.ROLES)
        if st.form_submit_button("Create user", type="primary"):
            _report(
                api.post(
                    "/admin/users",
                    {
                        "username": username,
                        "password": password,
                        "first_name": first,
                        "last_name": last,
                        "email": email,
                        "role_code": role,
                    },
                )
            )

    ui.section("Reset password")
    with st.form("reset", clear_on_submit=True):
        c1, c2 = st.columns(2)
        who = c1.text_input("Username")
        pw = c2.text_input("New password", type="password")
        if st.form_submit_button("Reset"):
            _report(
                api.post(
                    "/admin/users/reset-password",
                    {"username": who, "new_password": pw},
                )
            )

    ui.section("Look up user")
    name = st.text_input("Username", key="ad_find")
    if name and st.button("Find"):
        res = api.get(f"/admin/users/{name}", _cache=False)
        if res:
            result = res.get("result") or {}
            ui.card(
                result.get("username") or name,
                meta=[result.get("role_code") or "", result.get("email") or ""],
            )


def render_categories() -> None:
    ui.header("Categories", "Add content categories.")
    with st.form("cat", clear_on_submit=True):
        name = st.text_input("Category name")
        desc = st.text_input("Description")
        if st.form_submit_button("Add category", type="primary"):
            _report(api.post("/admin/categories", {"name": name, "description": desc}))


def _report(res: dict | None) -> None:
    if res:
        st.success(res.get("message") or "Done.")
        ui.raw(res.get("result"), "Technical details")


def render() -> None:
    render_dashboard()
