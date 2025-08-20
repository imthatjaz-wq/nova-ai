"""Memory module: STM and LTM (SQLite) with gated persistence."""
from __future__ import annotations

import sqlite3
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Optional, Tuple, Dict

from nova.config import Settings
from nova.permissions import request_permission, Decision


class STM:
    """Simple short-term memory buffer (no persistence)."""

    def __init__(self, capacity: int = 20) -> None:
        self.capacity = capacity
        self._buf: Deque[Tuple[str, str]] = deque(maxlen=capacity)

    def add(self, role: str, text: str) -> None:
        self._buf.append((role, text))

    def recent(self) -> list[Tuple[str, str]]:
        return list(self._buf)


@dataclass
class LTMConfig:
    db_path: Path
    persistent: bool


class LTM:
    """Long-term memory store using SQLite.

    On initialization, requests permission to use a persistent DB at C:\\Nova\\data\\memory.db.
    If denied or unavailable, falls back to in-memory DB for the session.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or Settings()
        file_path = self.settings.data_dir / "memory.db"
        decision = request_permission(
            action="open/create persistent memory",
            resource="memory.db",
            path=file_path,
        )
        self._config = LTMConfig(db_path=file_path, persistent=(decision is Decision.APPROVED))
        self._conn = self._connect()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        if self._config.persistent and self.settings.data_dir.exists():
            return sqlite3.connect(str(self._config.db_path))
        return sqlite3.connect(":memory:")

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                source_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS prefs (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                title TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS fact_vectors (
                fact_id INTEGER PRIMARY KEY,
                vector_json TEXT NOT NULL,
                FOREIGN KEY(fact_id) REFERENCES facts(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subj TEXT NOT NULL,
                pred TEXT NOT NULL,
                obj TEXT NOT NULL,
                source_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(subj, pred, obj)
            )
            """
        )
        self._conn.commit()

    # Facts
    def add_fact(self, key: str, value: str, source_id: Optional[int] = None) -> int:
        cur = self._conn.cursor()
        cur.execute("INSERT INTO facts(key, value, source_id) VALUES (?, ?, ?)", (key, value, source_id))
        self._conn.commit()
        return int(cur.lastrowid)

    def get_facts(self, key: Optional[str] = None) -> list[tuple[int, str, str, Optional[int], str]]:
        cur = self._conn.cursor()
        if key is None:
            cur.execute("SELECT id, key, value, source_id, created_at FROM facts ORDER BY id DESC")
        else:
            cur.execute(
                "SELECT id, key, value, source_id, created_at FROM facts WHERE key = ? ORDER BY id DESC",
                (key,),
            )
        return list(cur.fetchall())

    # Events
    def log_event(self, type_: str, content: str) -> int:
        cur = self._conn.cursor()
        cur.execute("INSERT INTO events(type, content) VALUES (?, ?)", (type_, content))
        self._conn.commit()
        return int(cur.lastrowid)

    def get_events(self, type_: Optional[str] = None) -> list[tuple[int, str, str, str]]:
        cur = self._conn.cursor()
        if type_ is None:
            cur.execute("SELECT id, type, content, created_at FROM events ORDER BY id DESC")
        else:
            cur.execute("SELECT id, type, content, created_at FROM events WHERE type = ? ORDER BY id DESC", (type_,))
        return list(cur.fetchall())

    # Prefs
    def set_pref(self, key: str, value: str) -> None:
        cur = self._conn.cursor()
        cur.execute("INSERT INTO prefs(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        self._conn.commit()

    def get_pref(self, key: str) -> Optional[str]:
        cur = self._conn.cursor()
        cur.execute("SELECT value FROM prefs WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else None

    # Sources
    def add_source(self, url: str, title: str) -> int:
        cur = self._conn.cursor()
        cur.execute("INSERT INTO sources(url, title) VALUES (?, ?)", (url, title))
        self._conn.commit()
        return int(cur.lastrowid)

    def get_source(self, source_id: int) -> Optional[tuple[int, str, str]]:
        cur = self._conn.cursor()
        cur.execute("SELECT id, url, title FROM sources WHERE id = ?", (source_id,))
        row = cur.fetchone()
        return (int(row[0]), str(row[1]), str(row[2])) if row else None

    # Aggregation helpers
    def add_fact_with_sources(self, key: str, value: str, sources: list[tuple[str, str]]) -> int:
        """Store a fact and attach multiple sources; returns fact id.

        sources: list of (url, title)
        """
        last_id = -1
        for url, title in sources:
            sid = self.add_source(url, title)
            last_id = self.add_fact(key, value, source_id=sid)
        if last_id == -1:
            last_id = self.add_fact(key, value, source_id=None)
        return last_id

    def get_citation_urls_for_key(self, key: str, limit: int = 5) -> list[str]:
        """Return up to 'limit' citation URLs associated with facts for this key."""
        urls: list[str] = []
        cur = self._conn.cursor()
        cur.execute("SELECT source_id FROM facts WHERE key = ? AND source_id IS NOT NULL ORDER BY id DESC", (key,))
        rows = cur.fetchall()
        seen = set()
        for (sid,) in rows:
            cur.execute("SELECT url FROM sources WHERE id = ?", (sid,))
            r = cur.fetchone()
            if r and r[0] and r[0] not in seen:
                urls.append(str(r[0]))
                seen.add(r[0])
                if len(urls) >= limit:
                    break
        return urls

    # Semantic vectors
    def upsert_fact_vector(self, fact_id: int, vector: Dict[str, float]) -> None:
        import json as _json
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO fact_vectors(fact_id, vector_json) VALUES (?, ?) "
            "ON CONFLICT(fact_id) DO UPDATE SET vector_json=excluded.vector_json",
            (fact_id, _json.dumps(vector)),
        )
        self._conn.commit()

    def get_fact_vector(self, fact_id: int) -> Optional[Dict[str, float]]:
        import json as _json
        cur = self._conn.cursor()
        cur.execute("SELECT vector_json FROM fact_vectors WHERE fact_id = ?", (fact_id,))
        row = cur.fetchone()
        return (_json.loads(row[0]) if row and row[0] else None)

    def query_semantic(self, text: str, *, top_k: int = 3) -> list[tuple[int, str, str, Optional[int], str, float]]:
        """Return top_k facts most similar to the query text using local tiny embeddings.

        Returns tuples of (id, key, value, source_id, created_at, score) sorted by score desc.
        """
        from .indexing import embed_text, cosine_similarity
        qv = embed_text(text)
        cur = self._conn.cursor()
        cur.execute("SELECT id, key, value, source_id, created_at FROM facts ORDER BY id DESC")
        rows = list(cur.fetchall())
        scored = []
        for r in rows:
            fid = int(r[0])
            vec = self.get_fact_vector(fid)
            # If no vector yet, embed on the fly (for fresh facts) but don't store here
            if vec is None:
                from .indexing import embed_text as _embed
                vec = _embed(str(r[2]))
            score = cosine_similarity(qv, vec)
            if score > 0:
                scored.append((*r, float(score)))
        scored.sort(key=lambda x: x[-1], reverse=True)
        return scored[:top_k]

    # Knowledge graph relations
    def add_relation(self, subj: str, pred: str, obj: str, *, source_id: Optional[int] = None) -> int | None:
        cur = self._conn.cursor()
        try:
            cur.execute(
                "INSERT OR IGNORE INTO relations(subj, pred, obj, source_id) VALUES (?, ?, ?, ?)",
                (subj, pred, obj, source_id),
            )
            self._conn.commit()
            # fetch id if it exists
            cur.execute("SELECT id FROM relations WHERE subj=? AND pred=? AND obj=?", (subj, pred, obj))
            row = cur.fetchone()
            return int(row[0]) if row else None
        except Exception:
            return None

    def get_relations(
        self,
        subj: Optional[str] = None,
        pred: Optional[str] = None,
        obj: Optional[str] = None,
    ) -> list[tuple[int, str, str, str, Optional[int], str]]:
        cur = self._conn.cursor()
        clauses = []
        params: list[object] = []
        if subj is not None:
            clauses.append("subj = ?")
            params.append(subj)
        if pred is not None:
            clauses.append("pred = ?")
            params.append(pred)
        if obj is not None:
            clauses.append("obj = ?")
            params.append(obj)
        sql = "SELECT id, subj, pred, obj, source_id, created_at FROM relations"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id DESC"
        cur.execute(sql, tuple(params))
        return list(cur.fetchall())

    def neighbors(self, subj: str) -> list[tuple[str, str]]:
        """Return list of (pred, obj) for 1-hop outgoing edges from subj."""
        cur = self._conn.cursor()
        cur.execute("SELECT pred, obj FROM relations WHERE subj = ? ORDER BY id DESC", (subj,))
        return [(str(r[0]), str(r[1])) for r in cur.fetchall()]

    def inverse_neighbors(self, obj: str) -> list[tuple[str, str]]:
        """Return list of (subj, pred) for 1-hop incoming edges to obj."""
        cur = self._conn.cursor()
        cur.execute("SELECT subj, pred FROM relations WHERE obj = ? ORDER BY id DESC", (obj,))
        return [(str(r[0]), str(r[1])) for r in cur.fetchall()]

    def is_persistent(self) -> bool:
        return self._config.persistent

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
