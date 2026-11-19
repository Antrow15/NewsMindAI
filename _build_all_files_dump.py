"""Write a single updated source dump of NewsMindAI V2 (no secrets/binaries)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "ALL_FILES_DUMP.txt"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "node_modules",
    "artifacts",
    "logs",
    "documentation",
}

SKIP_FILE_NAMES = {
    ".env",
    "ALL_FILES_DUMP.txt",
    "JWT_AUTH_CHANGED_FILES_DUMP.txt",
    "probe_canvas_data.json",
    "probe_results.json",
}

SKIP_SUFFIXES = {
    ".joblib",
    ".pyc",
    ".pyo",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".docx",
    ".zip",
    ".7z",
}

INCLUDE_SUFFIXES = {
    ".py",
    ".sql",
    ".html",
    ".md",
    ".txt",
    ".example",
    ".json",
    ".csv",
    ".gitignore",
}

# Skip huge training CSVs but keep tiny json metadata if under size cap
MAX_FILE_BYTES = 400_000  # ~400KB per file


def should_skip(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return True
    if path.name.startswith("_probe"):
        return True
    if path.name in SKIP_FILE_NAMES:
        return True
    if path.name == Path(__file__).name:
        return True
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    if path.suffix.lower() not in INCLUDE_SUFFIXES and path.name not in {".gitignore"}:
        # allow extensionless only if known
        if path.name not in {"ENV.example"}:
            return True
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return True
    except OSError:
        return True
    return False


def main() -> None:
    files = sorted(
        p for p in ROOT.rglob("*") if p.is_file() and not should_skip(p)
    )
    lines: list[str] = []
    lines.append("=" * 88)
    lines.append("NewsMindAI V2 — ALL_FILES_DUMP (updated source snapshot)")
    lines.append(f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}")
    lines.append("Includes JWT auth updates. Excludes: .env, artifacts/binaries, caches,")
    lines.append("documentation outputs, probe dumps, huge CSVs (>400KB), _probe scripts.")
    lines.append("=" * 88)
    lines.append("")
    lines.append(f"FILE COUNT: {len(files)}")
    lines.append("")
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        lines.append(f"  - {rel}")
    lines.append("")

    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        lines.append("=" * 88)
        lines.append(f"FILE: {rel}")
        lines.append("=" * 88)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            lines.append(f"[UNREADABLE: {exc}]")
            lines.append("")
            continue
        lines.append(text.rstrip("\n"))
        lines.append("")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes) files={len(files)}")


if __name__ == "__main__":
    main()
