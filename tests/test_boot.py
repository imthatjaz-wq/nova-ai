from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_imports() -> None:
    # Ensure key packages import
    import nova_core  # noqa: F401
    import nova  # noqa: F401
    import conversation  # noqa: F401
    import memory  # noqa: F401
    import internet  # noqa: F401
    import commands  # noqa: F401
    import workspace  # noqa: F401
    import ui  # noqa: F401
    import security  # noqa: F401


def test_cli_help() -> None:
    # Run `python -m ui.cli --help` and expect exit code 0
    cmd = [sys.executable, "-m", "ui.cli", "--help"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "Nova CLI" in proc.stdout or "Usage" in proc.stdout
