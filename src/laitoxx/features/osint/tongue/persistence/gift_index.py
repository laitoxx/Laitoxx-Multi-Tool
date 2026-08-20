"""Persistent exact index for resolved Telegram gifts."""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..domain.chain import KNOWN_GIFT_COLLECTIONS, _account_address


class GiftIndex:
    """Small persistent exact index; repeated investigations do no rescanning."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS gift_items (
                gift_slug TEXT PRIMARY KEY,
                item_address TEXT NOT NULL,
                owner_address TEXT,
                collection_address TEXT,
                collection_name TEXT,
                verified INTEGER,
                item_json TEXT NOT NULL,
                observed_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS gift_collections (
                collection_slug TEXT PRIMARY KEY,
                collection_address TEXT NOT NULL,
                collection_name TEXT,
                observed_at INTEGER NOT NULL
            );
            """
        )
        now = int(time.time())
        for slug, (address, name) in KNOWN_GIFT_COLLECTIONS.items():
            self.conn.execute(
                "INSERT OR IGNORE INTO gift_collections VALUES (?, ?, ?, ?)",
                (slug, address, name, now),
            )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def get_item(self, gift_slug: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM gift_items WHERE gift_slug=?", (gift_slug,)).fetchone()
        if not row:
            return None
        return {
            "item_address": row["item_address"],
            "owner_address": row["owner_address"],
            "collection_address": row["collection_address"],
            "collection_name": row["collection_name"],
            "verified": bool(row["verified"]) if row["verified"] is not None else None,
            "item": json.loads(row["item_json"]),
        }

    def save_item(self, gift_slug: str, item: Mapping[str, Any]) -> None:
        address = _account_address(item.get("address"))
        if not address:
            return
        owner = _account_address(item.get("owner"))
        collection = item.get("collection") if isinstance(item.get("collection"), Mapping) else {}
        collection_address = _account_address(collection)
        collection_name = str(collection.get("name") or "") or None
        self.conn.execute(
            """
            INSERT INTO gift_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(gift_slug) DO UPDATE SET
                item_address=excluded.item_address,
                owner_address=excluded.owner_address,
                collection_address=excluded.collection_address,
                collection_name=excluded.collection_name,
                verified=excluded.verified,
                item_json=excluded.item_json,
                observed_at=excluded.observed_at
            """,
            (
                gift_slug,
                address,
                owner,
                collection_address,
                collection_name,
                int(bool(item.get("verified"))) if item.get("verified") is not None else None,
                json.dumps(dict(item), ensure_ascii=False),
                int(time.time()),
            ),
        )
        collection_slug = gift_slug.rsplit("-", 1)[0]
        if collection_address:
            self.conn.execute(
                """
                INSERT INTO gift_collections VALUES (?, ?, ?, ?)
                ON CONFLICT(collection_slug) DO UPDATE SET
                    collection_address=excluded.collection_address,
                    collection_name=COALESCE(excluded.collection_name, gift_collections.collection_name),
                    observed_at=excluded.observed_at
                """,
                (collection_slug, collection_address, collection_name, int(time.time())),
            )
        self.conn.commit()

    def get_collection(self, collection_slug: str) -> tuple[str, str | None] | None:
        row = self.conn.execute(
            "SELECT collection_address, collection_name FROM gift_collections WHERE collection_slug=?",
            (collection_slug,),
        ).fetchone()
        return (str(row[0]), str(row[1]) if row[1] else None) if row else None
