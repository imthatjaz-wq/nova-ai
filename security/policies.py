"""Central security policies and helpers.

Rules:
- Read-only by default.
- Any write/modify/system-changing action requires explicit user approval.
- Elevation may be required for sensitive locations/operations.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DATA_DIR_DEFAULT = Path(r"C:\\Nova\\data")


@dataclass(frozen=True)
class Policy:
    name: str
    description: str


DEFAULT_WRITE_POLICY = Policy(
    name="default_write_policy",
    description="Writes require explicit user approval and may require elevation.",
)


def get_data_dir() -> Path:
    """Resolve configured data dir, falling back to default."""
    return Path(os.getenv("NOVA_DATA_DIR", str(DATA_DIR_DEFAULT)))


def _normalize_windows_path(p: Path) -> str:
    """Normalize path for case-insensitive Windows comparison.

    - Resolve to absolute if possible
    - Convert to backslashes
    - Lower-case
    - Ensure no trailing slash (except drive root), so callers can control suffix checks
    """
    try:
        as_path = p.resolve()
    except Exception:
        as_path = p.absolute()
    s = str(as_path).replace('/', '\\').lower()
    # normalize trailing backslash except for drive root like c:\
    if len(s) > 3 and s.endswith('\\'):
        s = s.rstrip('\\')
    return s


def is_within_data_dir(path: Path) -> bool:
    data_dir = _normalize_windows_path(get_data_dir())
    target = _normalize_windows_path(path)
    # exact match or startswith data_dir + backslash
    return target == data_dir or target.startswith(data_dir + '\\')


def requires_elevation_for_path(path: Path) -> bool:
    """Elevation required for any path outside the configured data dir.

    C:\\Nova\\data (or NOVA_DATA_DIR) and its children do not require elevation.
    Everything else does.
    """
    return not is_within_data_dir(path)


ALLOWED_ELEVATED_COMMANDS: set[str] = set(
    [
        # Minimal safe whitelist; expand cautiously in later segments
        # Note: compare using Path(command).name.lower()
        "powershell.exe",
        "powershell",  # be tolerant to missing extension
        "schtasks.exe",
        "schtasks",
    ]
)


def is_command_allowed_elevated(command: str) -> bool:
    exe = Path(command).name.lower()
    return exe in ALLOWED_ELEVATED_COMMANDS
