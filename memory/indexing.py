"""Lightweight keyword indexing (no embeddings)."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import DefaultDict, Dict, Iterable, List, Set


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
STOPWORDS: Set[str] = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "is", "it"}


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def index_text(text: str) -> list[str]:
    return [t for t in tokenize(text) if t not in STOPWORDS]


class InvertedIndex:
    def __init__(self) -> None:
        self._index: DefaultDict[str, Set[int]] = defaultdict(set)

    def add(self, doc_id: int, text: str) -> None:
        for tok in index_text(text):
            self._index[tok].add(doc_id)

    def query(self, terms: Iterable[str]) -> Set[int]:
        result: Set[int] = set()
        for term in terms:
            tok = term.lower()
            if tok in self._index:
                result.update(self._index[tok])
        return result
