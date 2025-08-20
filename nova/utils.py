from __future__ import annotations

import shutil
from pathlib import Path


def is_windows() -> bool:
    return shutil.which("cmd.exe") is not None


def normalize_path(p: str | Path) -> Path:
    return Path(p).expanduser().resolve()
