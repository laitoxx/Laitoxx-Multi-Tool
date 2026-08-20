"""Local TTL cache for normalized OSINT results."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from laitoxx.core.settings.paths import OSINT_CACHE_FILE


class OSINTCache:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or OSINT_CACHE_FILE)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _init_db(self):
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    namespace TEXT NOT NULL,
                    query TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )"""
            )
            db.execute("CREATE INDEX IF NOT EXISTS idx_cache_expiry ON cache_entries(expires_at)")

    @staticmethod
    def make_key(namespace: str, query: str) -> str:
        normalized = f"{namespace.strip().lower()}\0{query.strip().lower()}"
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get(self, namespace: str, query: str) -> Any | None:
        key = self.make_key(namespace, query)
        now = time.time()
        with self._connect() as db:
            row = db.execute("SELECT value_json, expires_at FROM cache_entries WHERE cache_key=?", (key,)).fetchone()
            if not row:
                return None
            if row[1] <= now:
                db.execute("DELETE FROM cache_entries WHERE cache_key=?", (key,))
                return None
            return json.loads(row[0])

    def set(self, namespace: str, query: str, value: Any, ttl: int = 3600) -> Any:
        now = time.time()
        with self._connect() as db:
            db.execute(
                """INSERT OR REPLACE INTO cache_entries
                   (cache_key, namespace, query, value_json, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    self.make_key(namespace, query),
                    namespace,
                    query,
                    json.dumps(value, ensure_ascii=False, default=str),
                    now,
                    now + max(1, ttl),
                ),
            )
        return value

    def get_or_set(self, namespace: str, query: str, loader: Callable[[], Any], ttl: int = 3600):
        cached = self.get(namespace, query)
        if cached is not None:
            return cached, True
        return self.set(namespace, query, loader(), ttl), False

    def clear_expired(self) -> int:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM cache_entries WHERE expires_at <= ?", (time.time(),))
            return cursor.rowcount

    def clear_namespace_prefix(self, prefix: str) -> int:
        """Delete one feature's cache without touching other OSINT data."""
        normalized = prefix.strip().lower()
        if not normalized:
            raise ValueError("Cache namespace prefix must not be empty")
        with self._connect() as db:
            cursor = db.execute(
                "DELETE FROM cache_entries WHERE substr(lower(namespace), 1, ?) = ?",
                (len(normalized), normalized),
            )
            return cursor.rowcount

    def stats(self) -> dict[str, int]:
        with self._connect() as db:
            total = db.execute("SELECT COUNT(*) FROM cache_entries").fetchone()[0]
            active = db.execute("SELECT COUNT(*) FROM cache_entries WHERE expires_at > ?", (time.time(),)).fetchone()[0]
        return {"total": total, "active": active, "expired": total - active}


cache = OSINTCache()
