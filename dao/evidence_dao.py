"""Evidence DAO — table evidence."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.content.evidence import Evidence
from utils.errors import NotFoundError, ValidationError
from utils.validators import (
    require_nonempty,
    require_optional_positive_id,
    require_optional_str,
    require_positive_id,
    require_title,
)


class EvidenceDAO(BaseDAO):
    table = "evidence"

    def create(self, evidence: Evidence) -> int:
        title = require_title(evidence.title)
        # DB column remains ocr_text for compatibility; app stores plain body_text only (no OCR).
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO evidence (
                    content_id, title, evidence_type, source_url, file_path, ocr_text, uploaded_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING evidence_id
                """,
                (
                    require_positive_id(evidence.content_id, "Content ID"),
                    title,
                    require_optional_str(evidence.evidence_type, "Evidence type", max_len=64)
                    or "document",
                    require_optional_str(evidence.source_url, "Source URL"),
                    require_optional_str(evidence.file_path, "File path"),
                    require_optional_str(evidence.body_text, "Evidence text"),
                    require_optional_positive_id(evidence.uploaded_by, "Uploaded by"),
                ),
            )
            return int(cur.fetchone()["evidence_id"])

    def read(self, evidence_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id("evidence_id", require_positive_id(evidence_id, "Evidence ID"))

    def require(self, evidence_id: int) -> dict[str, Any]:
        row = self.read(evidence_id)
        if not row:
            raise NotFoundError(f"Evidence ID {evidence_id} was not found.")
        return row

    def update(self, evidence_id: int, **fields: Any) -> int:
        self.require(evidence_id)
        if "body_text" in fields:
            fields = {**fields, "ocr_text": fields.pop("body_text")}
        allowed = {"title", "evidence_type", "source_url", "file_path", "ocr_text", "uploaded_by"}
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "title" in cols:
            cols["title"] = require_title(cols["title"])
        if "evidence_type" in cols:
            cols["evidence_type"] = require_nonempty(cols["evidence_type"], "Evidence type")
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE evidence SET {sets} WHERE evidence_id = %s",
                (*cols.values(), evidence_id),
            )
        )

    def delete(self, evidence_id: int) -> int:
        self.require(evidence_id)
        return self.delete_by_id("evidence_id", evidence_id)

    def list_for_content(self, content_id: int) -> list[dict[str, Any]]:
        cid = require_positive_id(content_id, "Content ID")
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT evidence_id, content_id, title, evidence_type, source_url,
                       file_path, ocr_text AS body_text, uploaded_by, uploaded_at
                FROM evidence
                WHERE content_id = %s
                ORDER BY evidence_id
                """,
                (cid,),
            )
            return [dict(r) for r in (cur.fetchall() or [])]
