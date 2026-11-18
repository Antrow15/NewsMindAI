"""Application logging."""

from __future__ import annotations

import logging
from pathlib import Path

from utils.helpers import project_path


def get_logger(name: str = "newsmind") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    log_dir = project_path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "application.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.INFO)
    # Console: show INFO+ so pipeline steps are visible in the terminal
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger
