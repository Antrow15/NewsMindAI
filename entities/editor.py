"""Stakeholder desk: Editor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Editor:
    editor_id: Optional[int] = None
    user_id: Optional[int] = None
    editorial_desk: Optional[str] = None
    status: str = "active"
