from __future__ import annotations

from unittest.mock import patch

from nova.jobs import run_gap_research
from nova.jobs import run_daily_summary
from memory.store import LTM


def test_run_gap_research_uses_aggregator_and_stores_sources(monkeypatch) -> None:
    # In-memory LTM only
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")

    ltm = LTM()
    # Seed a gap from a prior conversation
    ltm.log_event("chat", "user: What is the capital of France? | nova: I don't know yet. I can research that if you want.")

    fake_summary = "Paris is the capital of France."
    fake_citations = [
        {"name": "Wikipedia", "snippet": "Capital of France", "url": "https://en.wikipedia.org/wiki/Paris"},
        {"name": "Britannica", "snippet": "Paris", "url": "https://www.britannica.com/place/Paris"},
    ]
    with patch("nova.jobs.aggregate_sources", return_value=(fake_summary, fake_citations)):
        count = run_gap_research(ltm, max_items=2)
        assert count == 1
        facts = ltm.get_facts("learned:what is the capital of france?")
        assert facts and any("Paris" in f[2] for f in facts)


def test_inbox_and_daily_summary(monkeypatch) -> None:
    # Deny writes for safety; DB will be in-memory
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")
    from conversation.dialogue_manager import DialogueManager
    dm = DialogueManager()
    # Trigger unknown question inbox entry
    with patch("conversation.dialogue_manager.aggregate_sources", return_value=("", [])):
        _ = dm.handle("What's the capital of Atlantis?")
    ltm = dm.ensure_ltm()
    inbox = ltm.get_events("inbox")
    assert any("question:" in c for _i, _t, c, _ts in inbox)
    # Generate daily summary
    digest = run_daily_summary(ltm)
    assert digest.startswith("Daily digest:")
    # Persisted as summary fact
    from datetime import datetime
    key = f"summary:{datetime.utcnow().strftime('%Y-%m-%d')}"
    assert ltm.get_facts(key)

def test_jobs_status_events(monkeypatch) -> None:
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")
    ltm = LTM()
    # Trigger all three jobs
    from nova.jobs import run_nightly, run_gap_research
    # Seed a gap
    ltm.log_event("chat", "user: Q? | nova: I don't know yet.")
    run_nightly(ltm)
    run_gap_research(ltm, max_items=1)
    _ = run_daily_summary(ltm)
    # Ensure job events recorded with duration and status
    rows = ltm.get_events("job")
    assert any("name=nightly" in c and "duration_ms=" in c for _i, _t, c, _ts in rows)
    assert any("name=research" in c and "status=" in c for _i, _t, c, _ts in rows)
    assert any("name=daily-summary" in c and "duration_ms=" in c for _i, _t, c, _ts in rows)
