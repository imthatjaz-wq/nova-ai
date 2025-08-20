from __future__ import annotations

"""Windows integration helpers: Task Scheduler command builders and admin checks."""

import os
import sys
from pathlib import Path
from typing import List


def is_windows() -> bool:
    return os.name == "nt"


def is_admin() -> bool:
    """Best-effort admin check on Windows; returns False elsewhere."""
    if not is_windows():
        return False
    try:
        import ctypes  # type: ignore

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def quote(s: str) -> str:
    """Quote an argument for cmd.exe/schtasks; wrap with quotes and escape inner quotes."""
    if not s:
        return '""'
    if '"' in s:
        s = s.replace('"', '\\"')
    if " " in s or "\t" in s or "\n" in s or "'" in s or "&" in s:
        return f'"{s}"'
    return s


def build_schtasks_create(
    task_name: str,
    working_dir: Path,
    python_exe: Path | None = None,
    time_hhmm: str = "02:00",
    args: List[str] | None = None,
) -> List[str]:
    """Build a schtasks /Create command for a daily task.

    Returns a list of arguments suitable for subprocess.run([...]).
    """
    if python_exe is None:
        python_exe = Path(sys.executable)
    if args is None:
        args = ["-m", "ui.cli", "jobs", "nightly"]
    # Join TR as a single argument: executable plus args
    tr = f"{quote(str(python_exe))} {' '.join(args)}"
    cmd = [
        "schtasks",
        "/Create",
        "/TN",
        task_name,
        "/TR",
        tr,
        "/SC",
        "DAILY",
        "/ST",
        time_hhmm,
        "/RL",
        "LIMITED",
        "/F",
    ]
    return cmd


def build_schtasks_delete(task_name: str) -> List[str]:
    return ["schtasks", "/Delete", "/TN", task_name, "/F"]
