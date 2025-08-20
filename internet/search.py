"""Search providers and multi-source aggregator with allowlist.

Supports Bing Web Search (if NOVA_SEARCH_API_KEY set).
Includes a simple Wikipedia provider using summary endpoint.
Does not call external APIs during tests (mock requests).
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urlparse

import requests

from nova.config import Settings
from .filters import sanitize_summary_and_citations

logger = logging.getLogger("nova.search")


def _allow_domain(url: str, allowlist_csv: str) -> bool:
    """Strict host-based allowlist check.

    - If allowlist empty -> allow all.
    - If token contains a dot (e.g., wikipedia.org), allow host == token or host endswith "." + token.
    - If token has no dot (e.g., 'edu'), match exact host label equality (e.g., 'edu' matches 'example.edu' TLD? not on Windows; treat as label match only).
    """
    host = urlparse(url).hostname or ""
    host = host.lower()
    parts = [s.strip().lower() for s in allowlist_csv.split(',') if s.strip()]
    if not parts:
        return True
    for tok in parts:
        if '.' in tok:
            if host == tok or host.endswith('.' + tok):
                return True
        else:
            # label-aware: match any dot-separated label equal to tok
            labels = host.split('.')
            if tok in labels:
                return True
    return False


def search_web(
    query: str,
    *,
    settings: Optional[Settings] = None,
    http_get: Optional[Callable[..., requests.Response]] = None,
) -> List[Dict[str, str]]:
    s = settings or Settings()
    provider = s.search_provider.lower()
    if not s.search_api_key:
        logger.info("Search API key not set; returning empty results")
        return []
    if provider not in ("bing",):
        logger.info("Unsupported search provider=%s", provider)
        return []
    params = {
        "q": query,
        "mkt": "en-US",
        "safeSearch": "Strict" if s.safesearch.lower() in ("on", "strict") else "Moderate",
        "count": 5,
        "textDecorations": False,
        "textFormat": "Raw",
    }
    url = f"https://api.bing.microsoft.com/v7.0/search?{urlencode(params)}"
    headers = {"Ocp-Apim-Subscription-Key": s.search_api_key}
    getter = http_get or requests.get
    try:
        resp = getter(url, headers=headers, timeout=10)
        if resp.status_code < 200 or resp.status_code >= 300:
            return []
        data = resp.json()
        web_pages = data.get("webPages", {}).get("value", [])
        results: List[Dict[str, str]] = []
        for item in web_pages:
            u = item.get("url", "")
            if not _allow_domain(u, s.domain_allowlist):
                continue
            results.append({
                "name": item.get("name", ""),
                "snippet": item.get("snippet", ""),
                "url": u,
            })
        return results
    except Exception as e:
        logger.debug("Search failed: %s", e)
        return []


def _wiki_summary(query: str, http_get: Optional[Callable[..., requests.Response]] = None) -> List[Dict[str, str]]:
    """Fetch a brief summary from Wikipedia.

    In tests, http_get is monkeypatched. Returns at most one result.
    """
    getter = http_get or requests.get
    try:
        # Simple API: https://en.wikipedia.org/api/rest_v1/page/summary/<title>
        # Heuristic: strip common question phrasing to derive a title
        q = query.strip()
        lowers = q.lower()
        for pref in ("what is ", "what's ", "who is ", "where is ", "capital of "):
            if lowers.startswith(pref):
                q = q[len(pref):]
                break
        # Simple normalization
        title = q.strip().rstrip('?').replace(" ", "%20")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
        resp = getter(url, timeout=10, headers={"Accept": "application/json"})
        if resp.status_code < 200 or resp.status_code >= 300:
            return []
        data = resp.json()
        page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "") or data.get("url", "")
        # Filter through allowlist
        s = Settings()
        if not _allow_domain(page_url or "https://en.wikipedia.org", s.domain_allowlist):
            return []
        return [{
            "name": data.get("title", "Wikipedia"),
            "snippet": data.get("extract", ""),
            "url": page_url or f"https://en.wikipedia.org/wiki/{title}",
        }]
    except Exception as e:
        logger.debug("Wiki fetch failed: %s", e)
        return []


def aggregate_sources(query: str, *, http_get: Optional[Callable[..., requests.Response]] = None, settings: Optional[Settings] = None) -> Tuple[str, List[Dict[str, str]]]:
    """Aggregate 2-3 sources (Wikipedia + Bing top results) and return a brief summary with citations.

    Returns (summary, citations), where citations is a list of {name,snippet,url}.
    """
    s = settings or Settings()
    citations: List[Dict[str, str]] = []

    # Wikipedia (preferred concise summary)
    wiki = _wiki_summary(query, http_get=http_get)
    if wiki:
        citations.extend(wiki)

    # Bing results (if key present)
    # Use existing search_web which already allowlists
    bing = search_web(query, settings=s, http_get=http_get)
    if bing:
        # Add diverse domains until we reach 3–5 total citations
        seen = {urlparse(c.get("url"," ")).hostname for c in citations if c.get("url")}
        for item in bing:
            host = urlparse(item.get("url", "")).hostname or ""
            if host and host not in seen:
                citations.append(item)
                seen.add(host)
            if len(citations) >= 5:
                break

    # Compose a brief cross-checked summary: take top snippets/title
    if not citations:
        return ("", [])
    parts: List[str] = []
    for c in citations[:3]:
        title = c.get("name", "").strip()
        snip = c.get("snippet", "").strip()
        if title and snip:
            parts.append(f"{title}. {snip}")
        elif title:
            parts.append(title)
        elif snip:
            parts.append(snip)
    from .summarize import summarize_text
    summary = summarize_text("\n".join(parts), max_sentences=3)
    # Sanitize summary and citations before returning
    summary, citations = sanitize_summary_and_citations(summary, citations)
    return (summary, citations)
