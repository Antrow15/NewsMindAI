"""Stakeholder: Role (desk / capability)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Role:
    role_id: Optional[int] = None
    role_code: str = ""
    role_name: str = ""
    role_description: Optional[str] = None
    is_active: bool = True
