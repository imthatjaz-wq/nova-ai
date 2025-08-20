"""Memory module: STM and LTM (SQLite) with gated persistence."""
from __future__ import annotations

import sqlite3
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Iterable, Optional, Tuple

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

    def is_persistent(self) -> bool:
        return self._config.persistent

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
