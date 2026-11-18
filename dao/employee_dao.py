"""Employee DAO — table employee."""

from __future__ import annotations

from typing import Any, Optional

from dao.base_dao import BaseDAO
from database.connection import db_cursor
from entities.employee import Employee
from utils.errors import NotFoundError, ValidationError
from utils.validators import (
    require_email,
    require_employment_status,
    require_nonempty,
    require_optional_str,
    require_positive_id,
)


class EmployeeDAO(BaseDAO):
    table = "employee"

    def create(self, employee: Employee) -> int:
        code = require_nonempty(employee.employee_code, "Employee code")
        first_name = require_nonempty(employee.first_name, "First name")
        last_name = require_nonempty(employee.last_name, "Last name")
        email = require_email(employee.email)
        status = require_employment_status(employee.employment_status or "active")
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO employee (
                    employee_code, first_name, last_name, email,
                    mobile_number, department, designation, location, employment_status, joining_date
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (employee_code) DO UPDATE
                SET first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    email = EXCLUDED.email
                RETURNING employee_id
                """,
                (
                    code,
                    first_name,
                    last_name,
                    email,
                    require_optional_str(employee.mobile_number, "Mobile"),
                    require_optional_str(employee.department, "Department", max_len=128),
                    require_optional_str(employee.designation, "Designation", max_len=128),
                    require_optional_str(employee.location, "Location", max_len=128),
                    status,
                    employee.joining_date,
                ),
            )
            return int(cur.fetchone()["employee_id"])

    def read(self, employee_id: int) -> Optional[dict[str, Any]]:
        return self.get_by_id("employee_id", require_positive_id(employee_id, "Employee ID"))

    def require(self, employee_id: int) -> dict[str, Any]:
        row = self.read(employee_id)
        if not row:
            raise NotFoundError(f"Employee ID {employee_id} was not found.")
        return row

    def update(self, employee_id: int, **fields: Any) -> int:
        self.require(employee_id)
        allowed = {
            "first_name",
            "last_name",
            "email",
            "mobile_number",
            "department",
            "designation",
            "location",
            "employment_status",
        }
        cols = {k: v for k, v in fields.items() if k in allowed}
        if "first_name" in cols:
            cols["first_name"] = require_nonempty(cols["first_name"], "First name")
        if "last_name" in cols:
            cols["last_name"] = require_nonempty(cols["last_name"], "Last name")
        if "email" in cols:
            cols["email"] = require_email(cols["email"])
        if "employment_status" in cols:
            cols["employment_status"] = require_employment_status(cols["employment_status"])
        if not cols:
            raise ValidationError("No valid fields to update.")
        sets = ", ".join(f"{k} = %s" for k in cols)
        return int(
            self.execute(
                f"UPDATE employee SET {sets}, updated_at = NOW() WHERE employee_id = %s",
                (*cols.values(), employee_id),
            )
        )

    def delete(self, employee_id: int) -> int:
        self.require(employee_id)
        return self.delete_by_id("employee_id", employee_id)
