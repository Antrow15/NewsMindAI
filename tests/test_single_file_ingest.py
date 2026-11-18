from __future__ import annotations

import pytest

from config.constants import DEMO_PASSWORDS
from modules.admin import AdminModule
from modules.authentication import authenticate, logout
from services.ingestion_service import IngestionService
from services.report_service import ReportService
from utils.helpers import project_path


def test_single_file_ingest_registers_hash(db_ready, tmp_path):
    csv_path = tmp_path / "extra_story.csv"
    csv_path.write_text(
        "title,text,category\n"
        "Single file civic update story,"
        "Body long enough for schema cleaner validation during single-file ingest tests,"
        "City\n",
        encoding="utf-8",
    )
    svc = IngestionService(raw_dir=tmp_path)
    first = svc.ingest_one("extra_story.csv")
    assert first["usable_row_count"] == 1
    assert first["source_files"] == ["extra_story.csv"]
    assert svc.file_needs_ingest("extra_story.csv") is False
    assert svc.list_new_or_changed_files() == []

    csv_path.write_text(
        "title,text,category\n"
        "Single file civic update story,"
        "Body long enough for schema cleaner validation during single-file ingest tests,"
        "City\n"
        "Another single file follow-up story,"
        "Second body long enough for schema cleaner validation during single-file ingest,"
        "City\n",
        encoding="utf-8",
    )
    assert svc.file_needs_ingest("extra_story.csv") is True
    second = svc.ingest_all_content(only_new=True)
    assert second["source_files"] == ["extra_story.csv"]
    assert second["collections"]["list_count"] == 2


def test_admin_pipeline_file_and_report(db_ready, tmp_path, monkeypatch):
    raw = project_path("data", "raw")
    files = sorted(p.relative_to(raw).as_posix() for p in raw.rglob("*.csv") if p.is_file())
    if not files:
        pytest.skip("No CSV files in data/raw")
    # Prefer a small-ish top-level sample if present
    target = next((f for f in files if "/" not in f), files[0])

    authenticate("admin", DEMO_PASSWORDS["admin"])
    try:
        admin = AdminModule()
        # Use only_new listing path + single file ingest without full tree persist cost
        loaded = admin.ingest_file(target, store_raw=False)
        assert target in loaded["source_files"]
        cleaned = admin.clean(
            records=loaded["records"][:25],
            pitches=[],
            source_files=loaded["source_files"],
        )
        assert cleaned.get("cleaning_report_id")
        report = ReportService().get(cleaned["cleaning_report_id"])
        assert report["report_type"] == "content"
        assert report["input_count"] == cleaned["content_stats"]["input"]
        listed = admin.list_reports(limit=5)
        assert any(
            r["cleaning_report_id"] == cleaned["cleaning_report_id"]
            for r in listed["reports"]
        )
    finally:
        logout()
