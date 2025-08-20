from __future__ import annotations

import threading

from nova.scheduler import schedule_once, list_scheduled, cancel_all


def test_schedule_once_executes() -> None:
    evt = threading.Event()

    def task():
        evt.set()

    try:
        schedule_once(0.05, task)
        # Should be scheduled
        assert len(list_scheduled()) >= 1
        # Wait up to 0.5s for event
        assert evt.wait(0.5)
    finally:
        cancel_all()
