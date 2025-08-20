from __future__ import annotations

from memory.store import STM, LTM
from memory.consolidator import consolidate
from memory.indexing import embed_text, cosine_similarity


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


def test_semantic_query_finds_related(monkeypatch) -> None:
    # No persistence, offline
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")

    ltm = LTM()
    # Seed semantically related facts with different wording
    ltm.add_fact("note:coffee_pref", "User likes double espresso with one sugar")
    ltm.add_fact("note:beverage", "Tea with lemon is preferred by guest")
    ltm.add_fact("note:city", "Paris is the capital of France")

    # Run consolidation to write vectors
    consolidate(ltm)

    # Query semantically similar content
    results = ltm.query_semantic("favorite coffee order double espresso")
    assert results, "Expected at least one semantic match"
    top = results[0]
    assert "espresso" in top[2].lower() or "coffee" in top[2].lower()


def test_kg_relations_store_and_query(monkeypatch) -> None:
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")

    ltm = LTM()
    # Directly add relations
    rid = ltm.add_relation("France", "capital_of", "Paris")
    assert rid is not None
    rels = ltm.get_relations(subj="France", pred="capital_of")
    assert rels and rels[0][3] == "Paris"
    # Traversals
    neigh = ltm.neighbors("France")
    assert any(p == "capital_of" and o == "Paris" for p, o in neigh)
    inv = ltm.inverse_neighbors("Paris")
    assert any(s == "France" and p == "capital_of" for s, p in inv)


def test_consolidation_extracts_relations(monkeypatch) -> None:
    monkeypatch.setenv("NOVA_NONINTERACTIVE", "1")
    monkeypatch.setenv("NOVA_PERMISSION_DEFAULT", "deny")
    ltm = LTM()
    ltm.add_fact("capital:france", "Paris")
    consolidate(ltm)
    rels = ltm.get_relations(subj="France", pred="capital_of", obj="Paris")
    assert rels, "Expected extracted relation from capital:france"
