"""Consolidation: create a simple daily summary entry in events."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .store import LTM


def summarize_session(ltm: LTM, *, max_items: int = 5) -> str:
    facts = ltm.get_facts()
    events = ltm.get_events()
    parts: list[str] = []
    if facts:
        parts.append(f"facts={min(len(facts), max_items)}")
    if events:
        parts.append(f"events={min(len(events), max_items)}")
    if not parts:
        parts.append("idle")
    return "; ".join(parts)


def consolidate(ltm: Optional[LTM] = None) -> None:
    store = ltm or LTM()
    summary = summarize_session(store)
    store.log_event("consolidation", f"{datetime.utcnow().isoformat()} | {summary}")
