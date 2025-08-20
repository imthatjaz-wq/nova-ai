from __future__ import annotations

from unittest.mock import patch

from conversation.nlu import interpret
from conversation.dialogue_manager import DialogueManager


def test_nlu_intents_and_slots() -> None:
    r = interpret("Open https://example.com")
    assert r.intent == "COMMAND" and r.slots.get("action") == "open_url"

    r2 = interpret("create file 'C:/Nova/data/x.txt'")
    assert r2.intent == "COMMAND" and r2.slots.get("action") == "create_file"
    assert r2.slots.get("path", "").endswith("x.txt")

    r3 = interpret("What is the capital of France?")
    assert r3.intent == "QUESTION" and r3.slots.get("qtype") == "capital_of"


def test_dialogue_context_and_dont_know(monkeypatch) -> None:
    # Deny persistence to avoid writing
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")

    dm = DialogueManager()
    # Ask something unknown; search_web will be mocked to return empty
    with patch("conversation.dialogue_manager.search_web", return_value=[]):
        resp = dm.handle("What's the capital of Atlantis?")
        assert "don't know" in resp.lower()
        # Context carries last nova reply
        assert dm.stm.recent()[-1][0] == "nova"


def test_dialogue_command_flow(monkeypatch) -> None:
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")

    dm = DialogueManager()
    resp = dm.handle("open https://example.com")
    assert "Would open URL" in resp

    resp2 = dm.handle("create file 'C:/Nova/data/demo.txt'")
    assert resp2.startswith("[denied]") or "Would create" in resp2


def test_coref_open_it_uses_last_object(monkeypatch) -> None:
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")
    dm = DialogueManager()
    dm.handle("open https://example.com")
    resp = dm.handle("open it")
    assert "Would open URL" in resp


def test_open_app_and_reminder(monkeypatch) -> None:
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")
    dm = DialogueManager()
    r1 = interpret("launch notepad")
    assert r1.intent == "COMMAND" and r1.slots.get("action") == "open_app"
    resp1 = dm.handle("launch notepad")
    assert "Would open app" in resp1 or "app not found" in resp1
    resp2 = dm.handle("remind me in 1 minute to stretch")
    assert "[scheduled]" in resp2


def test_question_uses_aggregator_and_persists(monkeypatch) -> None:
    # Noninteractive deny: LTM will be in-memory but available
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")

    dm = DialogueManager()
    # Mock aggregate_sources to return a deterministic summary + 2 citations
    fake_summary = "Paris is the capital of France."
    fake_citations = [
        {"name": "Wikipedia", "snippet": "Capital of France", "url": "https://en.wikipedia.org/wiki/Paris"},
        {"name": "Britannica", "snippet": "Paris", "url": "https://www.britannica.com/place/Paris"},
    ]
    with patch("conversation.dialogue_manager.aggregate_sources", return_value=(fake_summary, fake_citations)):
        resp = dm.handle("What is the capital of France?")
        assert "Sources:" in resp and "wikipedia" in resp.lower()
        # A subsequent ask should hit memory and include the same fact
        resp2 = dm.handle("What is the capital of France?")
        assert "don't know" not in resp2.lower()


def test_memory_hit_bypasses_internet(monkeypatch) -> None:
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")

    dm = DialogueManager()
    # Seed memory directly
    ltm = dm.ensure_ltm()
    ltm.add_fact("capital:france", "Paris")
    # Ensure we don't call aggregate_sources when memory has the fact
    with patch("conversation.dialogue_manager.aggregate_sources") as agg:
        resp = dm.handle("What is the capital of France?")
        assert "Sources:" not in resp  # from seeded fact without cites
        agg.assert_not_called()


def test_memory_hit_returns_citations_when_available(monkeypatch) -> None:
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")

    dm = DialogueManager()
    ltm = dm.ensure_ltm()
    # Add two sources and facts for the key
    sid1 = ltm.add_source("https://en.wikipedia.org/wiki/Paris", "Wikipedia")
    sid2 = ltm.add_source("https://www.britannica.com/place/Paris", "Britannica")
    ltm.add_fact("capital:france", "Paris", source_id=sid1)
    ltm.add_fact("capital:france", "Paris", source_id=sid2)

    with patch("conversation.dialogue_manager.aggregate_sources") as agg:
        resp = dm.handle("What is the capital of France?")
        assert "Sources:" in resp and "wikipedia" in resp.lower()
        agg.assert_not_called()
