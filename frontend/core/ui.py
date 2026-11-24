"""Small reusable UI building blocks."""

from __future__ import annotations

from typing import Any, Iterable

import altair as alt
import pandas as pd
import streamlit as st

from core import session

_COMPACT_CSS = """
<style>
    :root {
        --nm-blue: #1F4E79;
        --nm-blue-soft: #e8eef5;
        --nm-border: #e2e8f0;
        --nm-muted: #64748b;
        --nm-bg: #f8fafc;
        /* 4px spacing scale */
        --nm-space-1: 4px;
        --nm-space-2: 8px;
        --nm-space-3: 12px;
        --nm-space-4: 16px;
        --nm-space-5: 24px;
        --nm-space-6: 32px;
        --nm-space-7: 48px;
        --nm-radius: 12px;
        --nm-page-pad-x: 24px;
        --nm-page-pad-y: 24px;
        --nm-topbar-clearance: 48px;
    }
    /* Use the full main column — kill Streamlit's centered max-width gutter */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"],
    [data-testid="stMain"], .stMain, .main {
        max-width: none !important;
        width: 100% !important;
    }
    [data-testid="stMain"] {
        flex: 1 1 auto !important;
    }
    .block-container,
    div.block-container,
    [data-testid="stMainBlockContainer"],
    .stMainBlockContainer,
    section.main .block-container {
        padding-top: calc(var(--nm-topbar-clearance) + var(--nm-space-4)) !important;
        padding-bottom: var(--nm-space-6) !important;
        padding-left: var(--nm-page-pad-x) !important;
        padding-right: var(--nm-page-pad-x) !important;
        max-width: none !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    [data-testid="stVerticalBlock"],
    [data-testid="stHorizontalBlock"],
    [data-testid="stLayoutWrapper"],
    [data-testid="stElementContainer"] {
        max-width: none !important;
        box-sizing: border-box !important;
    }
    .nm-kpi-row {
        width: 100% !important;
        box-sizing: border-box !important;
    }
    [data-testid="stSidebarNav"] [data-testid="stSidebarNavSeparator"] {
        margin: var(--nm-space-3) 0 !important;
    }
    /* Keep header/toolbar — expand-sidebar lives inside stToolbar */
    div[data-testid="stToolbar"] {
        display: flex !important;
        visibility: visible !important;
        height: auto !important;
        opacity: 1 !important;
    }
    /* Soften chrome but never hide expand/collapse */
    [data-testid="stToolbar"] [data-testid="stToolbarActions"],
    [data-testid="stAppDeployButton"],
    [data-testid="stMainMenu"] {
        opacity: 0.35;
    }
    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapseButton"] {
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        width: 2.25rem !important;
        height: 2.25rem !important;
        min-width: 2.25rem !important;
        min-height: 2.25rem !important;
    }

    /* ── Fixed top bar — kill chrome flex-gap slots above page titles ── */
    .nm-topbar-marker,
    .nm-topbar-spacer {
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    /*
      Streamlit main column uses gap:16px between EVERY child. Zero-height
      style/markdown/iframe chrome still eats a gap each — hide them entirely.
    */
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]
      > [data-testid="stElementContainer"]:has(style),
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]
      > [data-testid="stElementContainer"]:has(.nm-topbar-marker),
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]
      > [data-testid="stElementContainer"]:has(.nm-topbar-spacer),
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]
      > [data-testid="stElementContainer"]:has(iframe),
    div[data-testid="stElementContainer"]:has(.nm-topbar-marker),
    div[data-testid="stElementContainer"]:has(.nm-topbar-spacer),
    div[data-testid="stElementContainer"]:has(iframe[height="0"]),
    div[data-testid="stElementContainer"]:has(iframe[height="0px"]),
    iframe[height="0"],
    iframe[height="0px"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        max-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: 0 !important;
        overflow: hidden !important;
    }
    /* Also hide style-only injects anywhere under main (duplicate inject_chrome) */
    [data-testid="stMain"] [data-testid="stElementContainer"]:has(> div.stMarkdown style),
    [data-testid="stMain"] [data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"] > style) {
        display: none !important;
        margin: 0 !important;
        padding: 0 !important;
        height: 0 !important;
    }
    /* Streamlit chrome header: take no layout height (expand control stays fixed) */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 0 !important;
        min-height: 0 !important;
        overflow: visible !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        z-index: 1001 !important;
        pointer-events: none !important;
    }
    header[data-testid="stHeader"] [data-testid="stToolbar"],
    header[data-testid="stHeader"] button {
        pointer-events: auto !important;
    }
    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapseButton"] {
        position: relative !important;
        z-index: 1002 !important;
    }
    /*
      Fixed bar wrapper must not keep an in-flow flex slot (height+gap).
      Collapse the wrapper; paint chrome on the inner horizontal block.
    */
    [data-testid="stLayoutWrapper"]:has(.nm-brand),
    div[data-testid="stElementContainer"]:has(.nm-topbar-marker)
      + [data-testid="stLayoutWrapper"] {
        position: fixed !important;
        top: 0 !important;
        z-index: 1000 !important;
        height: 0 !important;
        min-height: 0 !important;
        max-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        overflow: visible !important;
        /* Drop out of flex gap accounting where supported */
        flex: 0 0 0 !important;
        align-self: flex-start !important;
    }
    [data-testid="stLayoutWrapper"]:has(.nm-brand) > [data-testid="stHorizontalBlock"],
    div[data-testid="stElementContainer"]:has(.nm-topbar-marker)
      + [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {
        background: rgba(255,255,255,0.98) !important;
        backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--nm-border);
        padding: var(--nm-space-2) var(--nm-page-pad-x) !important;
        margin: 0 !important;
        box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
        box-sizing: border-box !important;
        min-height: 44px !important;
        width: 100% !important;
        gap: var(--nm-space-3) !important;
    }
    /*
      Root main stack: gap 0 (chrome is display:none). Content rhythm comes from
      a single margin-bottom on each element container — avoid double spacing
      with component-level margins.
    */
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
        gap: 0 !important;
        row-gap: 0 !important;
    }
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]
      > [data-testid="stElementContainer"] {
        margin: 0 0 var(--nm-space-4) 0 !important;
        padding: 0 !important;
    }
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]
      > [data-testid="stElementContainer"]:has(style),
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]
      > [data-testid="stElementContainer"]:has(iframe),
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]
      > [data-testid="stElementContainer"]:has(.nm-topbar-marker),
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]
      > [data-testid="stLayoutWrapper"]:has(.nm-brand) {
        margin: 0 !important;
        padding: 0 !important;
    }
    /* Nested columns / forms use the same 16px gap */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
        gap: var(--nm-space-4) !important;
        row-gap: var(--nm-space-4) !important;
    }
    [data-testid="stMain"] [data-testid="stVerticalBlock"] {
        gap: var(--nm-space-4) !important;
        row-gap: var(--nm-space-4) !important;
    }
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
        gap: 0 !important;
        row-gap: 0 !important;
    }
    [data-testid="stMain"] [data-testid="stColumn"] > [data-testid="stVerticalBlock"]
      > [data-testid="stElementContainer"] {
        margin: 0 !important;
    }
    .nm-brand {
        font-weight: 700;
        color: var(--nm-blue);
        font-size: 1.1rem;
        letter-spacing: 0.02em;
        line-height: 40px;
        padding-left: var(--nm-space-1);
    }

    /* Hide popover carets / material expand icons in the top bar */
    [data-testid="stMain"] [data-testid="stPopover"] svg,
    [data-testid="stMain"] [data-testid="stPopoverButton"] [data-testid="stIconMaterial"],
    [data-testid="stMain"] [data-testid="stPopoverButton"] [data-testid="stIcon"] {
        display: none !important;
    }
    /* Alerts pill */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.nm-brand)
      > [data-testid="stColumn"]:last-child
      [data-testid="stHorizontalBlock"]
      > [data-testid="stColumn"]:first-child
      [data-testid="stPopoverButton"] {
        border-radius: 999px !important;
        min-height: 2.55rem !important;
        height: 2.55rem !important;
        padding: 0 1rem !important;
        background: #fff !important;
        color: var(--nm-blue) !important;
        border: 1px solid var(--nm-border) !important;
        box-shadow: none !important;
        font-weight: 600 !important;
        width: 100% !important;
        max-width: none !important;
        white-space: nowrap !important;
    }

    /* Round blue avatar (initial only) */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.nm-brand)
      > [data-testid="stColumn"]:last-child
      [data-testid="stHorizontalBlock"]
      > [data-testid="stColumn"]:last-child
      [data-testid="stPopoverButton"] {
        border-radius: 999px !important;
        width: 2.55rem !important;
        min-width: 2.55rem !important;
        max-width: 2.55rem !important;
        height: 2.55rem !important;
        min-height: 2.55rem !important;
        padding: 0 !important;
        margin-left: auto !important;
        background: var(--nm-blue) !important;
        color: #fff !important;
        border: 2px solid #d6e4f2 !important;
        box-shadow: 0 2px 6px rgba(31, 78, 121, 0.22) !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        letter-spacing: 0 !important;
    }
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.nm-brand)
      > [data-testid="stColumn"]:last-child
      [data-testid="stHorizontalBlock"]
      > [data-testid="stColumn"]:last-child
      [data-testid="stPopoverButton"] p,
    [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.nm-brand)
      > [data-testid="stColumn"]:last-child
      [data-testid="stHorizontalBlock"]
      > [data-testid="stColumn"]:last-child
      [data-testid="stPopoverButton"] span {
        color: #fff !important;
        font-weight: 700 !important;
    }

    /* ── Sidebar logout: stay INSIDE the rail (no viewport-fixed) ── */
    section[data-testid="stSidebar"] {
        position: relative !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        display: flex !important;
        flex-direction: column !important;
        height: 100% !important;
        min-height: 100% !important;
        box-sizing: border-box !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
        flex: 1 1 auto !important;
        overflow-y: auto !important;
        max-height: none !important;
    }
    /* Never show Streamlit's View more / View less nav toggle */
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] button[kind="secondary"],
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] [data-testid="stSidebarNavViewButton"],
    section[data-testid="stSidebar"] ul[data-testid="stSidebarNavItems"] ~ div button,
    section[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] + div button {
        display: none !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] {
        max-height: none !important;
        overflow: visible !important;
    }
    .nm-logout-anchor { height: 0; overflow: hidden; }
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        margin-top: auto !important;
        position: sticky !important;
        bottom: 0 !important;
        padding: var(--nm-space-4) var(--nm-space-3) var(--nm-space-5) !important;
        background: inherit !important;
        border-top: 1px solid var(--nm-border) !important;
        z-index: 5 !important;
    }
    section[data-testid="stSidebar"] .stButton {
        position: static !important;
        width: 100% !important;
        max-width: 100% !important;
        left: auto !important;
        bottom: auto !important;
        background: transparent !important;
        padding: 0 !important;
        border-top: none !important;
        margin: 0 !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        border: 1px solid var(--nm-border) !important;
        background: #fff !important;
        color: #334155 !important;
        font-weight: 600 !important;
        border-radius: var(--nm-space-2) !important;
        width: 100% !important;
        min-height: 40px !important;
    }
    /* When collapsed, never paint logout outside the rail */
    section[data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarUserContent"],
    section[data-testid="stSidebar"][data-collapsed="true"] .stButton,
    section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarUserContent"],
    section[data-testid="stSidebar"][aria-expanded="false"] .stButton {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }

    /* ── Page / section typography rhythm ── */
    .nm-page-head {
        margin: 0 0 var(--nm-space-2) 0;
        padding: 0;
    }
    .nm-page-head.nm-section {
        margin-top: var(--nm-space-5);
        padding-top: var(--nm-space-1);
    }
    .nm-page-head h3 {
        margin: 0 0 var(--nm-space-2) 0 !important;
        padding: 0 !important;
        font-size: 1.35rem !important;
        line-height: 1.3 !important;
        color: #0f172a;
    }
    .nm-page-head .nm-page-desc {
        margin: 0 !important;
        padding: 0 !important;
        color: var(--nm-muted);
        font-size: 0.9rem;
        line-height: 1.45;
    }
    [data-testid="stMain"] h1,
    [data-testid="stMain"] h2,
    [data-testid="stMain"] h3 {
        margin-top: 0 !important;
        margin-bottom: var(--nm-space-2) !important;
        padding-top: 0 !important;
        line-height: 1.3 !important;
    }
    [data-testid="stMain"] h2,
    [data-testid="stMain"] h3:not(.nm-page-head h3) {
        margin-top: var(--nm-space-2) !important;
    }
    [data-testid="stMain"] h1 { font-size: 1.35rem !important; }
    div[data-testid="stCaptionContainer"] {
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="stCaptionContainer"] p {
        margin: 0 !important;
        line-height: 1.45 !important;
    }
    [data-testid="stMain"] hr {
        margin: var(--nm-space-5) 0 !important;
        border: none !important;
        border-top: 1px solid var(--nm-border) !important;
    }
    [data-testid="stMain"] [data-testid="stExpander"] {
        margin: 0 !important;
    }
    [data-testid="stMain"] [data-testid="stForm"] {
        border: 1px solid var(--nm-border) !important;
        border-radius: var(--nm-radius) !important;
        padding: var(--nm-space-4) !important;
        background: #fff !important;
    }
    [data-testid="stMain"] .stButton > button {
        border-radius: var(--nm-space-2) !important;
        min-height: 40px !important;
    }
    [data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: var(--nm-space-2) !important;
        margin-bottom: var(--nm-space-4) !important;
    }
    [data-testid="stMain"] [data-testid="stDataFrame"],
    [data-testid="stMain"] [data-testid="stTable"] {
        margin: 0 !important;
    }
    [data-testid="stMain"] .stAlert {
        margin: 0 !important;
        padding: var(--nm-space-3) var(--nm-space-4) !important;
        border-radius: var(--nm-radius) !important;
    }

    /* ── HEMA-style KPI cards ── */
    .nm-kpi-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: var(--nm-space-4);
        margin: 0;
        width: 100%;
        box-sizing: border-box;
    }
    .nm-kpi {
        background: #fff;
        border: 1px solid var(--nm-border);
        border-radius: var(--nm-radius);
        padding: var(--nm-space-4);
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        min-height: 96px;
        box-sizing: border-box;
    }
    .nm-kpi-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--nm-space-2);
        margin-bottom: var(--nm-space-2);
    }
    .nm-kpi-label {
        color: var(--nm-muted);
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.01em;
    }
    .nm-kpi-icon {
        width: 32px;
        height: 32px;
        border-radius: 999px;
        background: var(--nm-blue-soft);
        color: var(--nm-blue);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.85rem;
        flex: 0 0 auto;
    }
    .nm-kpi-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.2;
    }
    .nm-kpi-hint {
        margin-top: var(--nm-space-2);
        font-size: 0.75rem;
        color: var(--nm-muted);
        line-height: 1.35;
    }
    .nm-kpi-hint.up { color: #15803d; }
    .nm-kpi-hint.down { color: #b91c1c; }

    /* Cards: no outer margin — Streamlit element gap owns the rhythm */
    .nm-card {
        border: 1px solid rgba(31, 78, 121, 0.18);
        border-radius: var(--nm-radius);
        padding: var(--nm-space-4);
        margin: 0;
        background: linear-gradient(180deg, #ffffff 0%, #f6f9fc 100%);
        box-sizing: border-box;
    }
    .nm-card h4 {
        margin: 0 0 var(--nm-space-2) 0;
        font-size: 0.98rem;
        color: #12324f;
        line-height: 1.35;
    }
    .nm-meta {
        color: #5a6b7d;
        font-size: 0.84rem;
        margin: var(--nm-space-1) 0;
        line-height: 1.4;
    }
    .nm-chip {
        display: inline-block;
        padding: var(--nm-space-1) var(--nm-space-2);
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        background: #e8eef5;
        color: #1F4E79;
        margin: 0 var(--nm-space-2) var(--nm-space-2) 0;
        vertical-align: middle;
    }
    .nm-chip.warn { background: #fff3cd; color: #856404; }
    .nm-chip.ok { background: #d4edda; color: #155724; }
    .nm-chip.danger { background: #f8d7da; color: #721c24; }

    /* ── Score meters ── */
    .nm-meters {
        display: grid;
        gap: var(--nm-space-3);
        margin: 0;
        width: 100%;
        box-sizing: border-box;
    }
    .nm-meter {
        background: #fff;
        border: 1px solid var(--nm-border);
        border-radius: var(--nm-radius);
        padding: var(--nm-space-3) var(--nm-space-4);
        box-sizing: border-box;
    }
    .nm-meter-head {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: var(--nm-space-2);
        margin-bottom: var(--nm-space-2);
    }
    .nm-meter-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: var(--nm-muted);
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }
    .nm-meter-value {
        font-size: 0.95rem;
        font-weight: 700;
        color: #0f172a;
        font-variant-numeric: tabular-nums;
    }
    .nm-meter-track {
        height: 8px;
        border-radius: 999px;
        background: #e8eef5;
        overflow: hidden;
    }
    .nm-meter-fill {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #1F4E79 0%, #3d7ab0 100%);
        transition: width 0.35s ease;
    }
    .nm-meter-fill.high { background: linear-gradient(90deg, #b45309 0%, #dc2626 100%); }
    .nm-meter-fill.good { background: linear-gradient(90deg, #15803d 0%, #22c55e 100%); }
    .nm-meter-fill.mid { background: linear-gradient(90deg, #1F4E79 0%, #0ea5e9 100%); }

    .nm-match-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: var(--nm-space-4);
        margin: 0;
        width: 100%;
        box-sizing: border-box;
    }
    .nm-match {
        background: #fff;
        border: 1px solid var(--nm-border);
        border-radius: var(--nm-radius);
        padding: var(--nm-space-4);
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        border-top: 3px solid var(--nm-blue);
        box-sizing: border-box;
        height: 100%;
    }
    .nm-match.rank-1 { border-top-color: #ca8a04; }
    .nm-match.rank-2 { border-top-color: #64748b; }
    .nm-match.rank-3 { border-top-color: #b45309; }
    .nm-match-rank {
        font-size: 0.72rem;
        font-weight: 700;
        color: var(--nm-blue);
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin: 0 0 var(--nm-space-1) 0;
    }
    .nm-match-name {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0 0 var(--nm-space-2) 0;
        line-height: 1.3;
    }
    .nm-match-meta {
        font-size: 0.8rem;
        color: var(--nm-muted);
        margin: var(--nm-space-1) 0;
        line-height: 1.4;
    }
    .nm-stack {
        display: grid;
        gap: var(--nm-space-4);
        margin: 0;
        width: 100%;
        box-sizing: border-box;
    }
    .nm-stack-sm {
        display: grid;
        gap: var(--nm-space-3);
        margin: 0;
        width: 100%;
        box-sizing: border-box;
    }

    @media (max-width: 900px) {
        .block-container,
        div.block-container,
        [data-testid="stMainBlockContainer"],
        .stMainBlockContainer,
        section.main .block-container {
            padding-left: var(--nm-space-4) !important;
            padding-right: var(--nm-space-4) !important;
            padding-bottom: var(--nm-space-5) !important;
        }
        .nm-kpi-row,
        .nm-match-grid {
            grid-template-columns: 1fr;
            gap: var(--nm-space-3);
        }
    }
</style>
"""

_ID_COLS = {
    "id", "content_id", "story_pitch_id", "article_id", "news_id", "user_id",
    "journalist_id", "assignee_user_id", "assigned_by_user_id", "author_id",
    "evidence_id", "notification_id", "task_id", "request_id", "draft_id",
}

_KPI_ICONS = ("📄", "📤", "🔁", "✅", "📢", "⏱", "📥", "📊")

# Soft full desk load — one open story is light work, not "at capacity".
DESK_CAPACITY_FULL = 8


def desk_load_pct(open_items: Any, *, full_at: int = DESK_CAPACITY_FULL) -> int:
    """0–100 desk load. full_at open items ≈ 100% (default 8)."""
    try:
        n = max(0, int(open_items or 0))
    except (TypeError, ValueError):
        n = 0
    full = max(1, int(full_at or DESK_CAPACITY_FULL))
    return min(100, round(100.0 * n / full))


def desk_capacity_pct(open_items: Any, *, full_at: int = DESK_CAPACITY_FULL) -> int:
    """Remaining capacity 0–100 complementary to desk_load_pct."""
    return max(0, 100 - desk_load_pct(open_items, full_at=full_at))


def inject_chrome() -> None:
    """Tighten Streamlit chrome every run (custom HTML is wiped on rerun)."""
    st.markdown(_COMPACT_CSS, unsafe_allow_html=True)


def header(title: str, caption: str | None = None) -> None:
    """Page title + optional description as one spaced unit."""
    inject_chrome()
    desc = f'<p class="nm-page-desc">{caption}</p>' if caption else ""
    st.markdown(
        f'<div class="nm-page-head"><h3>{title}</h3>{desc}</div>',
        unsafe_allow_html=True,
    )


def section(title: str, caption: str | None = None) -> None:
    """In-page section heading with shared spacing tokens."""
    desc = f'<p class="nm-page-desc">{caption}</p>' if caption else ""
    st.markdown(
        f'<div class="nm-page-head nm-section"><h3>{title}</h3>{desc}</div>',
        unsafe_allow_html=True,
    )


def kpi_row(
    items: dict[str, Any],
    *,
    hints: dict[str, str] | None = None,
    icons: dict[str, str] | None = None,
) -> None:
    """HEMA-style KPI metric cards."""
    if not items:
        return
    hints = hints or {}
    icons = icons or {}
    parts = ['<div class="nm-kpi-row">']
    for i, (label, value) in enumerate(items.items()):
        icon = icons.get(label) or _KPI_ICONS[i % len(_KPI_ICONS)]
        hint = hints.get(label) or ""
        hint_cls = "nm-kpi-hint"
        low = hint.lower()
        if "↑" in hint or "up" in low or "+" in hint[:2]:
            hint_cls += " up"
        elif "↓" in hint or "down" in low or risk_word(hint):
            hint_cls += " down"
        display = "—" if value is None else value
        hint_html = f'<div class="{hint_cls}">{hint}</div>' if hint else ""
        parts.append(
            f'<div class="nm-kpi">'
            f'<div class="nm-kpi-top"><span class="nm-kpi-label">{label}</span>'
            f'<span class="nm-kpi-icon">{icon}</span></div>'
            f'<div class="nm-kpi-value">{display}</div>'
            f"{hint_html}"
            f"</div>"
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def risk_word(hint: str) -> bool:
    return any(w in hint.lower() for w in ("risk", "overdue", "stuck", "at risk"))


def as_rows(data: Any, *keys: str) -> list[dict]:
    """Extract a list of records from the many response shapes the API returns."""
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        for key in keys:
            if isinstance(data.get(key), list):
                return [r for r in data[key] if isinstance(r, dict)]
        for value in data.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value
    return []


def status_chip(status: str | None) -> str:
    s = (status or "unknown").lower()
    kind = "nm-chip"
    if s in {"approved", "published", "ready"}:
        kind += " ok"
    elif s in {"rejected", "urgent"}:
        kind += " danger"
    elif s in {"rework", "submitted", "scheduled"}:
        kind += " warn"
    return f'<span class="{kind}">{s}</span>'


def _card_html(
    title: str,
    *,
    meta: list[str] | None = None,
    body: str | None = None,
    status: str | None = None,
) -> str:
    bits = [f'<div class="nm-card"><h4>{title}</h4>']
    if status:
        bits.append(status_chip(status))
    for line in meta or []:
        if line:
            bits.append(f'<div class="nm-meta">{line}</div>')
    if body:
        bits.append(f'<div class="nm-meta">{body}</div>')
    bits.append("</div>")
    return "".join(bits)


def card(
    title: str,
    *,
    meta: list[str] | None = None,
    body: str | None = None,
    status: str | None = None,
) -> None:
    st.markdown(
        _card_html(title, meta=meta, body=body, status=status),
        unsafe_allow_html=True,
    )


def cards(items: Iterable[dict] | None, *, empty: str = "Nothing to show.") -> None:
    """Render many cards in one stack so spacing is owned by CSS gap."""
    items = list(items or [])
    if not items:
        st.caption(empty)
        return
    parts = ['<div class="nm-stack">']
    for item in items:
        parts.append(
            _card_html(
                str(item.get("title") or item.get("name") or "Untitled"),
                status=item.get("status"),
                meta=[m for m in (item.get("meta") or []) if m],
                body=item.get("body") or item.get("summary"),
            )
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def _display_frame(rows: list[dict], *, hide_ids: bool = True) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if hide_ids:
        drop = [c for c in df.columns if c.lower() in _ID_COLS or c.lower().endswith("_id")]
        if drop and len(drop) < len(df.columns):
            df = df.drop(columns=drop, errors="ignore")
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, (dict, list))).any():
            df[col] = df[col].map(lambda v: str(v) if isinstance(v, (dict, list)) else v)
    rename = {
        "content_kind": "type",
        "source_type": "source",
        "created_by_desk": "from",
        "assigned_by": "assigned by",
        "due_at": "deadline",
        "deadline": "deadline",
        "full_name": "name",
        "primary_specialization": "specialty",
        "availability_status": "availability",
        "open_workload": "open work",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    return df


def table(
    rows: Iterable[dict] | None,
    *,
    key: str,
    selectable: bool = False,
    empty: str = "Nothing to show.",
    hide_ids: bool = True,
) -> dict | None:
    rows = list(rows or [])
    if not rows:
        st.caption(empty)
        return None
    df = _display_frame(rows, hide_ids=hide_ids)
    if not selectable:
        st.dataframe(df, hide_index=True, key=f"{key}:{session.revision()}")
        return None
    event = st.dataframe(
        df,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"{key}:{session.revision()}",
    )
    picked = event.selection.rows
    return rows[picked[0]] if picked else None


def pick_id(row: dict | None, keys: tuple[str, ...]) -> int | None:
    for k in keys:
        if row and row.get(k) is not None:
            return int(row[k])
    return None


def _clamp01(value: Any) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if v > 1.0 and v <= 100.0:
        v = v / 100.0
    return max(0.0, min(1.0, v))


def _meter_good_when_high(label: str) -> bool:
    """True when a full bar is healthy (capacity left), not a warning (desk load)."""
    key = str(label or "").strip().lower()
    if any(
        bad in key
        for bad in (
            "desk load",
            "load (",
            "backlog",
            "risk",
            "pressure",
            "pending",
            "overdue",
            "open assignments",
        )
    ):
        return False
    if any(
        good in key
        for good in (
            "capacity left",
            "capacity",
            "available",
            "availability",
            "match",
            "specialty",
            "credibility",
            "engagement",
            "interest",
            "similarity",
            "approved",
            "ready",
            "flow",
        )
    ):
        return True
    return True


def _meter_tone(pct: float, *, good_when_high: bool = True) -> str:
    """CSS tone for a 0–1 fill. Capacity left → green when full; desk load → red when full."""
    x = max(0.0, min(1.0, float(pct)))
    if good_when_high:
        if x >= 0.75:
            return "good"
        if x >= 0.45:
            return "mid"
        return "high"
    if x >= 0.75:
        return "high"
    if x >= 0.45:
        return "mid"
    return "good"


def score_meters(
    scores: dict[str, Any],
    *,
    scale: str = "auto",
) -> None:
    """Horizontal meters for ML / desk scores (0–1 or 0–100)."""
    if not scores:
        return
    parts = ['<div class="nm-meters">']
    for label, raw in scores.items():
        if raw is None or raw == "—":
            parts.append(
                f'<div class="nm-meter"><div class="nm-meter-head">'
                f'<span class="nm-meter-label">{label}</span>'
                f'<span class="nm-meter-value">—</span></div></div>'
            )
            continue
        try:
            num = float(raw)
        except (TypeError, ValueError):
            parts.append(
                f'<div class="nm-meter"><div class="nm-meter-head">'
                f'<span class="nm-meter-label">{label}</span>'
                f'<span class="nm-meter-value">{raw}</span></div></div>'
            )
            continue
        if scale == "100" or (scale == "auto" and num > 1.0):
            pct = max(0.0, min(1.0, num / 100.0))
            display = f"{int(round(pct * 100))}%"
        else:
            pct = _clamp01(num)
            display = f"{pct:.0%}"
        tone = _meter_tone(pct, good_when_high=_meter_good_when_high(str(label)))
        parts.append(
            f'<div class="nm-meter"><div class="nm-meter-head">'
            f'<span class="nm-meter-label">{label}</span>'
            f'<span class="nm-meter-value">{display}</span></div>'
            f'<div class="nm-meter-track"><div class="nm-meter-fill {tone}" '
            f'style="width:{pct * 100:.1f}%"></div></div></div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def desk_capacity_card(
    name: str,
    open_items: Any,
    *,
    full_at: int = DESK_CAPACITY_FULL,
    specialty: str | None = None,
    availability: str | None = None,
) -> None:
    """One journalist desk card: open/soft-full + load/capacity meters with correct tones."""
    try:
        open_n = max(0, int(open_items or 0))
    except (TypeError, ValueError):
        open_n = 0
    full = max(1, int(full_at or DESK_CAPACITY_FULL))
    load = desk_load_pct(open_n, full_at=full)
    left = desk_capacity_pct(open_n, full_at=full)
    load_tone = _meter_tone(load / 100.0, good_when_high=False)
    left_tone = _meter_tone(left / 100.0, good_when_high=True)
    meta_bits = [f"Open · <b>{open_n}</b> / {full} soft capacity"]
    if specialty:
        meta_bits.append(str(specialty))
    if availability:
        meta_bits.append(str(availability).title())
    meta_html = "".join(f'<div class="nm-meta">{bit}</div>' for bit in meta_bits)
    html = (
        f'<div class="nm-card"><h4>{name}</h4>{meta_html}'
        f'<div class="nm-meters" style="margin-top:var(--nm-space-3);gap:var(--nm-space-3)">'
        f'<div class="nm-meter" style="border:none;padding:0;background:transparent">'
        f'<div class="nm-meter-head"><span class="nm-meter-label">Desk load</span>'
        f'<span class="nm-meter-value">{load}%</span></div>'
        f'<div class="nm-meter-track"><div class="nm-meter-fill {load_tone}" '
        f'style="width:{load}%"></div></div></div>'
        f'<div class="nm-meter" style="border:none;padding:0;background:transparent">'
        f'<div class="nm-meter-head"><span class="nm-meter-label">Capacity left</span>'
        f'<span class="nm-meter-value">{left}%</span></div>'
        f'<div class="nm-meter-track"><div class="nm-meter-fill {left_tone}" '
        f'style="width:{left}%"></div></div></div>'
        f"</div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def scores_chart(
    scores: dict[str, Any],
    *,
    title: str = "Score breakdown",
    height: int = 220,
) -> None:
    """Altair bar chart for numeric score dicts (Streamlit-native)."""
    rows = []
    for label, raw in (scores or {}).items():
        try:
            num = float(raw)
        except (TypeError, ValueError):
            continue
        if num > 1.0 and num <= 100.0:
            num = num / 100.0
        rows.append({"signal": str(label), "score": max(0.0, min(1.0, num))})
    if not rows:
        return
    df = pd.DataFrame(rows)
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, color="#1F4E79")
        .encode(
            x=alt.X("score:Q", title=None, scale=alt.Scale(domain=[0, 1])),
            y=alt.Y("signal:N", sort="-x", title=None),
            tooltip=[
                alt.Tooltip("signal:N", title="Signal"),
                alt.Tooltip("score:Q", title="Score", format=".0%"),
            ],
        )
        .properties(height=height, title=title)
    )
    st.altair_chart(chart, use_container_width=True)


def pick_top_journalist(
    matches: list[dict] | None,
    *,
    key: str,
    empty: str = "Click **Find top 3 journalists** to rank by specialty + open workload.",
) -> int | None:
    """Show ranked top matches with meters/chart; return chosen user_id."""
    rows = [m for m in (matches or []) if m.get("user_id")][:3]
    if not rows:
        st.caption(empty)
        return None

    section(
        "Top journalists",
        "Ranked by specialty fit, open desk workload (draft / submitted / rework), and availability.",
    )

    # Comparison chart across the shortlist
    chart_rows: list[dict[str, Any]] = []
    for i, m in enumerate(rows, start=1):
        name = m.get("full_name") or m.get("username") or f"#{i}"
        chart_rows.extend(
            [
                {"journalist": name, "signal": "Match", "value": _clamp01(m.get("score"))},
                {
                    "journalist": name,
                    "signal": "Specialty",
                    "value": _clamp01(m.get("specialty_score")),
                },
                {
                    "journalist": name,
                    "signal": "Capacity",
                    "value": _clamp01(m.get("workload_score")),
                },
            ]
        )
    if chart_rows:
        cdf = pd.DataFrame(chart_rows)
        chart = (
            alt.Chart(cdf)
            .mark_bar(cornerRadiusEnd=3)
            .encode(
                x=alt.X("value:Q", title=None, scale=alt.Scale(domain=[0, 1])),
                y=alt.Y("signal:N", title=None, sort=["Match", "Specialty", "Capacity"]),
                color=alt.Color(
                    "signal:N",
                    scale=alt.Scale(
                        domain=["Match", "Specialty", "Capacity"],
                        range=["#1F4E79", "#0ea5e9", "#15803d"],
                    ),
                    legend=None,
                ),
                row=alt.Row("journalist:N", title=None, header=alt.Header(labelAngle=0)),
                tooltip=[
                    alt.Tooltip("journalist:N"),
                    alt.Tooltip("signal:N"),
                    alt.Tooltip("value:Q", format=".0%"),
                ],
            )
            .properties(height=70)
            .resolve_scale(x="shared")
        )
        st.altair_chart(chart, use_container_width=True)

    labels: list[str] = []
    by_label: dict[str, dict] = {}
    cards_html = ['<div class="nm-match-grid">']
    for i, m in enumerate(rows, start=1):
        rank = int(m.get("rank") or i)
        name = m.get("full_name") or m.get("username") or f"Journalist {rank}"
        specialty = m.get("primary_specialization") or "General"
        open_work = int(m.get("open_workload") or 0)
        full_at = int(m.get("capacity_full_at") or DESK_CAPACITY_FULL)
        avail = (m.get("availability_status") or "available").title()
        match_pct = _clamp01(m.get("score"))
        spec_pct = _clamp01(m.get("specialty_score"))
        # Prefer API capacity; fall back to soft-full-at math (never 1 item = full).
        if m.get("workload_score") is not None:
            cap_pct = _clamp01(m.get("workload_score"))
        else:
            cap_pct = desk_capacity_pct(open_work, full_at=full_at) / 100.0
        load_pct = int(m.get("load_pct") or desk_load_pct(open_work, full_at=full_at))
        label = f"#{rank}  {name}"
        labels.append(label)
        by_label[label] = m
        cards_html.append(
            f'<div class="nm-match rank-{rank}">'
            f'<div class="nm-match-rank">Rank {rank}</div>'
            f'<div class="nm-match-name">{name}</div>'
            f'<div class="nm-match-meta">{specialty} · {avail}</div>'
            f'<div class="nm-match-meta">Open desk · <b>{open_work}</b> / {full_at}</div>'
            f'<div class="nm-meter" style="border:none;padding:0.35rem 0 0">'
            f'<div class="nm-meter-head"><span class="nm-meter-label">Match</span>'
            f'<span class="nm-meter-value">{match_pct:.0%}</span></div>'
            f'<div class="nm-meter-track"><div class="nm-meter-fill {_meter_tone(match_pct, good_when_high=True)}" '
            f'style="width:{match_pct*100:.1f}%"></div></div>'
            f'<div class="nm-meter-head" style="margin-top:0.35rem"><span class="nm-meter-label">Specialty</span>'
            f'<span class="nm-meter-value">{spec_pct:.0%}</span></div>'
            f'<div class="nm-meter-track"><div class="nm-meter-fill {_meter_tone(spec_pct, good_when_high=True)}" '
            f'style="width:{spec_pct*100:.1f}%"></div></div>'
            f'<div class="nm-meter-head" style="margin-top:0.35rem"><span class="nm-meter-label">Capacity left</span>'
            f'<span class="nm-meter-value">{cap_pct:.0%}</span></div>'
            f'<div class="nm-meter-track"><div class="nm-meter-fill {_meter_tone(cap_pct, good_when_high=True)}" '
            f'style="width:{cap_pct*100:.1f}%"></div></div>'
            f'<div class="nm-meter-head" style="margin-top:0.35rem"><span class="nm-meter-label">Desk load</span>'
            f'<span class="nm-meter-value">{load_pct}%</span></div>'
            f'<div class="nm-meter-track"><div class="nm-meter-fill {_meter_tone(load_pct/100.0, good_when_high=False)}" '
            f'style="width:{load_pct}%"></div></div>'
            f"</div></div>"
        )
    cards_html.append("</div>")
    st.markdown("".join(cards_html), unsafe_allow_html=True)

    chosen = st.radio("Assign to", labels, key=key, horizontal=True)
    picked = by_label.get(chosen) or {}
    return int(picked["user_id"]) if picked.get("user_id") else None


def target_id(row: dict | None, keys: tuple[str, ...], label: str, key: str) -> int | None:
    chosen = pick_id(row, keys)
    if chosen is not None:
        title = (row or {}).get("title") or (row or {}).get("name")
        if title:
            st.caption(f"Selected · **{title}**")
        else:
            st.caption("Selected")
        return chosen
    st.caption(f"Select a {label.lower()} above to continue.")
    return None


def metrics(items: dict[str, Any]) -> None:
    """Backward-compatible alias → KPI cards."""
    kpi_row(items)


def bar(data: dict[str, Any] | None, *, caption: str | None = None) -> None:
    numeric = {str(k): float(v) for k, v in (data or {}).items() if isinstance(v, (int, float))}
    if not numeric:
        return
    df = pd.DataFrame({"label": list(numeric.keys()), "value": list(numeric.values())})
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, color="#1F4E79")
        .encode(
            x=alt.X("value:Q", title=None),
            y=alt.Y("label:N", sort="-x", title=None),
            tooltip=["label:N", alt.Tooltip("value:Q", format=".0f")],
        )
        .properties(height=max(140, 28 * len(numeric)), title=caption or None)
    )
    st.altair_chart(chart, use_container_width=True)


def raw(data: Any, label: str = "Technical details") -> None:
    if data is not None:
        with st.expander(label):
            st.json(data, expanded=2)
