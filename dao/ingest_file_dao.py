"""DAO for ingest_file — CSV file registry."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from utils.validators import require_nonempty


class IngestFileDAO(BaseDAO):
    table = "ingest_file"

    def upsert(
        self,
        *,
        source_file: str,
        file_hash: str,
        row_count: int,
        usable_row_count: int,
        last_status: str = "ingested",
    ) -> int:
        source_file = require_nonempty(source_file, "Source file")
        file_hash = require_nonempty(file_hash, "File hash")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO ingest_file (
                    source_file, file_hash, row_count, usable_row_count, last_status, last_ingested_at
                )
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (source_file) DO UPDATE
                SET file_hash = EXCLUDED.file_hash,
                    row_count = EXCLUDED.row_count,
                    usable_row_count = EXCLUDED.usable_row_count,
                    last_status = EXCLUDED.last_status,
                    last_ingested_at = NOW()
                RETURNING ingest_file_id
                """,
                (source_file, file_hash, int(row_count), int(usable_row_count), last_status),
            )
            return int(cur.fetchone()["ingest_file_id"])

    def get_by_source(self, source_file: str) -> Optional[dict[str, Any]]:
        row = self.execute(
            "SELECT * FROM ingest_file WHERE source_file = %s",
            (source_file,),
            fetch="one",
        )
        return dict(row) if row else None

    def list_all(self, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.execute(
            """
            SELECT * FROM ingest_file
            ORDER BY last_ingested_at DESC
            LIMIT %s
            """,
            (limit,),
            fetch="all",
        )
        return [dict(r) for r in rows or []]
