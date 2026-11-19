"""Reusable writers for concept + file/method/library explanation blocks."""

from __future__ import annotations

from docx_helpers import bullet, code, h, note, numbered, p, table


def concept_block(
    doc,
    title: str,
    *,
    meaning: str,
    why: str,
    how_works: str,
    in_project: str,
    related: str = "",
):
    h(doc, title, 2)
    h(doc, "Concept explanation", 3)
    p(doc, f"What it is: {meaning}")
    p(doc, f"Why it exists: {why}")
    p(doc, f"How it works (theory): {how_works}")
    p(doc, f"How NewsMind applies it: {in_project}")
    if related:
        p(doc, f"Related concepts: {related}", italic=True)


def file_block(
    doc,
    path: str,
    *,
    purpose: str,
    libraries: list[tuple[str, str]],
    methods: list[dict],
    calls: str,
    called_by: str,
):
    h(doc, f"File: {path}", 3)
    p(doc, f"Purpose of this file: {purpose}")
    if libraries:
        h(doc, "Libraries / imports used here", 4)
        table(
            doc,
            ["Library / module", "Why this file uses it"],
            [[a, b] for a, b in libraries],
        )
    if methods:
        h(doc, "Important functions / methods", 4)
        for m in methods:
            p(doc, f"Name: {m['name']}", bold=True)
            bullet(doc, f"Responsibility: {m['resp']}")
            if m.get("params"):
                bullet(doc, f"Parameters: {m['params']}")
            if m.get("returns"):
                bullet(doc, f"Returns: {m['returns']}")
            if m.get("calls"):
                bullet(doc, f"Calls: {m['calls']}")
            if m.get("notes"):
                bullet(doc, f"Notes: {m['notes']}")
    p(doc, f"This file calls: {calls}")
    p(doc, f"This file is called by: {called_by}")


def flow(doc, title: str, steps: list[str]):
    h(doc, title, 3)
    for s in steps:
        numbered(doc, s)
