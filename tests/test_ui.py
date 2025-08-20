from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_cli_chat_once_noninteractive(monkeypatch) -> None:
    # Deny persistence so LTM is in-memory
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")

    cmd = [sys.executable, "-m", "ui.cli", "chat", "--once", "hello"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    assert "Nova>" in proc.stdout


def test_cli_bootstrap_creates_logs_and_noninteractive_prompt(monkeypatch, tmp_path) -> None:
    # Use a temp data dir and noninteractive prompt mode
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "prompt")
    monkeypatch.setenv("NOVA_DATA_DIR", str(tmp_path))

    cmd = [sys.executable, "-m", "ui.cli", "hello"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    # Logs directory should be created best-effort (permission gate defaults to deny in prompt mode -> no dirs).
    # So file log may not exist; but running again with allow should create and write.
    logs_dir = Path(tmp_path) / "logs"
    assert not logs_dir.exists()

    # Now allow and ensure file appears
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "allow")
    proc2 = subprocess.run(cmd, capture_output=True, text=True)
    assert proc2.returncode == 0
    assert logs_dir.exists()
    # A nova.log should exist after logging is set up with dirs present
    log_file = logs_dir / "nova.log"
    assert log_file.exists()


def test_cli_jobs_commands_noninteractive(monkeypatch) -> None:
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "allow")
    # jobs nightly
    import sys, subprocess
    cmd = [sys.executable, "-m", "ui.cli", "jobs", "nightly"]
    p1 = subprocess.run(cmd, capture_output=True, text=True)
    assert p1.returncode == 0
    assert "Nightly consolidation complete" in p1.stdout
    # jobs research (with no gaps, may say 0)
    cmd2 = [sys.executable, "-m", "ui.cli", "jobs", "research", "--max-items", "1"]
    p2 = subprocess.run(cmd2, capture_output=True, text=True)
    assert p2.returncode == 0
    assert "Researched" in p2.stdout


def test_cli_version_outputs_version() -> None:
    import sys, subprocess
    cmd = [sys.executable, "-m", "ui.cli", "version"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    assert p.returncode == 0
    assert "Nova v" in p.stdout


def test_cli_diag_outputs(monkeypatch) -> None:
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    import sys, subprocess
    cmd = [sys.executable, "-m", "ui.cli", "diag"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    assert p.returncode == 0
    out = p.stdout
    assert "=== Nova Diagnostics ===" in out
    assert "Search provider:" in out
    assert "Policy: data dir=" in out
