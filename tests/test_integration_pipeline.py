from __future__ import annotations

import pytest

from cleaners.orchestrator import CleaningOrchestrator
from config.constants import DEMO_PASSWORDS
from modules.admin import AdminModule
from modules.authentication import authenticate, logout
from services.persistence_service import PersistenceService


def test_clean_and_persist_inline_fixture(db_ready, tmp_path):
    rows = [
        {
            "title": "Integration fixture: civic coverage follow-up",
            "text": (
                "Inline test body long enough for cleaner schema checks so the persistence "
                "layer can store a cleaned content row through DAO."
            ),
            "_raw_text": "raw inline body before clean",
            "category": "City",
            "date": "2026-11-02",
            "status": "draft",
            "content_kind": "article",
            "source_type": "test",
        }
    ]
    pitches = [
        {
            "title": "Integration pitch: coverage gap on civic response",
            "summary": "Test pitch summary with enough detail for editorial follow-up assignment.",
            "text": "Pitch body with enough characters for schema cleaner when record_type is pitch.",
            "status": "submitted",
            "source_type": "test",
            "trend_score": 0.5,
            "audience_interest_score": 0.5,
            "coverage_gap_score": 0.5,
        }
    ]
    cleaned_content = CleaningOrchestrator(processed_dir=tmp_path).clean_content(rows)
    cleaned_pitches = CleaningOrchestrator(processed_dir=tmp_path).clean_pitches(pitches)
    assert cleaned_content["stats"]["kept"] == 1

    persist = PersistenceService()
    content_ids = persist.persist_content(cleaned_content["kept"])
    pitch_ids = persist.persist_pitches(cleaned_pitches["kept"])
    assert len(content_ids) == 1
    assert len(pitch_ids) == 1


def test_admin_pipeline_persists_raw_and_clean(db_ready):
    authenticate("admin", DEMO_PASSWORDS["admin"])
    try:
        admin = AdminModule()
        files = admin.list_csv_files()["all_files"]
        assert files
        # Single-file path keeps CI bounded while still exercising DB persist
        loaded = admin.ingest_file(files[0], store_raw=True)
        cleaned = admin.clean(
            records=loaded["records"][:40],
            pitches=[],
            source_files=loaded["source_files"],
        )
        result = admin.persist(cleaned)
        assert result["actor"] == "admin"
        assert "persisted_content" in result
        assert "rejected_raw_stored" in result
        assert cleaned.get("cleaning_report_id")
    finally:
        logout()
