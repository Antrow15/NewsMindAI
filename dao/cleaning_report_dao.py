"""DAO for cleaning_report — quality reports in DB."""

from __future__ import annotations

import json
from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from utils.validators import require_nonempty, require_optional_positive_id, require_positive_id


class CleaningReportDAO(BaseDAO):
    table = "cleaning_report"

    def create(
        self,
        *,
        report_type: str,
        report: dict[str, Any],
        input_count: int,
        kept_count: int,
        rejected_count: int,
        source_files: str = "",
        created_by: int | None = None,
    ) -> int:
        report_type = require_nonempty(report_type, "Report type").lower()
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO cleaning_report (
                    report_type, source_files, input_count, kept_count, rejected_count,
                    report_json, created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                RETURNING cleaning_report_id
                """,
                (
                    report_type,
                    source_files or None,
                    int(input_count),
                    int(kept_count),
                    int(rejected_count),
                    json.dumps(report),
                    require_optional_positive_id(created_by, "Created by"),
                ),
            )
            return int(cur.fetchone()["cleaning_report_id"])

    def read(self, cleaning_report_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id(
            "cleaning_report_id",
            require_positive_id(cleaning_report_id, "Cleaning report ID"),
        )

    def list_recent(self, limit: int = 20, report_type: str | None = None) -> list[dict[str, Any]]:
        if report_type:
            rows = self.execute(
                """
                SELECT cleaning_report_id, report_type, source_files, input_count,
                       kept_count, rejected_count, created_by, created_at
                FROM cleaning_report
                WHERE report_type = %s
                ORDER BY cleaning_report_id DESC
                LIMIT %s
                """,
                (report_type, limit),
                fetch="all",
            )
        else:
            rows = self.execute(
                """
                SELECT cleaning_report_id, report_type, source_files, input_count,
                       kept_count, rejected_count, created_by, created_at
                FROM cleaning_report
                ORDER BY cleaning_report_id DESC
                LIMIT %s
                """,
                (limit,),
                fetch="all",
            )
        return [dict(r) for r in rows or []]
