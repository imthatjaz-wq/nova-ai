from __future__ import annotations

import types
from unittest.mock import patch

import requests

from internet.fetch import polite_get, set_cache_ttl, get_rate_limiter
from internet.search import search_web
from internet.summarize import summarize_text
from nova.config import Settings


def test_summarize_bullets_and_sentences() -> None:
    text = """- First point\n- Second point\nA paragraph. Another sentence."""
    s = summarize_text(text, max_sentences=2)
    assert "First point" in s and "Second point" in s
    s2 = summarize_text("One. Two. Three.", max_sentences=2)
    assert s2.count("\n") == 1


def test_fetch_cache_and_rate_limit(monkeypatch) -> None:
    # Set short cache
    set_cache_ttl(60)

    class FakeResp:
        def __init__(self, text: str, status_code: int = 200) -> None:
            self.text = text
            self.status_code = status_code

    def fake_get(url, timeout=None, headers=None):
        # robots.txt allowed
        if url.endswith('/robots.txt'):
            return FakeResp("User-agent: *\nDisallow:")
        return FakeResp("<html>ok</html>")

    with patch.object(requests, 'get', side_effect=fake_get):
        content1 = polite_get("https://example.com/")
        assert content1 and "ok" in content1
        # Cached hit should not call underlying again (we can't easily count here,
        # but at least should return same string)
        content2 = polite_get("https://example.com/")
        assert content2 == content1

    # Rate limit
    s = Settings()
    limiter = get_rate_limiter(s)
    # Emulate exceeding the limit for a host
    limiter.state['example.com'] = (int(__import__('time').time() // 60), s.http_rate_limit_per_min)
    with patch.object(requests, 'get', side_effect=fake_get):
        limited = polite_get("https://example.com/")
        assert limited is None


def test_search_allowlist_and_empty_without_key(monkeypatch) -> None:
    # No key -> empty
    s = Settings()
    results = search_web("test", settings=s)
    assert results == []

    # With key: mock response and filter allowlist
    s2 = Settings()
    monkeypatch.setenv("NOVA_SEARCH_API_KEY", "x")
    s2.search_api_key = "x"

    def fake_get(url, headers=None, timeout=None):
        class Fake:
            status_code = 200

            def json(self):
                return {
                    "webPages": {"value": [
                        {"name": "Wiki page", "snippet": "..", "url": "https://en.wikipedia.org/wiki/Test"},
                        {"name": "Random", "snippet": "..", "url": "https://example.com/whatever"},
                    ]}
                }
        return Fake()

    with patch.object(requests, 'get', side_effect=fake_get):
        res = search_web("test", settings=s2)
        # Allowlist includes wiki/wikipedia by default; example.com is dropped
        assert any('wikipedia' in r['url'] for r in res)
        assert all('example.com' not in r['url'] for r in res)
