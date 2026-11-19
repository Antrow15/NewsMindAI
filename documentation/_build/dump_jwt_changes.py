"""Write a dump of JWT-auth changed files only (no .env secrets)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "JWT_AUTH_CHANGED_FILES_DUMP.txt"

FILES = [
    "requirements.txt",
    "ENV.example",
    "README.md",
    "config/constants.py",
    "modules/authentication/security.py",
    "modules/authentication/auth_service.py",
    "api/deps.py",
    "api/main.py",
    "api/routers/auth.py",
    "api/schemas/auth.py",
]


def main() -> None:
    lines: list[str] = []
    lines.append("=" * 80)
    lines.append("NewsMindAI V2 — JWT Auth Change Dump (changed files only)")
    lines.append(f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}")
    lines.append("Note: .env is NOT included (contains secrets). See ENV.example.")
    lines.append("=" * 80)
    lines.append("")
    lines.append("CHANGED FILES:")
    for rel in FILES:
        lines.append(f"  - {rel}")
    lines.append("")

    for rel in FILES:
        path = ROOT / rel
        lines.append("=" * 80)
        lines.append(f"FILE: {rel}")
        lines.append("=" * 80)
        if not path.exists():
            lines.append("[MISSING]")
            lines.append("")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lines.append(text.rstrip() + "\n")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
