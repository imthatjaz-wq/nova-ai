"""Rule-based summarizer (deterministic).

Approach:
- Split into lines, extract bullet-like lines first
- Fallback to sentence-leading lines
- Limit to max_sentences; join with newline bullets
"""
from __future__ import annotations

import re
from typing import List


BULLET_RE = re.compile(r"^\s*([\-*•]|\d+\.)\s+(.*)")


def _bullets(text: str) -> List[str]:
    out: List[str] = []
    for line in text.splitlines():
        m = BULLET_RE.match(line)
        if m:
            body = m.group(2).strip()
            if body:
                out.append(body)
    return out


def _sentences(text: str) -> List[str]:
    # naive split on .!? keeping order
    raw = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in raw if s.strip()]


def summarize_text(text: str, max_sentences: int = 5) -> str:
    bullets = _bullets(text)
    if bullets:
        return "\n".join(bullets[:max_sentences])
    sents = _sentences(text)
    return "\n".join(sents[:max_sentences])
