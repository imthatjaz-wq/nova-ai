"""Workspace event bus with priority and subscribers."""
from __future__ import annotations

from queue import PriorityQueue
from typing import Any, Callable, List, Tuple


class Bus:
    def __init__(self) -> None:
        self.q: PriorityQueue[Tuple[int, Any]] = PriorityQueue()
        self._subs: List[Callable[[Any], None]] = []

    def publish(self, priority: int, item: Any) -> None:
        self.q.put((priority, item))

    def get(self) -> Tuple[int, Any]:
        return self.q.get()

    def subscribe(self, callback: Callable[[Any], None]) -> None:
        self._subs.append(callback)

    def broadcast(self, max_items: int | None = None) -> int:
        """Deliver queued items to all subscribers in priority order.

        Returns the number of items broadcast.
        """
        delivered = 0
        while not self.q.empty():
            if max_items is not None and delivered >= max_items:
                break
            pr, item = self.q.get()
            for sub in list(self._subs):
                try:
                    sub(item)
                except Exception:
                    # ignore subscriber errors to keep bus flowing
                    pass
            delivered += 1
        return delivered
