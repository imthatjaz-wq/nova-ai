"""Privileged helper shim: centralizes elevation-gated actions.

For Phase D, this is a simple module that defers to the existing permission gate.
Later, this can be hosted as a separate process to harden boundaries.
"""
from __future__ import annotations

from pathlib import Path

from nova.permissions import request_permission, Decision
from security import policies


def can_write(path: Path | str) -> bool:
    p = Path(path)
    d = request_permission(action="write", resource=str(p), path=p)
    if d is not Decision.APPROVED:
        return False
    if policies.requires_elevation_for_path(p):
        return False
    return True


def guarded_write_preview(path: Path | str, description: str) -> str:
    """Return a message indicating whether a write would be allowed.

    We do not perform actual writes in this phase.
    """
    p = Path(path)
    d = request_permission(action="write", resource=str(p), path=p)
    if d is not Decision.APPROVED:
        return f"[denied] {description} {p}"
    if policies.requires_elevation_for_path(p):
        return f"[approved] Would perform (elev needed) {description} {p}"
    return f"[approved] Would perform {description} {p}"
