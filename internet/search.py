"""Search wrapper with SafeSearch and domain allowlist.

Supports Bing Web Search (if NOVA_SEARCH_API_KEY set).
Does not call external APIs during tests (mock requests).
"""
from __future__ import annotations

import json
import logging
from typing import Callable, Dict, List, Optional
from urllib.parse import urlencode

import requests

from nova.config import Settings

logger = logging.getLogger("nova.search")


def _allow_domain(url: str, allowlist_csv: str) -> bool:
    allow_parts = [s.strip().lower() for s in allowlist_csv.split(',') if s.strip()]
    url_l = url.lower()
    return any(part in url_l for part in allow_parts) if allow_parts else True


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
