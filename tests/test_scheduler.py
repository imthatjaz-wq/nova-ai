from __future__ import annotations

import threading

from nova.scheduler import schedule_once, schedule_every, list_scheduled, cancel_all


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


def test_schedule_every_recurs() -> None:
    evt = threading.Event()
    counter = {"n": 0}

    def task():
        counter["n"] += 1
        if counter["n"] >= 2:
            evt.set()

    try:
        schedule_every(0.05, task)
        assert evt.wait(0.5)
    finally:
        cancel_all()
