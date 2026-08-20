"""SQLite evidence repository for incremental TON investigations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .gift_evidence import GiftEvidenceMixin
from .history_evidence import HistoryEvidenceMixin
from .wallet_evidence import WalletEvidenceMixin


class EvidenceDB(WalletEvidenceMixin, GiftEvidenceMixin, HistoryEvidenceMixin):
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                mode TEXT NOT NULL,
                summary_json TEXT
            );
            CREATE TABLE IF NOT EXISTS checkpoints (
                address TEXT PRIMARY KEY,
                last_lt INTEGER NOT NULL DEFAULT 0,
                last_utime INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS movements (
                movement_id TEXT PRIMARY KEY,
                address TEXT NOT NULL,
                direction TEXT NOT NULL,
                source TEXT,
                destination TEXT,
                amount_ton REAL,
                created_at TEXT,
                tx_hash TEXT,
                tx_lt INTEGER,
                trace_id TEXT,
                message_hash TEXT,
                opcode INTEGER,
                decoded_opcode TEXT,
                comment TEXT,
                success INTEGER,
                classification TEXT,
                confidence REAL,
                evidence_json TEXT,
                observed_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_movements_address_lt ON movements(address, tx_lt);
            CREATE TABLE IF NOT EXISTS nft_transfers (
                id TEXT PRIMARY KEY,
                address TEXT NOT NULL,
                direction TEXT,
                nft_address TEXT,
                collection_address TEXT,
                old_owner TEXT,
                new_owner TEXT,
                tx_hash TEXT,
                tx_lt INTEGER,
                tx_time TEXT,
                payload_json TEXT,
                observed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jetton_transfers (
                id TEXT PRIMARY KEY,
                address TEXT NOT NULL,
                direction TEXT,
                jetton_master TEXT,
                source TEXT,
                destination TEXT,
                amount TEXT,
                tx_hash TEXT,
                tx_lt INTEGER,
                tx_time TEXT,
                payload_json TEXT,
                observed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS gifts (
                slug TEXT PRIMARY KEY,
                title TEXT,
                gift_number INTEGER,
                collection_slug TEXT,
                public_profiles_json TEXT,
                ton_candidates_json TEXT,
                payload_json TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS gift_resolutions (
                id TEXT PRIMARY KEY,
                gift_slug TEXT NOT NULL,
                nft_address TEXT,
                ton_owner TEXT,
                telegram_profile TEXT,
                relation TEXT NOT NULL,
                confidence REAL NOT NULL,
                source TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                observed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS collectible_identity_observations (
                id TEXT PRIMARY KEY,
                collectible_id TEXT NOT NULL,
                collectible_kind TEXT NOT NULL,
                nft_address TEXT,
                chain_owner TEXT,
                public_identity TEXT NOT NULL,
                source TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                valid_to TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_collectible_identity_open
                ON collectible_identity_observations(collectible_id, valid_to, last_seen);
            CREATE TABLE IF NOT EXISTS nft_history_events (
                id TEXT PRIMARY KEY,
                nft_address TEXT NOT NULL,
                event_type TEXT NOT NULL,
                old_owner TEXT,
                new_owner TEXT,
                transaction_lt INTEGER,
                transaction_time TEXT,
                transaction_hash TEXT,
                trace_id TEXT,
                success INTEGER NOT NULL,
                price_ton REAL,
                confidence REAL NOT NULL,
                evidence_json TEXT NOT NULL,
                observed_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_nft_history_item_lt
                ON nft_history_events(nft_address, transaction_lt);
            CREATE TABLE IF NOT EXISTS discovery_edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence_json TEXT NOT NULL,
                depth INTEGER NOT NULL,
                observed_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()


# ---------------------------------------------------------------------------
# Scanning and correlation
# ---------------------------------------------------------------------------
