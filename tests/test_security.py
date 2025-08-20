from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from security import policies
from nova.permissions import request_permission, Decision
from internet.search import _allow_domain


def test_permission_defaults_and_outside_paths(monkeypatch, tmp_path) -> None:
    # Noninteractive deny by default
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.delenv("NOVA_PERMISSION_DEFAULT", raising=False)
    d = request_permission("write", str(tmp_path / "x.txt"), path=str(tmp_path / "x.txt"))
    assert d is Decision.DENIED

    # Outside data dir requires elevation
    monkeypatch.delenv("NOVA_DATA_DIR", raising=False)
    outside = tmp_path / "folder" / "x.txt"
    assert policies.requires_elevation_for_path(outside)
    inside = Path(r"C:\\Nova\\data\\x.txt")
    assert policies.requires_elevation_for_path(inside) is False


def test_allowlist_strict_host() -> None:
    # wikipedia allowed, example.com not allowed
    allow = "wikipedia.org,edu,gov"
    assert _allow_domain("https://en.wikipedia.org/wiki/Paris", allow)
    assert _allow_domain("https://sub.domain.edu/page", allow)
    assert not _allow_domain("https://example.com/page", allow)
