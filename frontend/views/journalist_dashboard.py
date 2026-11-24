"""Journalist dashboard — KPI cards and editor assignments."""

from __future__ import annotations

import streamlit as st

from core import api, ui


def render() -> None:
    ui.header("Dashboard", "Desk overview and briefs assigned by editors.")
    data = api.get("/journalist/dashboard")
    if not data:
        ui.card(
            "Dashboard unavailable",
            body="Could not load desk metrics. Check that the API is running, then refresh.",
        )
        return

    metrics = data.get("metrics") or {}
    drafts = metrics.get("drafts", 0) or 0
    submitted = metrics.get("submitted", 0) or 0
    rework = metrics.get("rework", 0) or 0
    assignments = metrics.get("open_assignments", 0) or 0

    ui.kpi_row(
        {
            "Drafts": drafts,
            "Submitted": submitted,
            "Rework": rework,
            "Assignments": assignments,
        },
        hints={
            "Drafts": "In progress on your desk",
            "Submitted": "Waiting on editorial review",
            "Rework": "Needs your revision" if rework else "Clear",
            "Assignments": "Open briefs from editors",
        },
        icons={
            "Drafts": "📝",
            "Submitted": "📤",
            "Rework": "🔁",
            "Assignments": "📋",
        },
    )
    open_items = int(drafts) + int(submitted) + int(rework)
    left, right = st.columns([1.15, 1])
    with left:
        ui.bar(
            {
                "Drafts": drafts,
                "Submitted": submitted,
                "Rework": rework,
                "Assignments": assignments,
            },
            caption="Desk mix (counts)",
        )
    with right:
        # Absolute capacity vs soft full load (~8 open items), not "1 of 1 = 100%".
        ui.score_meters(
            {
                f"Desk load ({open_items}/{ui.DESK_CAPACITY_FULL})": ui.desk_load_pct(open_items),
                "Capacity left": ui.desk_capacity_pct(open_items),
                "Open assignments": ui.desk_load_pct(assignments),
            },
            scale="100",
        )
        st.caption(
            f"Capacity is relative to about {ui.DESK_CAPACITY_FULL} open desk items — "
            "one story is light load, not full."
        )

    ui.section("Assignments from editors")
    rows = data.get("assignments") or []
    if not rows:
        st.caption(
            "No editor assignments yet. When an editor matches a pitch to you, it appears here."
        )
        return

    for a in rows:
        meta = [
            f"Assigned by · {a.get('assigned_by') or 'Editor'}",
            f"Article · {a.get('title') or 'Untitled'}",
            f"Deadline · {a.get('deadline') or 'Not set'}",
        ]
        if a.get("brief_from_pitch"):
            meta.append(f"From pitch · {a['brief_from_pitch']}")
        if a.get("kind"):
            meta.append(f"Type · {str(a['kind']).title()}")
        if a.get("note"):
            meta.append(f"Note · {a['note']}")
        ui.card(
            a.get("title") or "Untitled assignment",
            status=a.get("status"),
            meta=meta,
            body=a.get("summary"),
        )
