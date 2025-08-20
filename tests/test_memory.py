from __future__ import annotations

from memory.store import STM, LTM
from memory.consolidator import consolidate


def test_stm_buffer_capacity() -> None:
    stm = STM(capacity=3)
    stm.add("user", "a")
    stm.add("nova", "b")
    stm.add("user", "c")
    stm.add("nova", "d")  # should evict oldest
    recent = stm.recent()
    assert len(recent) == 3
    assert recent[0][1] == "b"
    assert recent[-1][1] == "d"


def test_ltm_crud_nonpersistent(monkeypatch) -> None:
    # Noninteractive deny -> in-memory DB
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")
    ltm = LTM()
    assert ltm.is_persistent() is False

    sid = ltm.add_source("https://example.com", "Example")
    fid = ltm.add_fact("capital:france", "paris", source_id=sid)
    ltm.set_pref("theme", "dark")

    facts = ltm.get_facts("capital:france")
    assert any(r[2] == "paris" for r in facts)
    assert ltm.get_pref("theme") == "dark"
    assert ltm.get_source(sid) is not None


def test_consolidation_creates_event(monkeypatch) -> None:
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")
    ltm = LTM()
    before = len(ltm.get_events("consolidation"))
    consolidate(ltm)
    after = len(ltm.get_events("consolidation"))
    assert after == before + 1
