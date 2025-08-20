"""Consolidation: create a simple daily summary entry in events."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .store import LTM
from .indexing import embed_text


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
    # Write/refresh vectors for facts
    for fid, _k, val, _sid, _ts in store.get_facts():
        try:
            vec = embed_text(val)
            store.upsert_fact_vector(int(fid), vec)
        except Exception:
            # Best-effort, continue
            pass
    # Extract simple relations from known fact patterns
    try:
        for _fid, key, value, sid, _ts in store.get_facts():
            # Pattern: capital:<country> -> (country, capital_of, value)
            if key.startswith("capital:"):
                country = key.split(":", 1)[1].strip().title()
                city = str(value).strip().title()
                if country and city:
                    store.add_relation(country, "capital_of", city, source_id=sid)
                    store.add_relation(city, "is_capital_of", country, source_id=sid)
            # You can extend with more patterns later
    except Exception:
        pass
