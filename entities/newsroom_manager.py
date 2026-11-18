"""Stakeholder desk: Newsroom Manager."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class NewsroomManager:
    newsroom_manager_id: Optional[int] = None
    user_id: Optional[int] = None
    managed_region: Optional[str] = None
    status: str = "active"
