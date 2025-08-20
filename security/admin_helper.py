"""Minimal Windows elevation helper using runas semantics.

This function enforces a strict whitelist from security.policies and delegates
to PowerShell Start-Process -Verb RunAs to trigger UAC if needed.
No return data is captured; only exit code is provided.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence

from . import policies


def run_elevated(command: str, args: Sequence[str] | None = None) -> int:
    exe = Path(command)
    if not policies.is_command_allowed_elevated(command):
        return 2  # blocked by policy
    arg_list = list(args or [])
    # Build PowerShell Start-Process to request elevation
    ps_cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Start-Process",
        f"-FilePath '{str(exe)}'",
    ]
    if arg_list:
        joined = " ".join(arg_list).replace("'", "''")
        ps_cmd += ["-ArgumentList", f"'{joined}'"]
    ps_cmd += [
        "-Verb",
        "RunAs",
        "-Wait",
    ]
    # Filter out empty elements
    ps_cmd = [p for p in ps_cmd if p]
    try:
        proc = subprocess.run(ps_cmd, capture_output=True, text=True)
        return proc.returncode
    except Exception:
        return 1
