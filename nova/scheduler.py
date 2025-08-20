"""Minimal in-process scheduler using threading.Timer for one-shot jobs.

Adds a simple alert sink to surface reminder messages (log by default).
"""
from __future__ import annotations

import threading
import logging
from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class Scheduled:
    delay_seconds: int
    func: Callable[[], None]
    timer: threading.Timer | None = None
    interval_seconds: Optional[float] = None
    recurring: bool = False
    cancelled: bool = False


_SCHEDULED: List[Scheduled] = []


_ALERT_SINK = None  # type: Callable[[str], None] | None


def _default_alert_sink(msg: str) -> None:
    logger = logging.getLogger("nova.alerts")
    if not logger.handlers:
        logger.propagate = True
    logger.setLevel(logging.INFO)
    logger.info("alert=%s", msg)


def set_alert_sink(func: Callable[[str], None]) -> None:
    global _ALERT_SINK
    _ALERT_SINK = func


def alert(message: str) -> None:
    sink = _ALERT_SINK or _default_alert_sink
    try:
        sink(message)
    except Exception:
        # Never crash caller on alert
        _default_alert_sink(message)


def schedule_once(delay_seconds: int, func: Callable[[], None]) -> int:
    """Schedule func to run once after delay_seconds in a background thread."""
    item = Scheduled(delay_seconds=delay_seconds, func=func)
    t = threading.Timer(delay_seconds, func)
    item.timer = t
    _SCHEDULED.append(item)
    t.daemon = True
    t.start()
    return len(_SCHEDULED)


def schedule_every(interval_seconds: float, func: Callable[[], None]) -> int:
    """Schedule func to run repeatedly every interval_seconds.

    Returns an identifier (list index) for introspection only; use cancel_all to stop.
    """
    item = Scheduled(delay_seconds=int(interval_seconds), func=func, interval_seconds=float(interval_seconds), recurring=True)

    def _runner():
        if item.cancelled:
            return
        try:
            func()
        finally:
            if not item.cancelled:
                t2 = threading.Timer(item.interval_seconds or interval_seconds, _runner)
                t2.daemon = True
                item.timer = t2
                t2.start()

    t = threading.Timer(interval_seconds, _runner)
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
            it.cancelled = True
            if it.timer:
                it.timer.cancel()
        except Exception:
            pass
    _SCHEDULED.clear()
