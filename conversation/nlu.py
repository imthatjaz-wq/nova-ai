"""Regex/keyword-based NLU: intents and simple slot extraction.

Phase B: expand intents/entities for dates/times, file paths, app names, and simple confirms.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Optional


QUESTION_RE = re.compile(r"\?\s*$")
URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
OPEN_RE = re.compile(r"^(open|launch)\b", re.IGNORECASE)
CREATE_FILE_RE = re.compile(r"\bcreate\s+file\b", re.IGNORECASE)
OPEN_FILE_RE = re.compile(r"\bopen\s+(?:the\s+)?(?:file\s+)?", re.IGNORECASE)
APP_NAME_RE = re.compile(r"^(?:open|launch)\s+([A-Za-z0-9._-]+)$", re.IGNORECASE)
FILE_PATH_RE = re.compile(r"([A-Za-z]:\\[^\s'\"<>|?*]+)")
REMIND_RE = re.compile(r"remind\s+me\s+in\s+(\d+)\s*(seconds?|minutes?|hours?)(?:\s+to\s+(.+))?", re.IGNORECASE)
YES_RE = re.compile(r"^(yes|y|sure|ok|okay)\b", re.IGNORECASE)
NO_RE = re.compile(r"^(no|n|nah|nope)\b", re.IGNORECASE)
CAPITAL_OF_RE = re.compile(r"capital\s+of\s+([A-Za-z\s]+)", re.IGNORECASE)


@dataclass
class NLUResult:
    intent: str
    text: str
    slots: Dict[str, str] = field(default_factory=dict)


def _strip(text: str) -> str:
    return text.strip()


def _extract_path(t: str) -> Optional[str]:
    # Quote first
    m = re.search(r"\"([^\"]+)\"|'([^']+)'", t)
    if m:
        return m.group(1) or m.group(2)
    m2 = FILE_PATH_RE.search(t)
    if m2:
        return m2.group(1)
    return None


def interpret(text: str) -> NLUResult:
    t = _strip(text)
    slots: Dict[str, str] = {}

    # Yes/No confirms
    if YES_RE.search(t):
        return NLUResult(intent="CONFIRM", text=t, slots={"value": "yes"})
    if NO_RE.search(t):
        return NLUResult(intent="CONFIRM", text=t, slots={"value": "no"})

    # Reminder
    m_rem = REMIND_RE.search(t)
    if m_rem:
        qty = int(m_rem.group(1))
        unit = (m_rem.group(2) or "seconds").lower()
        msg = (m_rem.group(3) or "").strip()
        scale = 1
        if unit.startswith("minute"):
            scale = 60
        elif unit.startswith("hour"):
            scale = 3600
        slots.update({"action": "set_reminder", "in_seconds": str(qty * scale)})
        if msg:
            slots["message"] = msg
        return NLUResult(intent="COMMAND", text=t, slots=slots)

    # URL or generic open
    if URL_RE.search(t) or OPEN_RE.search(t):
        url_match = URL_RE.search(t)
        if url_match:
            slots["action"] = "open_url"
            slots["url"] = url_match.group(0)
            return NLUResult(intent="COMMAND", text=t, slots=slots)
        # open file path explicitly
        if OPEN_FILE_RE.search(t):
            p = _extract_path(t)
            if p:
                slots["action"] = "open_file"
                slots["path"] = p
            else:
                slots["action"] = "open"
            return NLUResult(intent="COMMAND", text=t, slots=slots)
        # open app name
        m_app = APP_NAME_RE.search(t)
        if m_app:
            slots["action"] = "open_app"
            slots["app"] = m_app.group(1)
            return NLUResult(intent="COMMAND", text=t, slots=slots)
        # ambiguous open (e.g., "open it")
        slots["action"] = "open"
        return NLUResult(intent="COMMAND", text=t, slots=slots)

    # Create file command
    if CREATE_FILE_RE.search(t):
        slots["action"] = "create_file"
        p = _extract_path(t)
        if p:
            slots["path"] = p
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
