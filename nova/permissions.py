"""Permission gate with interactive prompt and audit logging."""
from __future__ import annotations

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Optional

from nova.config import Settings
from security import policies


class Decision(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"


AUDIT_LOGGER_NAME = "nova.audit"


def _audit_logger() -> logging.Logger:
    logger = logging.getLogger(AUDIT_LOGGER_NAME)
    if not logger.handlers:
        # inherit handlers from root configured in logging_setup
        logger.propagate = True
    logger.setLevel(logging.INFO)
    return logger


def interactive_prompt(question: str, *, default: Optional[bool] = None) -> bool:
    """Prompt user in console for Y/N; respects NOVA_NONINTERACTIVE for tests.

    NOVA_NONINTERACTIVE=1 with NOVA_PERMISSION_DEFAULT=approve|deny allows tests to simulate.
    """
    noninteractive = os.getenv("NOVA_NONINTERACTIVE", "0").lower() in ("1", "true", "yes")
    default_str = " [y/N]" if default is False else " [Y/n]" if default is True else " [y/n]"
    if noninteractive:
        choice = os.getenv("NOVA_PERMISSION_DEFAULT", "deny").lower()
        if choice.startswith("a") or choice.startswith("y"):
            return True
        if choice.startswith("d"):
            return False
        # "prompt" or any other value: choose provided default if any; else deny
        return bool(default) if default is not None else False
    while True:
        resp = input(f"{question}{default_str}: ").strip().lower()
        if not resp and default is not None:
            return default
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False


def request_permission(action: str, resource: str, *, path: str | Path | None = None) -> Decision:
    """Request user permission for a privileged action and log an audit record."""
    logger = _audit_logger()
    path_obj = Path(path) if path is not None else None
    needs_elev = path_obj is not None and policies.requires_elevation_for_path(path_obj)
    q = f"Nova requests permission to {action} on {resource}."
    if needs_elev:
        q += " (May require elevation)"
    approved = interactive_prompt(q, default=False)
    decision = Decision.APPROVED if approved else Decision.DENIED
    logger.info(
        "decision=%s action=%s resource=%s path=%s needs_elev=%s",
        decision,
        action,
        resource,
        str(path_obj) if path_obj else "",
        needs_elev,
    )
    return decision
