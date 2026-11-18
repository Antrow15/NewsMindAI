"""User-visible progress lines for long pipeline steps (console + log file)."""

from __future__ import annotations

import logging
from pathlib import Path

from utils.console_ui import info
from utils.helpers import project_path

_file_log: logging.Logger | None = None


def _file_logger() -> logging.Logger:
    """Write progress to application.log without duplicating on the console."""
    global _file_log
    if _file_log is not None:
        return _file_log
    logger = logging.getLogger("progress")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        log_dir = project_path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_dir / "application.log", encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        logger.addHandler(handler)
        logger.propagate = False
    _file_log = logger
    return logger


def progress(message: str) -> None:
    """Show a clear step on the console and mirror it to application.log."""
    text = str(message).strip()
    if not text:
        return
    info(text)
    _file_logger().info("%s", text)
