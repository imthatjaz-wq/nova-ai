from __future__ import annotations

from unittest.mock import patch

from nova.jobs import find_gaps, run_gap_research, run_nightly
from memory.store import LTM


def test_gap_detection_and_research(monkeypatch) -> None:
    # Non-persistent memory for tests
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")

    ltm = LTM()
    # Simulate a chat where Nova didn't know
    ltm.log_event("chat", "user: What's the capital of Atlantis? | nova: I don't know yet. I can research that if you want.")

    gaps = find_gaps(ltm)
    assert gaps and "Atlantis" in gaps[0]

    def fake_search(q):
        return [{"name": "Mythical Atlantis", "snippet": "City in legend.", "url": "https://en.wikipedia.org/wiki/Atlantis"}]

    with patch("nova.jobs.search_web", side_effect=fake_search):
        count = run_gap_research(ltm, max_items=1)
        assert count == 1
        # fact saved with source
        facts = ltm.get_facts("learned:what's the capital of atlantis?")
        assert facts
        # source exists
        sid = facts[0][3]
        assert sid is not None
        src = ltm.get_source(int(sid))
        assert src is not None and "wikipedia" in src[1]


def test_nightly_consolidation(monkeypatch) -> None:
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")

    ltm = LTM()
    before = len(ltm.get_events("consolidation"))
    run_nightly(ltm)
    after = len(ltm.get_events("consolidation"))
    assert after == before + 1
