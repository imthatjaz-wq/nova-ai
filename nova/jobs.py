from __future__ import annotations

"""Background jobs: knowledge gap research and nightly consolidation."""

from typing import List

from memory.store import LTM
from internet.search import search_web
from internet.summarize import summarize_text
from memory.consolidator import consolidate


def _extract_question_from_chat(content: str) -> str | None:
    # content format from CLI: "user: <q> | nova: <resp>"
    try:
        if "user:" in content and "| nova:" in content:
            q = content.split("user:", 1)[1].split("| nova:", 1)[0].strip()
            return q if q else None
    except Exception:
        pass
    return None


def find_gaps(ltm: LTM, limit: int = 5) -> List[str]:
    gaps: List[str] = []
    for _id, typ, content, _ts in ltm.get_events("chat"):
        if "don't know" in content.lower():
            q = _extract_question_from_chat(content)
            if q:
                gaps.append(q)
        if len(gaps) >= limit:
            break
    return gaps


def run_gap_research(ltm: LTM, max_items: int = 3) -> int:
    """Research up to max_items knowledge gaps and save notes with sources."""
    count = 0
    for q in find_gaps(ltm, limit=max_items):
        results = search_web(q)
        if not results:
            continue
        top = results[0]
        url = top.get("url", "")
        title = top.get("name", "")
        snippet = top.get("snippet", "")
        summary = summarize_text(f"{title}. {snippet}")
        source_id = ltm.add_source(url, title)
        key = f"learned:{q.lower()}"
        ltm.add_fact(key, summary, source_id=source_id)
        ltm.log_event("learning", f"query: {q} | source: {url}")
        count += 1
    return count


def run_nightly(ltm: LTM | None = None) -> None:
    store = ltm or LTM()
    consolidate(store)
