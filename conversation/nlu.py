"""Regex/keyword-based NLU: intents and simple slot extraction."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict


QUESTION_RE = re.compile(r"\?\s*$")
URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
OPEN_RE = re.compile(r"^(open|launch)\b", re.IGNORECASE)
CREATE_FILE_RE = re.compile(r"\bcreate\s+file\b", re.IGNORECASE)
CAPITAL_OF_RE = re.compile(r"capital\s+of\s+([A-Za-z\s]+)", re.IGNORECASE)


@dataclass
class NLUResult:
    intent: str
    text: str
    slots: Dict[str, str] = field(default_factory=dict)


def _strip(text: str) -> str:
    return text.strip()


def interpret(text: str) -> NLUResult:
    t = _strip(text)
    slots: Dict[str, str] = {}

    # URL open command
    if URL_RE.search(t) or OPEN_RE.search(t):
        url_match = URL_RE.search(t)
        if url_match:
            slots["action"] = "open_url"
            slots["url"] = url_match.group(0)
            return NLUResult(intent="COMMAND", text=t, slots=slots)

    # Create file command
    if CREATE_FILE_RE.search(t):
        slots["action"] = "create_file"
        # rudimentary path extract in quotes
        m = re.search(r"\"([^\"]+)\"|'([^']+)'", t)
        if m:
            slots["path"] = m.group(1) or m.group(2)
        return NLUResult(intent="COMMAND", text=t, slots=slots)

    # Question?
    if QUESTION_RE.search(t):
        # capture simple patterns
        m = CAPITAL_OF_RE.search(t)
        if m:
            country = m.group(1).strip().lower()
            slots["qtype"] = "capital_of"
            slots["country"] = country
        return NLUResult(intent="QUESTION", text=t, slots=slots)

    # Default chat
    return NLUResult(intent="CHAT", text=t, slots=slots)
