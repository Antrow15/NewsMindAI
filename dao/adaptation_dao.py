"""CAE adaptation tables — requests, drafts, reviews, finals."""

from __future__ import annotations

import json
from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from utils.errors import NotFoundError, ValidationError
from utils.validators import require_nonempty, require_positive_id, require_title


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {})


class AdaptationDAO(BaseDAO):
    table = "adaptation_requests"

    def create_request(
        self,
        *,
        original_title: str,
        original_content: str,
        created_by: int | None,
        status: str = "PROCESSING",
    ) -> int:
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO adaptation_requests (
                    original_title, original_content, created_by, status
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (
                    require_title(original_title),
                    require_nonempty(original_content, "Original content"),
                    created_by,
                    require_nonempty(status, "Status"),
                ),
            )
            return int(cur.fetchone()["id"])

    def update_request_status(self, request_id: int, status: str) -> int:
        request_id = require_positive_id(request_id, "Request ID")
        return int(
            self.execute(
                """
                UPDATE adaptation_requests
                SET status = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (require_nonempty(status, "Status"), request_id),
            )
        )

    def get_request(self, request_id: int) -> Optional[dict[str, Any]]:
        request_id = require_positive_id(request_id, "Request ID")
        with db_cursor() as cur:
            cur.execute("SELECT * FROM adaptation_requests WHERE id = %s", (request_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def require_request(self, request_id: int) -> dict[str, Any]:
        row = self.get_request(request_id)
        if not row:
            raise NotFoundError(f"Adaptation request {request_id} was not found.")
        return row

    def list_drafts_for_request(self, request_id: int) -> list[dict[str, Any]]:
        request_id = require_positive_id(request_id, "Request ID")
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT * FROM adaptation_drafts
                WHERE request_id = %s
                ORDER BY platform, version_number
                """,
                (request_id,),
            )
            return [dict(r) for r in cur.fetchall() or []]

    def create_draft(
        self,
        *,
        request_id: int,
        platform: str,
        version_number: int,
        adapted_title: str,
        adapted_content: str,
        model_version: str,
        status: str,
        parent_draft_id: int | None = None,
        generation_parameters: dict | None = None,
        validation_flags: dict | None = None,
    ) -> int:
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO adaptation_drafts (
                    request_id, platform, version_number, adapted_title, adapted_content,
                    model_version, status, parent_draft_id, generation_parameters, validation_flags
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                RETURNING id
                """,
                (
                    require_positive_id(request_id, "Request ID"),
                    require_nonempty(platform, "Platform"),
                    int(version_number),
                    require_title(adapted_title),
                    require_nonempty(adapted_content, "Adapted content"),
                    require_nonempty(model_version, "Model version"),
                    require_nonempty(status, "Status"),
                    parent_draft_id,
                    _json(generation_parameters),
                    _json(validation_flags),
                ),
            )
            return int(cur.fetchone()["id"])

    def get_draft(self, draft_id: int) -> Optional[dict[str, Any]]:
        draft_id = require_positive_id(draft_id, "Draft ID")
        with db_cursor() as cur:
            cur.execute("SELECT * FROM adaptation_drafts WHERE id = %s", (draft_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def require_draft(self, draft_id: int) -> dict[str, Any]:
        row = self.get_draft(draft_id)
        if not row:
            raise NotFoundError(f"Adaptation draft {draft_id} was not found.")
        return row

    def update_draft_status(self, draft_id: int, status: str) -> int:
        draft_id = require_positive_id(draft_id, "Draft ID")
        return int(
            self.execute(
                "UPDATE adaptation_drafts SET status = %s WHERE id = %s",
                (require_nonempty(status, "Status"), draft_id),
            )
        )

    def list_versions(self, request_id: int, platform: str) -> list[dict[str, Any]]:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT * FROM adaptation_drafts
                WHERE request_id = %s AND platform = %s
                ORDER BY version_number
                """,
                (require_positive_id(request_id, "Request ID"), require_nonempty(platform, "Platform")),
            )
            return [dict(r) for r in cur.fetchall() or []]

    def add_review(
        self,
        *,
        draft_id: int,
        action: str,
        reviewed_by: int | None,
        remarks: str | None = None,
    ) -> int:
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO adaptation_reviews (draft_id, action, remarks, reviewed_by)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (
                    require_positive_id(draft_id, "Draft ID"),
                    require_nonempty(action, "Action"),
                    remarks,
                    reviewed_by,
                ),
            )
            return int(cur.fetchone()["id"])

    def save_final(
        self,
        *,
        draft_id: int,
        final_title: str,
        final_content: str,
        finalized_by: int | None,
        remarks: str | None = None,
    ) -> int:
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO final_adaptations (
                    draft_id, final_title, final_content, finalized_by, remarks
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    require_positive_id(draft_id, "Draft ID"),
                    require_title(final_title),
                    require_nonempty(final_content, "Final content"),
                    finalized_by,
                    remarks,
                ),
            )
            return int(cur.fetchone()["id"])

    def get_final_for_draft(self, draft_id: int) -> Optional[dict[str, Any]]:
        with db_cursor() as cur:
            cur.execute(
                "SELECT * FROM final_adaptations WHERE draft_id = %s",
                (require_positive_id(draft_id, "Draft ID"),),
            )
            row = cur.fetchone()
            return dict(row) if row else None
