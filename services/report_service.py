"""Persist and read cleaning quality reports from DB."""

from __future__ import annotations

from typing import Any

from dao.cleaning_report_dao import CleaningReportDAO
from utils.errors import NotFoundError
from utils.validators import require_positive_id


class ReportService:
    def __init__(self) -> None:
        self.dao = CleaningReportDAO()

    def save_cleaning_report(
        self,
        *,
        report_type: str,
        result: dict[str, Any],
        source_files: list[str] | str | None = None,
        created_by: int | None = None,
    ) -> int:
        if isinstance(source_files, list):
            source_text = ", ".join(source_files)
        else:
            source_text = source_files or ""
        stats = result.get("stats") or {}
        report = result.get("report") or {}
        return self.dao.create(
            report_type=report_type,
            report=report,
            input_count=int(stats.get("input") or 0),
            kept_count=int(stats.get("kept") or 0),
            rejected_count=int(stats.get("rejected") or 0),
            source_files=source_text,
            created_by=created_by,
        )

    def list_recent(self, limit: int = 15) -> list[dict[str, Any]]:
        return self.dao.list_recent(limit=limit)

    def get(self, report_id: int) -> dict[str, Any]:
        row = self.dao.read(require_positive_id(report_id, "Report ID"))
        if not row:
            raise NotFoundError(f"Cleaning report ID {report_id} was not found.")
        return row
