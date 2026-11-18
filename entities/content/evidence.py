"""Content pipeline: Evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Evidence:
    evidence_id: Optional[int] = None
    content_id: Optional[int] = None
    title: str = ""
    evidence_type: Optional[str] = None
    source_url: Optional[str] = None
    file_path: Optional[str] = None
    # Plain optional body text (legacy DB column name ocr_text; not OCR).
    body_text: Optional[str] = None
    uploaded_by: Optional[int] = None
