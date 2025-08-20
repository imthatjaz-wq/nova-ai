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
