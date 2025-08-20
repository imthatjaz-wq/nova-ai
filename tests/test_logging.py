from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from nova.config import Settings
from nova.logging_setup import setup_logging
from nova.permissions import request_permission


def test_file_logging_and_audit_written(monkeypatch, tmp_path) -> None:
    # Prepare dirs and settings
    data_dir = Path(tmp_path)
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    settings = Settings(data_dir=data_dir, log_level="INFO")

    # Configure logging and verify file handler
    logger = setup_logging(settings)
    handlers = [h for h in logging.getLogger("nova").handlers]
    assert any(isinstance(h, RotatingFileHandler) for h in handlers)

    # Ensure noninteractive and log an audit decision
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")
    request_permission("test", "resource.txt", path=data_dir / "resource.txt")

    log_file = logs_dir / "nova.log"
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "decision=" in content
