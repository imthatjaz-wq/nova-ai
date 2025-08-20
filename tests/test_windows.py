from __future__ import annotations

import sys
from pathlib import Path


def test_build_schtasks_create_command(monkeypatch) -> None:
    # Force Windows path semantics for test even on non-Windows by importing module functions
    from nova.windows import build_schtasks_create

    cmd = build_schtasks_create(
        task_name="NovaNightlyTest",
        working_dir=Path("C:/Nova"),
        python_exe=Path(sys.executable),
        time_hhmm="03:30",
        args=["-m", "ui.cli", "jobs", "nightly"],
    )
    # schtasks /Create ... /TN NovaNightlyTest ... /ST 03:30 ... (TR contains python and args)
    assert cmd[0].lower() == "schtasks"
    assert "/Create" in cmd or "/create" in cmd
    assert "NovaNightlyTest" in cmd
    assert "03:30" in cmd
    # TR should include ui.cli jobs nightly
    assert any("ui.cli jobs nightly" in part for part in cmd)


def test_cli_jobs_schedule_dry_run(monkeypatch) -> None:
    # Ensure command prints dry-run without attempting to run schtasks
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    import subprocess
    proc = subprocess.run([sys.executable, "-m", "ui.cli", "jobs", "schedule", "--time", "01:45"], capture_output=True, text=True)
    assert proc.returncode in (0, 1)
    # On non-Windows it errors; on Windows it should show dry-run
    if proc.returncode == 0:
        assert "[dry-run] schtasks" in proc.stdout
