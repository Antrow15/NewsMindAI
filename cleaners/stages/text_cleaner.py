"""Normalize text fields — whitespace, HTML noise."""

from __future__ import annotations

import re
from typing import Any

from cleaners.stages.base_cleaner import BaseCleaner, CleanerResult
from utils.helpers import coerce_str


def _scrub(text: str) -> str:
    text = coerce_str(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


class TextCleaner(BaseCleaner):
    name = "text_cleaner"

    def clean(self, records: list[dict[str, Any]]) -> CleanerResult:
        kept: list[dict[str, Any]] = []
        for row in records:
            out = dict(row)
            out["title"] = _scrub(str(out.get("title") or ""))
            body = _scrub(str(out.get("text") or out.get("content_body") or ""))
            out["text"] = body
            out["content_body"] = body
            if out.get("summary"):
                out["summary"] = _scrub(str(out["summary"]))
            if out.get("category"):
                out["category"] = _scrub(str(out["category"]))
            kept.append(out)
        return CleanerResult(
            kept=kept,
            rejected=[],
            stats={"input": len(records), "kept": len(kept), "rejected": 0},
        )
