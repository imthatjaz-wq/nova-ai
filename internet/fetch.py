"""Polite HTTP client with simple caching, robots best-effort, and rate limiting."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

import requests

from nova.config import Settings

logger = logging.getLogger("nova.net")


_CACHE: Dict[str, Tuple[float, str]] = {}
_CACHE_TTL_SECONDS = 300


def set_cache_ttl(seconds: int) -> None:
    global _CACHE_TTL_SECONDS
    _CACHE_TTL_SECONDS = max(0, int(seconds))


@dataclass
class RateLimiter:
    max_per_min: int
    # state: (host -> (minute_window, count))
    state: Dict[str, Tuple[int, int]]

    def __init__(self, max_per_min: int) -> None:
        self.max_per_min = max_per_min
        self.state = {}

    def allow(self, host: str) -> bool:
        minute = int(time.time() // 60)
        window, count = self.state.get(host, (minute, 0))
        if window != minute:
            window, count = minute, 0
        if count >= self.max_per_min > 0:
            return False
        self.state[host] = (window, count + 1)
        return True


_RATE_LIMITER: Optional[RateLimiter] = None


def get_rate_limiter(settings: Optional[Settings] = None) -> RateLimiter:
    global _RATE_LIMITER
    if _RATE_LIMITER is None:
        s = settings or Settings()
        _RATE_LIMITER = RateLimiter(s.http_rate_limit_per_min)
    return _RATE_LIMITER


def _fetch(url: str, *, timeout: int, headers: Dict[str, str]) -> Optional[str]:
    try:
        resp = requests.get(url, timeout=timeout, headers=headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            return resp.text
        return None
    except Exception as e:
        logger.debug("HTTP GET failed: %s", e)
        return None


def _robots_txt_url(url: str) -> str:
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}/robots.txt"


def _is_allowed_by_robots(url: str, robots_text: Optional[str]) -> bool:
    if not robots_text:
        return True
    ua_all = False
    disallows = []
    for line in robots_text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.lower().startswith('user-agent:'):
            ua = line.split(':', 1)[1].strip()
            ua_all = (ua == '*' )
        elif ua_all and line.lower().startswith('disallow:'):
            path = line.split(':', 1)[1].strip()
            if path:
                disallows.append(path)
    path = urlparse(url).path or '/'
    for rule in disallows:
        if path.startswith(rule):
            return False
    return True


def polite_get(url: str, *, timeout: int = 10, settings: Optional[Settings] = None) -> Optional[str]:
    s = settings or Settings()
    # rate limit per host (applies even to cached responses to satisfy policy/tests)
    host = urlparse(url).netloc
    limiter = get_rate_limiter(s)
    if not limiter.allow(host):
        logger.info("Rate limit exceeded for host=%s", host)
        return None

    # cache (after rate limit)
    now = time.time()
    cached = _CACHE.get(url)
    if cached and (now - cached[0] <= _CACHE_TTL_SECONDS):
        return cached[1]

    # robots best-effort
    robots = _fetch(_robots_txt_url(url), timeout=timeout, headers={"User-Agent": "NovaAssistant/0.1 (+local)"})
    if not _is_allowed_by_robots(url, robots):
        logger.info("Blocked by robots.txt: %s", url)
        return None

    headers = {
        "User-Agent": "NovaAssistant/0.1 (+local)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    content = _fetch(url, timeout=timeout, headers=headers)
    if content is not None:
        _CACHE[url] = (now, content)
    return content
