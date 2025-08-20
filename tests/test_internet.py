from __future__ import annotations
from unittest.mock import patch

import requests

from internet.fetch import polite_get, set_cache_ttl, get_rate_limiter
from internet.search import search_web, aggregate_sources
from internet.filters import sanitize_text, sanitize_citations
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


def test_aggregate_sources_prefers_wiki_and_adds_bing(monkeypatch) -> None:
    # Provide a fake key so search_web path can run, but we'll stub HTTP
    monkeypatch.setenv("NOVA_SEARCH_API_KEY", "x")

    # fake requests.get to simulate wiki and bing responses based on URL
    def fake_get(url, headers=None, timeout=None):
        class Fake:
            status_code = 200

            def __init__(self, payload):
                self._payload = payload

            def json(self):
                return self._payload

        if "wikipedia.org/api/rest_v1/page/summary" in url:
            return Fake({
                "title": "Paris",
                "extract": "Paris is the capital and most populous city of France.",
                "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Paris"}},
            })
        if "api.bing.microsoft.com" in url:
            return Fake({
                "webPages": {"value": [
                    {"name": "Britannica", "snippet": "Paris is the capital of France.", "url": "https://www.britannica.com/place/Paris"},
                    {"name": "Example", "snippet": "Should be filtered by allowlist", "url": "https://example.com/paris"},
                ]}
            })
        # robots or other
        return Fake({})

    with patch.object(requests, 'get', side_effect=fake_get):
        summary, cites = aggregate_sources("Paris")
        assert summary and isinstance(cites, list) and len(cites) >= 1
        # Wikipedia should be present, example.com filtered
        urls = [c.get('url','') for c in cites]
        assert any('wikipedia.org' in u for u in urls)
        assert all('example.com' not in u for u in urls)


def test_filters_redact_pii_and_unsafe() -> None:
    text = "Contact me at john.doe@example.com or 555-123-4567. Do not kill switches."
    s = sanitize_text(text)
    assert "[redacted-email]" in s and "[redacted-phone]" in s and "[redacted]" in s
    cites = sanitize_citations([
        {"name": "Email john.doe@example.com", "snippet": "Call 555-123-4567"}
    ])
    assert "[redacted-email]" in cites[0]["name"] and "[redacted-phone]" in cites[0]["snippet"]
