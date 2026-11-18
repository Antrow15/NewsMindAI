"""Remove exact / normalized-title duplicates."""

from __future__ import annotations

from typing import Any

from cleaners.stages.base_cleaner import BaseCleaner, CleanerResult
from utils.helpers import normalize_key


class DuplicateCleaner(BaseCleaner):
    name = "duplicate_cleaner"

    def clean(self, records: list[dict[str, Any]]) -> CleanerResult:
        kept: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in records:
            key = normalize_key(str(row.get("title") or ""))
            if not key:
                rejected.append({**row, "_reject_reason": "empty_title_key"})
                continue
            if key in seen:
                rejected.append({**row, "_reject_reason": "duplicate_title"})
                continue
            seen.add(key)
            kept.append(row)
        return CleanerResult(
            kept=kept,
            rejected=rejected,
            stats={
                "input": len(records),
                "kept": len(kept),
                "rejected": len(rejected),
                "unique_titles": len(seen),
            },
        )
