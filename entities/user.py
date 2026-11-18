"""Stakeholder: User — ERD USER / physical table `users` (login by username)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    user_id: Optional[int] = None
    employee_id: Optional[int] = None
    role_id: Optional[int] = None
    username: str = ""
    password_hash: str = ""
    account_status: str = "active"
    role_code: Optional[str] = None
    role_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    last_login: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
