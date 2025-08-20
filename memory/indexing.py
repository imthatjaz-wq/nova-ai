"""Lightweight keyword indexing and tiny local embeddings.

Provides:
- tokenize/index_text for keyword index
- embed_text: small bag-of-ngrams vector with token synonyms
- cosine_similarity for comparing sparse vectors
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import DefaultDict, Dict, Iterable, List, Set


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
STOPWORDS: Set[str] = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "is", "it"}

# Tiny synonym map to improve recall without external models
SYNONYMS: Dict[str, List[str]] = {
    "usa": ["united", "states", "america", "u.s.", "u.s.a"],
    "nyc": ["new", "york", "city"],
}


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


def _char_ngrams(text: str, n: int = 3) -> List[str]:
    s = ''.join(ch.lower() for ch in text if ch.isalnum() or ch.isspace())
    s = f"  {s}  "  # pad for start/end
    grams: List[str] = []
    for i in range(len(s) - n + 1):
        g = s[i : i + n]
        if any(ch.isalnum() for ch in g):
            grams.append(f"#g:{g}")
    return grams


def _expand_synonyms(tokens: List[str]) -> List[str]:
    expanded = list(tokens)
    for t in tokens:
        if t in SYNONYMS:
            expanded.extend(SYNONYMS[t])
    return expanded


def embed_text(text: str) -> Dict[str, float]:
    """Create a tiny local embedding as a sparse vector.

    Features: token terms (minus stopwords) + character trigrams.
    Weights: term frequency normalized to unit length.
    """
    toks = index_text(text)
    toks = _expand_synonyms(toks)
    grams = _char_ngrams(text)
    feats: Dict[str, float] = {}
    for f in toks + grams:
        feats[f] = feats.get(f, 0.0) + 1.0
    # L2 normalize
    norm = sum(v * v for v in feats.values()) ** 0.5 or 1.0
    for k in list(feats.keys()):
        feats[k] = feats[k] / norm
    return feats


def cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    # iterate over smaller dict for speed
    if len(a) > len(b):
        a, b = b, a
    return sum(a[k] * b.get(k, 0.0) for k in a.keys())
