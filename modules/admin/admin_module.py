"""Admin / pipeline feature module."""

from __future__ import annotations

from typing import Any, Optional

from cleaners.orchestrator import CleaningOrchestrator
from config.constants import CAP_CLEAN, CAP_INGEST, CAP_PERSIST, CAP_PIPELINE
from config.runtime import pipeline_file_by_file
from services.access import require_capability_session
from services.ingestion_service import IngestionService
from services.persistence_service import PersistenceService
from services.report_service import ReportService
from utils.logger import get_logger
from utils.progress import progress

log = get_logger("admin")


class AdminModule:
    def __init__(
        self,
        ingestion: IngestionService | None = None,
        cleaning: CleaningOrchestrator | None = None,
        persistence: PersistenceService | None = None,
        reports: ReportService | None = None,
        session_token: str | None = None,
    ) -> None:
        self.ingestion = ingestion or IngestionService()
        self.cleaning = cleaning or CleaningOrchestrator()
        self.persistence = persistence or PersistenceService()
        self.reports = reports or ReportService()
        self.session_token = session_token

    def _cap(self, capability: str) -> dict[str, Any]:
        return require_capability_session(capability, self.session_token)

    def list_raw_ingest(self, limit: int = 20) -> dict[str, Any]:
        """ETL staging rows — admin pipeline only (not journalist desk)."""
        from services.content.content_service import ContentService

        user = self._cap(CAP_INGEST)
        content = ContentService()
        return {
            "actor": user["username"],
            "role": user.get("role_name") or user["role_code"],
            "items": content.list_raw_ingest(limit=limit),
            "counts": content.raw_ingest_counts(),
        }

    def list_csv_files(self) -> dict[str, Any]:
        user = self._cap(CAP_INGEST)
        progress("Scanning data/raw for CSV files...")
        files = self.ingestion.list_csv_files()
        new_files = self.ingestion.list_new_or_changed_files()
        progress(
            f"Found {len(files)} CSV file(s); {len(new_files)} new or changed."
        )
        return {
            "actor": user["username"],
            "role": user.get("role_name") or user["role_code"],
            "all_files": files,
            "new_or_changed": new_files,
            "registered": self.ingestion.registered_files(),
        }

    def ingest(self, *, only_new: bool = False, store_raw: bool = True) -> dict[str, Any]:
        user = self._cap(CAP_INGEST)
        mode = "new/changed only" if only_new else "all CSV files"
        progress(f"Ingest started ({mode})...")
        payload = self.ingestion.ingest_all_content(only_new=only_new)
        pitches = self.ingestion.ingest_pitches() if not only_new else []
        raw_ids: list[int] = []
        if store_raw and payload["records"]:
            progress(f"Storing {len(payload['records'])} raw row(s) in database...")
            raw_ids = self.persistence.persist_raw_records(
                payload["records"], cleaning_status="pending"
            )
            progress(f"Raw ingest stored: {len(raw_ids)} row(s).")
        progress(
            f"Ingest finished: {len(payload['records'])} content row(s), "
            f"{len(pitches)} pitch row(s), {len(payload.get('source_files') or [])} file(s)."
        )
        return {
            "actor": user["username"],
            "role": user.get("role_name") or user["role_code"],
            "content_rows": len(payload["records"]),
            "pitch_rows": len(pitches),
            "source_files": payload.get("source_files") or [],
            "collections": payload["collections"],
            "raw_ingest_ids": raw_ids,
            "message": payload.get("message"),
            "records": payload["records"],
            "pitches": pitches,
        }

    def ingest_file(self, source_file: str, *, store_raw: bool = True) -> dict[str, Any]:
        user = self._cap(CAP_INGEST)
        progress(f"Ingesting file: {source_file}")
        payload = self.ingestion.ingest_one(source_file)
        raw_ids: list[int] = []
        if store_raw and payload["records"]:
            progress(f"Storing {len(payload['records'])} raw row(s) in database...")
            raw_ids = self.persistence.persist_raw_records(
                payload["records"], cleaning_status="pending"
            )
            progress(f"Raw ingest stored: {len(raw_ids)} row(s).")
        progress(
            f"File ingest finished: {source_file} → "
            f"{payload.get('usable_row_count', len(payload['records']))} usable row(s)."
        )
        return {
            "actor": user["username"],
            "role": user.get("role_name") or user["role_code"],
            "content_rows": len(payload["records"]),
            "pitch_rows": 0,
            "source_files": payload["source_files"],
            "collections": payload["collections"],
            "raw_ingest_ids": raw_ids,
            "records": payload["records"],
            "pitches": [],
        }

    def clean(
        self,
        records: Optional[list[dict[str, Any]]] = None,
        pitches: Optional[list[dict[str, Any]]] = None,
        *,
        source_files: list[str] | None = None,
    ) -> dict[str, Any]:
        user = self._cap(CAP_CLEAN)
        if records is None:
            progress("Loading CSV data for cleaning...")
            loaded = self.ingestion.ingest_all_content(only_new=False)
            records = loaded["records"]
            source_files = source_files or loaded.get("source_files")
        if pitches is None:
            pitches = self.ingestion.ingest_pitches()

        progress(f"Cleaning {len(records)} content row(s)...")
        content_result = self.cleaning.clean_content(records)
        progress(
            f"Content clean done: kept={content_result['stats'].get('kept')} "
            f"rejected={content_result['stats'].get('rejected')}"
        )
        progress(f"Cleaning {len(pitches)} pitch row(s)...")
        pitch_result = self.cleaning.clean_pitches(pitches)
        progress(
            f"Pitch clean done: kept={pitch_result['stats'].get('kept')} "
            f"rejected={pitch_result['stats'].get('rejected')}"
        )
        progress("Saving cleaning report to database...")
        report_id = self.reports.save_cleaning_report(
            report_type="content",
            result=content_result,
            source_files=source_files or [],
            created_by=user.get("user_id"),
        )
        pitch_report_id = None
        if pitches:
            pitch_report_id = self.reports.save_cleaning_report(
                report_type="pitch",
                result=pitch_result,
                source_files=source_files or ["pitches.csv"],
                created_by=user.get("user_id"),
            )
        progress(f"Cleaning report saved (id={report_id}).")
        return {
            "actor": user["username"],
            "role": user.get("role_name") or user["role_code"],
            "content_stats": content_result["stats"],
            "pitch_stats": pitch_result["stats"],
            "content_report": content_result.get("report_path"),
            "cleaned_csv": content_result.get("cleaned_csv"),
            "cleaning_report_id": report_id,
            "pitch_report_id": pitch_report_id,
            "content": content_result,
            "pitches": pitch_result,
        }

    def ingest_and_clean(self, *, only_new: bool = False, store_raw: bool = True) -> dict[str, Any]:
        self._cap(CAP_CLEAN)
        loaded = self.ingest(only_new=only_new, store_raw=store_raw)
        cleaned = self.clean(
            records=loaded["records"],
            pitches=loaded["pitches"],
            source_files=loaded.get("source_files"),
        )
        return {
            "actor": cleaned["actor"],
            "role": cleaned["role"],
            "ingest": {
                "content_rows": loaded["content_rows"],
                "pitch_rows": loaded["pitch_rows"],
                "source_files": loaded["source_files"],
                "collections": loaded["collections"],
                "raw_stored": len(loaded.get("raw_ingest_ids") or []),
                "message": loaded.get("message"),
            },
            "content_stats": cleaned["content_stats"],
            "pitch_stats": cleaned["pitch_stats"],
            "content_report": cleaned["content_report"],
            "cleaned_csv": cleaned["cleaned_csv"],
            "cleaning_report_id": cleaned["cleaning_report_id"],
            "content": cleaned["content"],
            "pitches": cleaned["pitches"],
        }

    def pipeline_file(self, source_file: str) -> dict[str, Any]:
        self._cap(CAP_PIPELINE)
        progress(f"Pipeline for file: {source_file}")
        loaded = self.ingest_file(source_file, store_raw=True)
        cleaned = self.clean(
            records=loaded["records"],
            pitches=[],
            source_files=loaded["source_files"],
        )
        persisted = self.persist(cleaned)
        progress(
            f"Pipeline finished for {source_file}: "
            f"persisted={persisted['persisted_content']} "
            f"rejected_raw={persisted['rejected_raw_stored']}"
        )
        return {
            "actor": persisted["actor"],
            "role": persisted["role"],
            "source_files": loaded["source_files"],
            "ingest": {
                "content_rows": loaded["content_rows"],
                "source_files": loaded["source_files"],
                "collections": loaded["collections"],
            },
            "content_stats": cleaned["content_stats"],
            "cleaning_report_id": cleaned["cleaning_report_id"],
            "persisted_content": persisted["persisted_content"],
            "rejected_raw_stored": persisted["rejected_raw_stored"],
        }

    def persist(self, cleaned: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        user = self._cap(CAP_PERSIST)
        if cleaned is None:
            cleaned = self.ingest_and_clean(store_raw=True)
        kept = cleaned["content"]["kept"]
        rejected = cleaned["content"]["rejected"]
        pitches_kept = cleaned["pitches"]["kept"]
        progress(f"Persisting {len(kept)} cleaned content row(s)...")
        content_ids = self.persistence.persist_content(kept)
        progress(f"Persisting {len(rejected)} rejected row(s) to raw_ingest...")
        rejected_ids = self.persistence.persist_rejected(rejected)
        progress(f"Persisting {len(pitches_kept)} pitch row(s)...")
        pitch_ids = self.persistence.persist_pitches(pitches_kept)
        progress(
            f"Persist finished: content={len(content_ids)} "
            f"pitches={len(pitch_ids)} rejected_raw={len(rejected_ids)}"
        )
        return {
            "actor": user["username"],
            "role": user.get("role_name") or user["role_code"],
            "content_ids": content_ids,
            "pitch_ids": pitch_ids,
            "persisted_content": len(content_ids),
            "persisted_pitches": len(pitch_ids),
            "rejected_raw_stored": len(rejected_ids),
            "cleaning_report_id": cleaned.get("cleaning_report_id"),
        }

    def run_pipeline(self, *, only_new: bool = False) -> dict[str, Any]:
        """Full ETL. By default processes one CSV at a time with console progress."""
        self._cap(CAP_PIPELINE)
        if pipeline_file_by_file():
            files = (
                self.ingestion.list_new_or_changed_files()
                if only_new
                else self.ingestion.list_csv_files()
            )
            if only_new and not files:
                user = self._cap(CAP_PIPELINE)
                progress("No new or changed CSV files to process.")
                return {
                    "actor": user["username"],
                    "role": user.get("role_name") or user["role_code"],
                    "ingest": {
                        "content_rows": 0,
                        "pitch_rows": 0,
                        "source_files": [],
                        "message": "No new or changed CSV files to ingest.",
                    },
                    "content_stats": {"input": 0, "kept": 0, "rejected": 0},
                    "pitch_stats": {"input": 0, "kept": 0, "rejected": 0},
                    "quality_report": "",
                    "cleaning_report_id": None,
                    "persisted_content": 0,
                    "persisted_pitches": 0,
                    "rejected_raw_stored": 0,
                    "persisted_content_ids": [],
                    "persisted_pitch_ids": [],
                    "message": "No new or changed CSV files to ingest.",
                }
            totals = {
                "content_rows": 0,
                "kept": 0,
                "rejected": 0,
                "persisted_content": 0,
                "rejected_raw_stored": 0,
                "persisted_pitches": 0,
                "source_files": [],
                "content_ids": [],
                "pitch_ids": [],
                "cleaning_report_id": None,
            }
            last_actor = ""
            last_role = ""
            total_files = len(files)
            progress(f"Full pipeline starting for {total_files} file(s) (one file at a time)...")
            for index, rel in enumerate(files, start=1):
                progress(f"--- File {index}/{total_files}: {rel} ---")
                one = self.pipeline_file(rel)
                last_actor = one.get("actor") or last_actor
                last_role = one.get("role") or last_role
                totals["source_files"].append(rel)
                totals["content_rows"] += int((one.get("ingest") or {}).get("content_rows") or 0)
                stats = one.get("content_stats") or {}
                totals["kept"] += int(stats.get("kept") or 0)
                totals["rejected"] += int(stats.get("rejected") or 0)
                totals["persisted_content"] += int(one.get("persisted_content") or 0)
                totals["rejected_raw_stored"] += int(one.get("rejected_raw_stored") or 0)
                totals["cleaning_report_id"] = one.get("cleaning_report_id") or totals["cleaning_report_id"]
            pitches = self.ingestion.ingest_pitches() if not only_new else []
            pitch_ids: list[int] = []
            pitch_stats = {"input": 0, "kept": 0, "rejected": 0}
            if pitches:
                progress(f"Processing pitches.csv ({len(pitches)} row(s))...")
                pitch_clean = self.cleaning.clean_pitches(pitches)
                pitch_stats = pitch_clean["stats"]
                pitch_ids = self.persistence.persist_pitches(pitch_clean["kept"])
                totals["persisted_pitches"] = len(pitch_ids)
                progress(f"Pitches persisted: {len(pitch_ids)}")
            progress(
                f"Full pipeline complete: files={len(totals['source_files'])} "
                f"persisted_content={totals['persisted_content']} "
                f"rejected_raw={totals['rejected_raw_stored']}"
            )
            return {
                "actor": last_actor,
                "role": last_role,
                "ingest": {
                    "content_rows": totals["content_rows"],
                    "pitch_rows": len(pitches),
                    "source_files": totals["source_files"],
                    "message": f"Processed {len(totals['source_files'])} file(s) one at a time.",
                },
                "content_stats": {
                    "input": totals["content_rows"],
                    "kept": totals["kept"],
                    "rejected": totals["rejected"],
                },
                "pitch_stats": pitch_stats,
                "quality_report": "",
                "cleaning_report_id": totals["cleaning_report_id"],
                "persisted_content": totals["persisted_content"],
                "persisted_pitches": totals["persisted_pitches"],
                "rejected_raw_stored": totals["rejected_raw_stored"],
                "persisted_content_ids": totals["content_ids"],
                "persisted_pitch_ids": pitch_ids,
            }

        progress("Full pipeline started (combined mode)...")
        cleaned = self.ingest_and_clean(only_new=only_new, store_raw=True)
        persisted = self.persist(cleaned)
        progress("Full pipeline complete.")
        return {
            "actor": persisted["actor"],
            "role": persisted["role"],
            "ingest": cleaned["ingest"],
            "content_stats": cleaned["content_stats"],
            "pitch_stats": cleaned["pitch_stats"],
            "quality_report": cleaned["content_report"],
            "cleaning_report_id": cleaned.get("cleaning_report_id"),
            "persisted_content": persisted["persisted_content"],
            "persisted_pitches": persisted["persisted_pitches"],
            "rejected_raw_stored": persisted["rejected_raw_stored"],
            "persisted_content_ids": persisted["content_ids"],
            "persisted_pitch_ids": persisted["pitch_ids"],
        }

    def list_reports(self, limit: int = 15) -> dict[str, Any]:
        user = self._cap(CAP_CLEAN)
        rows = self.reports.list_recent(limit=limit)
        return {
            "actor": user["username"],
            "role": user.get("role_name") or user["role_code"],
            "reports": rows,
        }

    def view_report(self, report_id: int) -> dict[str, Any]:
        user = self._cap(CAP_CLEAN)
        row = self.reports.get(report_id)
        return {
            "actor": user["username"],
            "role": user.get("role_name") or user["role_code"],
            "report": row,
        }
