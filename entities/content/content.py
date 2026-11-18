"""Content pipeline: Content (base)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Content:
    content_id: Optional[int] = None
    author_id: Optional[int] = None
    title: str = ""
    summary: Optional[str] = None
    raw_body: Optional[str] = None
    content_body: Optional[str] = None
    content_kind: Optional[str] = "article"
    source_type: Optional[str] = None
    status: str = "draft"
    current_version: int = 1
