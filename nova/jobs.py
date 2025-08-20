from __future__ import annotations

"""Background jobs: knowledge gap research and nightly consolidation."""

from typing import List
from datetime import datetime, timezone
import time

from memory.store import LTM
from internet.search import aggregate_sources
from memory.consolidator import consolidate


def _log_job_event(ltm: LTM, name: str, status: str, started: float, meta: str = "") -> None:
    try:
        duration_ms = int((time.time() - started) * 1000)
        meta_str = f" meta={meta}" if meta else ""
        ltm.log_event("job", f"name={name} status={status} duration_ms={duration_ms}{meta_str}")
    except Exception:
        pass
# from .scheduler import schedule_every  # not used in tests; scheduling happens in installer/ops


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
    started = time.time()
    count = 0
    status = "ok"
    try:
        for q in find_gaps(ltm, limit=max_items):
            summary, citations = aggregate_sources(q)
            if not summary:
                continue
            key = f"learned:{q.lower()}"
            srcs = [(c.get("url", ""), c.get("name", "")) for c in citations if c.get("url")]
            if srcs:
                ltm.add_fact_with_sources(key, summary, srcs)
            else:
                ltm.add_fact(key, summary)
            # Log learning event with joined source URLs for traceability
            joined_sources = ",".join([u for u, _ in srcs]) if srcs else ""
            ltm.log_event("learning", f"query: {q} | sources: {joined_sources}")
            count += 1
        return count
    except Exception:
        status = "fail"
        raise
    finally:
        _log_job_event(ltm, "research", status, started, meta=f"count:{count}")


def run_nightly(ltm: LTM | None = None) -> None:
    store = ltm or LTM()
    started = time.time()
    status = "ok"
    try:
        consolidate(store)
    except Exception:
        status = "fail"
        raise
    finally:
        _log_job_event(store, "nightly", status, started)


def run_daily_summary(ltm: LTM | None = None) -> str:
    """Create a daily digest from inbox, learning, and recent chats; persist as a fact and event.

    Returns the digest text.
    """
    store = ltm or LTM()
    # Collect items
    inbox = store.get_events("inbox")[:50]
    learning = store.get_events("learning")[:50]
    chats = store.get_events("chat")[:50]
    # Compose a short digest
    parts: List[str] = []
    if inbox:
        parts.append(f"inbox={len(inbox)}")
    if learning:
        parts.append(f"learned={len(learning)}")
    if chats:
        parts.append(f"chats={len(chats)}")
    if not parts:
        parts.append("idle")
    header = ", ".join(parts)
    # Pull citation URLs from learned facts if any
    cite_urls: List[str] = []
    try:
        for _id, _k, v, _sid, _ts in store.get_facts():
            if _k.startswith("learned:"):
                # fetch cites via helper using the learned key
                cite_urls.extend(store.get_citation_urls_for_key(_k))
                if len(cite_urls) >= 5:
                    break
    except Exception:
        pass
    digest = f"Daily digest: {header}"
    # Persist summary as a fact with sources if present
    date_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fact_key = f"summary:{date_key}"
    started = time.time()
    status = "ok"
    try:
        if cite_urls:
            srcs = [(u, "source") for u in cite_urls[:5]]
            store.add_fact_with_sources(fact_key, digest, srcs)
        else:
            store.add_fact(fact_key, digest)
        store.log_event("summary", digest)
    except Exception:
        # Best-effort persistence
        status = "fail"
        pass
    finally:
        _log_job_event(store, "daily-summary", status, started)
    return digest


def run_health_checks(ltm: LTM | None = None) -> int:
    """Run quick health checks: loggers, memory access, and policy sanity.

    Returns number of checks passed.
    """
    store = ltm or LTM()
    passed = 0
    # Check logging via audit path
    from nova.permissions import request_permission, Decision
    d = request_permission("healthcheck", "noop", path=None)
    if d in (Decision.APPROVED, Decision.DENIED):
        passed += 1
    # Memory CRUD smoke
    sid = store.add_source("https://example.org/health", "Health")
    fid = store.add_fact("health:check", "ok", source_id=sid)
    if any(r[0] == fid for r in store.get_facts("health:check")):
        passed += 1
    # Policy check for data dir vs outside
    from security import policies
    from pathlib import Path
    inside = Path(r"C:\\Nova\\data\\ok.txt")
    outside = Path(r"C:\\notnova\\x.txt")
    if policies.requires_elevation_for_path(inside) is False and policies.requires_elevation_for_path(outside) is True:
        passed += 1
    return passed
