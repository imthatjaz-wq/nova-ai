from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .config import Settings


def setup_logging(settings: Settings, *, name: str = "nova") -> logging.Logger:
    """Configure root logger with console + rotating file handlers.

    - File logs in C:\\Nova\\data\\logs\\nova.log (best-effort)
    - Rotates at ~1 MB with 3 backups
    - Level from settings.log_level
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler only if logs dir already exists (respect read-only default)
    file_path: Path = settings.logs_dir / "nova.log"
    try:
        if settings.logs_dir.exists() and settings.logs_dir.is_dir():
            fh = RotatingFileHandler(file_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
            fh.setLevel(level)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            logger.debug("File logging enabled: %s", file_path)
        else:
            logger.debug("Logs directory not present; file logging disabled: %s", settings.logs_dir)
    except Exception as e:
        logger.debug("File logging disabled (%s)", e)

    logger.debug("Logging initialized at level %s", settings.log_level)
    return logger
