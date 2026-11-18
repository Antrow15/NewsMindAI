"""Cleaning orchestration — pipeline run + optional local file snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from cleaners.pipeline import CleaningPipeline
from config.runtime import write_processed_files
from utils.helpers import project_path
from utils.logger import get_logger

log = get_logger("cleaning")


class CleaningOrchestrator:
    """Runs cleaners. Report persistence to DB is done by ReportService."""

    def __init__(self, processed_dir: Path | None = None) -> None:
        self.processed_dir = processed_dir or project_path("data", "processed")
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def clean_content(
        self,
        records: list[dict[str, Any]],
        *,
        write_files: bool | None = None,
    ) -> dict[str, Any]:
        if write_files is None:
            write_files = write_processed_files()
        pipeline = CleaningPipeline(record_type="content")
        result = pipeline.run(records)
        report = pipeline.report.to_dict()
        report_path = ""
        cleaned_csv = ""
        if write_files:
            report_path_obj = self.processed_dir / "quality_report_content.json"
            report_path_obj.write_text(json.dumps(report, indent=2), encoding="utf-8")
            out_csv = self.processed_dir / "cleaned_content.csv"
            pd.DataFrame(result.kept).to_csv(out_csv, index=False)
            report_path = str(report_path_obj)
            cleaned_csv = str(out_csv)
        log.info("Content cleaning kept=%s rejected=%s", len(result.kept), len(result.rejected))
        return {
            "kept": result.kept,
            "rejected": result.rejected,
            "stats": result.stats,
            "report": report,
            "report_path": report_path,
            "cleaned_csv": cleaned_csv,
        }

    def clean_pitches(
        self,
        records: list[dict[str, Any]],
        *,
        write_files: bool | None = None,
    ) -> dict[str, Any]:
        if write_files is None:
            write_files = write_processed_files()
        pipeline = CleaningPipeline(record_type="pitch")
        result = pipeline.run(records)
        report = pipeline.report.to_dict()
        report_path = ""
        if write_files:
            report_path_obj = self.processed_dir / "quality_report_pitches.json"
            report_path_obj.write_text(json.dumps(report, indent=2), encoding="utf-8")
            report_path = str(report_path_obj)
        log.info("Pitch cleaning kept=%s rejected=%s", len(result.kept), len(result.rejected))
        return {
            "kept": result.kept,
            "rejected": result.rejected,
            "stats": result.stats,
            "report": report,
            "report_path": report_path,
        }


CleaningService = CleaningOrchestrator
