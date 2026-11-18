"""Persist raw ingest rows and cleaned content into Postgres."""

from __future__ import annotations

from typing import Any

from entities.content.content import Content
from entities.content.evidence import Evidence
from entities.content.story_pitch import StoryPitch
from repository.content_repository import ContentRepository
from repository.user_repository import UserRepository
from utils.logger import get_logger
from utils.progress import progress
from utils.validators import require_content_status, require_pitch_status, validate_content_record

log = get_logger("persistence")


class PersistenceService:
    def __init__(
        self,
        content_repo: ContentRepository | None = None,
        user_repo: UserRepository | None = None,
    ) -> None:
        self.content_repo = content_repo or ContentRepository()
        self.user_repo = user_repo or UserRepository()

    def persist_raw_records(self, records: list[dict[str, Any]], *, cleaning_status: str = "pending") -> list[int]:
        payload = []
        for row in records:
            payload.append(
                {
                    "source_file": str(
                        row.get("_source_file") or row.get("source_dataset") or row.get("source_type") or "csv"
                    )[:256],
                    "title": str(row.get("title") or ""),
                    "raw_text": str(row.get("_raw_text") or row.get("text") or row.get("content_body") or ""),
                    "category": str(row.get("category") or "")[:128],
                    "date": str(row.get("date") or row.get("published_date") or "")[:64],
                    "source_type": str(row.get("source_type") or "")[:128],
                    "cleaning_status": cleaning_status,
                    "reject_reason": row.get("_reject_reason"),
                    "content_id": row.get("content_id"),
                }
            )
        if payload:
            progress(
                f"Writing {len(payload)} raw_ingest row(s) "
                f"(status={cleaning_status})..."
            )
        ids = self.content_repo.raw.create_many(payload)
        log.info("Persisted %s raw ingest rows (status=%s)", len(ids), cleaning_status)
        return ids

    def persist_content(self, records: list[dict[str, Any]]) -> list[int]:
        self.user_repo.ensure_demo_user()
        ids: list[int] = []
        total = len(records)
        if total:
            progress(f"Saving cleaned content to database ({total} row(s))...")
        for index, row in enumerate(records, start=1):
            if index == 1 or index % 50 == 0 or index == total:
                progress(f"  content row {index}/{total}...")

            errors = validate_content_record(row)
            if errors:
                log.warning("Skip persist content errors=%s title=%s", errors, row.get("title"))
                self.persist_raw_records(
                    [{**row, "_reject_reason": ",".join(errors)}],
                    cleaning_status="rejected",
                )
                continue

            category = str(row.get("category_name") or row.get("category") or "").strip()
            body = str(row.get("content_body") or row.get("text") or "")
            raw_body = str(row.get("_raw_text") or row.get("text") or body)
            summary = str(row.get("summary") or "").strip()
            if not summary and category:
                summary = f"[{category}] {body[:200]}"
            elif not summary:
                summary = body[:240] or None

            status = require_content_status(str(row.get("status") or "draft"))
            content = Content(
                title=str(row["title"]),
                content_body=body,
                raw_body=raw_body,
                summary=summary,
                status=status,
                content_kind=str(row.get("content_kind") or "article"),
                source_type=str(row.get("source_type") or row.get("source_dataset") or "pipeline"),
            )
            content_id = self.content_repo.save_content_bundle(
                content,
                event_location=str(row.get("event_location") or category or ""),
            )
            ids.append(content_id)
            source = str(row.get("source_type") or row.get("source_dataset") or "pipeline")
            self.content_repo.save_evidence(
                Evidence(
                    content_id=content_id,
                    title=f"Ingest note for {content.title[:40]}",
                    evidence_type="ingest_log",
                    body_text=f"Persisted from source={source}",
                )
            )
            self.persist_raw_records(
                [{**row, "content_id": content_id}],
                cleaning_status="kept",
            )
        log.info("Persisted %s cleaned content rows", len(ids))
        return ids

    def persist_rejected(self, records: list[dict[str, Any]]) -> list[int]:
        return self.persist_raw_records(records, cleaning_status="rejected")

    def persist_pitches(self, records: list[dict[str, Any]]) -> list[int]:
        ids: list[int] = []
        for row in records:
            status = require_pitch_status(str(row.get("status") or "submitted"))
            title = str(row.get("title") or "").strip()
            summary = str(row.get("summary") or row.get("text") or title or "Pipeline pitch")[:500]
            pitch = StoryPitch(
                title=title,
                summary=summary,
                priority=str(row.get("priority") or "medium"),
                trend_score=float(row.get("trend_score") or 0),
                audience_interest_score=float(row.get("audience_interest_score") or 0),
                coverage_gap_score=float(row.get("coverage_gap_score") or 0),
                status=status,
                source_type=str(row.get("source_type") or "pipeline"),
            )
            ids.append(self.content_repo.save_pitch(pitch))
        log.info("Persisted %s pitch rows", len(ids))
        return ids
