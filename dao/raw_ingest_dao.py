"""Raw ingest DAO — table raw_ingest (CSV rows before/after cleaning)."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor


class RawIngestDAO(BaseDAO):
    table = "raw_ingest"

    def create(
        self,
        *,
        source_file: str,
        title: str = "",
        raw_text: str = "",
        category: str = "",
        published_date: str = "",
        source_type: str = "",
        cleaning_status: str = "pending",
        reject_reason: str | None = None,
        content_id: int | None = None,
    ) -> int:
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO raw_ingest (
                    source_file, title, raw_text, category, published_date,
                    source_type, cleaning_status, reject_reason, content_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING raw_ingest_id
                """,
                (
                    source_file,
                    title or None,
                    raw_text or None,
                    category or None,
                    published_date or None,
                    source_type or None,
                    cleaning_status,
                    reject_reason,
                    content_id,
                ),
            )
            return int(cur.fetchone()["raw_ingest_id"])

    def create_many(self, rows: list[dict[str, Any]]) -> list[int]:
        """Bulk insert in batches (one connection per batch)."""
        from config.runtime import db_insert_batch
        from utils.progress import progress

        if not rows:
            return []
        batch_size = db_insert_batch()
        ids: list[int] = []
        total_batches = (len(rows) + batch_size - 1) // batch_size
        sql = """
            INSERT INTO raw_ingest (
                source_file, title, raw_text, category, published_date,
                source_type, cleaning_status, reject_reason, content_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING raw_ingest_id
            """
        for batch_no, start in enumerate(range(0, len(rows), batch_size), start=1):
            batch = rows[start : start + batch_size]
            progress(f"DB insert batch {batch_no}/{total_batches} ({len(batch)} row(s))...")
            with db_cursor() as cur:
                for row in batch:
                    cur.execute(
                        sql,
                        (
                            str(row.get("source_file") or row.get("source_type") or "csv"),
                            str(row.get("title") or "") or None,
                            str(row.get("raw_text") or row.get("text") or row.get("_raw_text") or "") or None,
                            str(row.get("category") or "") or None,
                            str(row.get("date") or row.get("published_date") or "") or None,
                            str(row.get("source_type") or "") or None,
                            str(row.get("cleaning_status") or "pending"),
                            row.get("reject_reason") or row.get("_reject_reason"),
                            row.get("content_id"),
                        ),
                    )
                    ids.append(int(cur.fetchone()["raw_ingest_id"]))
        return ids

    def read(self, raw_ingest_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id("raw_ingest_id", raw_ingest_id)

    def update_status(
        self,
        raw_ingest_id: int,
        cleaning_status: str,
        *,
        reject_reason: str | None = None,
        content_id: int | None = None,
    ) -> int:
        return int(
            self.execute(
                """
                UPDATE raw_ingest
                SET cleaning_status = %s,
                    reject_reason = COALESCE(%s, reject_reason),
                    content_id = COALESCE(%s, content_id)
                WHERE raw_ingest_id = %s
                """,
                (cleaning_status, reject_reason, content_id, raw_ingest_id),
            )
        )

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.execute(
            """
            SELECT raw_ingest_id, source_file, title, category, cleaning_status,
                   reject_reason, content_id, ingested_at
            FROM raw_ingest
            ORDER BY raw_ingest_id DESC
            LIMIT %s
            """,
            (limit,),
            fetch="all",
        )
        return [dict(r) for r in rows or []]

    def count_by_status(self) -> dict[str, int]:
        rows = self.execute(
            """
            SELECT cleaning_status, COUNT(*) AS cnt
            FROM raw_ingest
            GROUP BY cleaning_status
            """,
            fetch="all",
        )
        return {str(r["cleaning_status"]): int(r["cnt"]) for r in rows or []}
