from __future__ import annotations

import os
from pathlib import Path

from nova.permissions import request_permission, Decision
from security import policies
from security.admin_helper import run_elevated


def test_permission_denied_noninteractive(monkeypatch) -> None:
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")
    d = request_permission("write", "test.txt", path="C:/Nova/data/test.txt")
    assert d is Decision.DENIED


def test_permission_approved_noninteractive(monkeypatch) -> None:
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "approve")
    d = request_permission("write", "test.txt", path="C:/Nova/data/test.txt")
    assert d is Decision.APPROVED


def test_requires_elevation_outside_data_dir(tmp_path, monkeypatch) -> None:
    # Ensure default data dir
    monkeypatch.delenv("NOVA_DATA_DIR", raising=False)
    outside = tmp_path / "outside.txt"
    assert policies.requires_elevation_for_path(outside) is True
    inside = Path("C:/Nova/data/inside.txt")
    assert policies.requires_elevation_for_path(inside) is False


def test_elevation_whitelist_denies_non_whitelisted(monkeypatch) -> None:
    # Non-whitelisted exe should be blocked by policy
    rc = run_elevated("notepad.exe", ["/A"])
    assert rc == 2  # blocked by policy

    # Whitelisted name should pass policy stage (may still fail to run in CI),
    # so we monkeypatch subprocess to avoid actual elevation.
    import subprocess

    class DummyResult:
        def __init__(self, code: int) -> None:
            self.returncode = code

    def fake_run(cmd, capture_output=True, text=True):
        return DummyResult(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    rc2 = run_elevated("powershell.exe", ["-NoProfile", "-Command", "Write-Output 'ok'"])
    assert rc2 == 0
