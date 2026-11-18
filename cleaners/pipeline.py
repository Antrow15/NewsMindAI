"""Ordered cleaner chain."""

from __future__ import annotations

from typing import Any

from cleaners.quality_report import QualityReport
from cleaners.stages import (
    BaseCleaner,
    CleanerResult,
    DuplicateCleaner,
    NullCleaner,
    SchemaCleaner,
    TextCleaner,
)


class CleaningPipeline:
    def __init__(self, cleaners: list[BaseCleaner] | None = None, record_type: str = "content") -> None:
        self.cleaners = cleaners or [
            TextCleaner(),
            NullCleaner(),
            DuplicateCleaner(),
            SchemaCleaner(record_type=record_type),
        ]
        self.report = QualityReport()

    def run(self, records: list[dict[str, Any]]) -> CleanerResult:
        from utils.progress import progress

        current = list(records)
        all_rejected: list[dict[str, Any]] = []
        input_count = len(records)
        progress(f"Cleaner chain starting ({input_count} row(s), {len(self.cleaners)} stage(s))...")
        for cleaner in self.cleaners:
            progress(f"  Stage: {cleaner.name} ({len(current)} row(s) in)...")
            result = cleaner.clean(current)
            self.report.add_stage(cleaner.name, result.stats, result.rejected)
            all_rejected.extend(result.rejected)
            current = result.kept
            progress(
                f"  Stage {cleaner.name} done: kept={len(result.kept)} "
                f"rejected={len(result.rejected)}"
            )
        self.report.finalize(input_count, len(current))
        progress(
            f"Cleaner chain finished: kept={len(current)} rejected={len(all_rejected)}"
        )
        return CleanerResult(
            kept=current,
            rejected=all_rejected,
            stats={
                "input": input_count,
                "kept": len(current),
                "rejected": len(all_rejected),
            },
        )
