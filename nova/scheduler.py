"""Minimal in-process scheduler using threading.Timer for one-shot jobs."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, List


@dataclass
class Scheduled:
    delay_seconds: int
    func: Callable[[], None]
    timer: threading.Timer | None = None


_SCHEDULED: List[Scheduled] = []


def schedule_once(delay_seconds: int, func: Callable[[], None]) -> int:
    """Schedule func to run once after delay_seconds in a background thread."""
    item = Scheduled(delay_seconds=delay_seconds, func=func)
    t = threading.Timer(delay_seconds, func)
    item.timer = t
    _SCHEDULED.append(item)
    t.daemon = True
    t.start()
    return len(_SCHEDULED)


def list_scheduled() -> List[Scheduled]:
    return list(_SCHEDULED)


def cancel_all() -> None:
    for it in _SCHEDULED:
        try:
            if it.timer:
                it.timer.cancel()
        except Exception:
            pass
    _SCHEDULED.clear()
