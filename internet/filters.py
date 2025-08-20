"""Content filters for web results: redact basic PII/unsafe tokens.

Simple, deterministic regex-based redaction to keep tests stable.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")

# Minimal profanity/unsafe words list (very small and neutral)
UNSAFE_WORDS: Tuple[str, ...] = (
    "kill",
    "suicide",
)


def sanitize_text(text: str) -> str:
    s = text or ""
    s = EMAIL_RE.sub("[redacted-email]", s)
    s = PHONE_RE.sub("[redacted-phone]", s)
    s = SSN_RE.sub("[redacted-ssn]", s)
    # Only redact likely card numbers with many digits; avoid over-redaction by requiring 13+ digits
    s = CARD_RE.sub("[redacted-card]", s)
    # Replace unsafe words with [redacted]
    for w in UNSAFE_WORDS:
        s = re.sub(rf"\b{re.escape(w)}\b", "[redacted]", s, flags=re.IGNORECASE)
    return s


def sanitize_citations(citations: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for c in citations:
        d = dict(c)
        if "name" in d:
            d["name"] = sanitize_text(str(d.get("name", "")))
        if "snippet" in d:
            d["snippet"] = sanitize_text(str(d.get("snippet", "")))
        out.append(d)
    return out


def sanitize_summary_and_citations(summary: str, citations: List[Dict[str, str]]) -> tuple[str, List[Dict[str, str]]]:
    return sanitize_text(summary or ""), sanitize_citations(citations or [])
