"""Stakeholder desk: Audience Insight Analyst."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AudienceInsightAnalyst:
    aia_id: Optional[int] = None
    user_id: Optional[int] = None
    focus_region: Optional[str] = None
    status: str = "active"
