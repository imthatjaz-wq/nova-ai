"""Templated NLG with citation hooks and safe fallbacks."""
from __future__ import annotations

from typing import Iterable, Optional


def with_citations(text: str, sources: Optional[Iterable[str]] = None) -> str:
    cites = list(sources or [])
    if not cites:
        return text
    return f"{text}\nSources: " + ", ".join(cites)


def answer_fact(question: str, fact: Optional[str], sources: Optional[Iterable[str]] = None) -> str:
    if not fact:
        return "I don't know yet. I can research that if you want."
    return with_citations(fact, sources)


def command_ack(message: str) -> str:
    return message


def smalltalk(reply: str) -> str:
    return reply


def format_help_banner() -> str:
    return (
        "Nova CLI — local assistant (Segment 1)\n"
        "Use `python -m ui.cli --help` to view commands."
    )
