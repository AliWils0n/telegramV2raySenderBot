"""
database/db.py
==============
SQLite persistence layer.
Tracks every config URI we have ever seen so duplicates are never re-sent.
Thread-safe via a single shared connection with WAL mode.
"""

from __future__ import annotations
import asyncio
import hashlib
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import List, Set

logger = logging.getLogger(__name__)


def _hash(uri: str) -> str:
    """Stable SHA-256 fingerprint for a config URI."""
    return hashlib.sha256(uri.strip().encode()).hexdigest()


class ConfigDatabase:
    """
    Async-friendly wrapper around a SQLite database.
    All blocking I/O is run in a thread-pool executor so it doesn't
    block the asyncio event loop.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Open (or create) the database and apply the schema."""
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._apply_schema()
        logger.info("Database connected: %s", self.db_path)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @contextmanager
    def _cursor(self):
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cur.close()

    def _apply_schema(self) -> None:
        with self._cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS configs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash        TEXT    NOT NULL UNIQUE,
                    uri         TEXT    NOT NULL,
                    protocol    TEXT    NOT NULL,
                    source      TEXT    NOT NULL,
                    first_seen  TEXT    NOT NULL,
                    sent        INTEGER NOT NULL DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_hash ON configs(hash)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_sent ON configs(sent)
            """)

    # ── public API (sync, called via run_in_executor from async code) ──────────

    def is_known(self, uri: str) -> bool:
        """Return True if this URI has been seen before."""
        h = _hash(uri)
        with self._cursor() as cur:
            cur.execute("SELECT 1 FROM configs WHERE hash = ?", (h,))
            return cur.fetchone() is not None

    def get_known_hashes(self) -> Set[str]:
        """Return all stored hashes (for bulk dedup)."""
        with self._cursor() as cur:
            cur.execute("SELECT hash FROM configs")
            return {row[0] for row in cur.fetchall()}

    def save_configs(self, configs: List[dict]) -> int:
        """
        Bulk-insert new configs.  Each dict must have:
            uri, protocol, source
        Returns the number of rows actually inserted.
        """
        inserted = 0
        now = datetime.utcnow().isoformat()
        with self._cursor() as cur:
            for cfg in configs:
                h = _hash(cfg["uri"])
                try:
                    cur.execute(
                        """
                        INSERT INTO configs (hash, uri, protocol, source, first_seen, sent)
                        VALUES (?, ?, ?, ?, ?, 0)
                        """,
                        (h, cfg["uri"], cfg["protocol"], cfg["source"], now),
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    pass   # duplicate — silently skip
        return inserted

    def mark_sent(self, uris: List[str]) -> None:
        """Mark a list of URIs as sent to Telegram."""
        hashes = [_hash(u) for u in uris]
        with self._cursor() as cur:
            cur.executemany(
                "UPDATE configs SET sent = 1 WHERE hash = ?",
                [(h,) for h in hashes],
            )

    def get_unsent(self, limit: int = 50) -> List[dict]:
        """Return up to *limit* configs that have not yet been sent."""
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT uri, protocol, source
                FROM   configs
                WHERE  sent = 0
                ORDER  BY first_seen ASC
                LIMIT  ?
                """,
                (limit,),
            )
            return [
                {"uri": r[0], "protocol": r[1], "source": r[2]}
                for r in cur.fetchall()
            ]

    def stats(self) -> dict:
        """Quick summary for logging."""
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM configs")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM configs WHERE sent = 1")
            sent = cur.fetchone()[0]
        return {"total": total, "sent": sent, "unsent": total - sent}

    # ── async helpers ──────────────────────────────────────────────────────────

    async def async_is_known(self, uri: str) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.is_known, uri)

    async def async_save_configs(self, configs: List[dict]) -> int:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.save_configs, configs)

    async def async_get_unsent(self, limit: int = 50) -> List[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_unsent, limit)

    async def async_mark_sent(self, uris: List[str]) -> None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.mark_sent, uris)

    async def async_get_known_hashes(self) -> Set[str]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_known_hashes)
