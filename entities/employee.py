"""Stakeholder: Employee (HR identity)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Employee:
    employee_id: Optional[int] = None
    employee_code: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    mobile_number: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    location: Optional[str] = None
    employment_status: str = "active"
    joining_date: Optional[date] = None
