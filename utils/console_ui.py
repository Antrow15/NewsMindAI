"""Human-readable console formatting (no JSON dumps)."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence


def line(char: str = "=", width: int = 56) -> str:
    return char * width


def header(title: str) -> None:
    print()
    print(line("="))
    print(f"  {title}")
    print(line("="))


def success(message: str) -> None:
    print(f"[OK] {message}")


def error(message: str) -> None:
    print(f"[ERROR] {message}")


def info(message: str) -> None:
    print(f"[INFO] {message}")


def kv(label: str, value: Any) -> None:
    text = "-" if value is None or value == "" else value
    print(f"  {label} - {text}")


def blank() -> None:
    print()


def show_user(user: Mapping[str, Any]) -> None:
    header("Session")
    kv("Username", user.get("username"))
    kv("Full Name", user.get("full_name"))
    kv("Role", user.get("role_name") or user.get("role_code"))
    kv("Role Code", user.get("role_code"))
    caps = user.get("capabilities") or []
    kv("Capabilities", ", ".join(caps) if caps else "none")
    profiles = user.get("profiles") or {}
    if profiles:
        kv("Profiles", ", ".join(f"{k}={v}" for k, v in profiles.items()))
    blank()


def show_dict_rows(title: str, rows: Sequence[Mapping[str, Any]], fields: Sequence[tuple[str, str]]) -> None:
    """fields: list of (label, key)."""
    header(title)
    if not rows:
        info("No records found.")
        blank()
        return
    for i, row in enumerate(rows, start=1):
        print(f"  --- Record {i} ---")
        for label, key in fields:
            kv(label, row.get(key))
        print()
    kv("Total", len(rows))
    blank()


def show_stats(title: str, stats: Mapping[str, Any]) -> None:
    header(title)
    for key, value in stats.items():
        label = str(key).replace("_", " ").title()
        if isinstance(value, Mapping):
            kv(label, ", ".join(f"{k}={v}" for k, v in value.items()))
        else:
            kv(label, value)
    blank()


CANCEL_WORDS = {"q", "quit", "exit", "cancel"}


class UserCancelled(Exception):
    """User asked to cancel the current prompt/action."""


def is_cancel(value: str) -> bool:
    return (value or "").strip().lower() in CANCEL_WORDS


def prompt_nonempty(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if is_cancel(value):
            raise UserCancelled("Cancelled.")
        if value:
            return value
        error(f"{label} cannot be empty.")


def prompt_optional(label: str, default: str = "") -> str:
    value = input(f"{label}: ").strip()
    if is_cancel(value):
        raise UserCancelled("Cancelled.")
    return value if value else default


def prompt_choice(label: str, allowed: Sequence[str], *, allow_empty: bool = False) -> Optional[str]:
    options = ", ".join(allowed)
    while True:
        value = input(f"{label} [{options}]: ").strip().lower()
        if is_cancel(value):
            raise UserCancelled("Cancelled.")
        if not value:
            if allow_empty:
                return None
            error(f"{label} is required. Choose one of: {options}")
            continue
        if value in {a.lower() for a in allowed}:
            return value
        error(f"Invalid {label.lower()}. Allowed: {options}")
