"""Persist wallet scan state and transfer observations."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from ..domain.models import Movement
from ..domain.primitives import jsonable, safe_int, stable_id, ts_to_iso, utc_now_iso


class WalletEvidenceMixin:
    def begin_scan(self, target: str, mode: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO scans(target, started_at, mode) VALUES (?, ?, ?)",
            (target, utc_now_iso(), mode),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def finish_scan(self, scan_id: int, summary: Mapping[str, Any]) -> None:
        self.conn.execute(
            "UPDATE scans SET finished_at=?, summary_json=? WHERE id=?",
            (utc_now_iso(), json.dumps(jsonable(summary), ensure_ascii=False), scan_id),
        )
        self.conn.commit()

    def get_checkpoint(self, address: str) -> tuple[int, int]:
        row = self.conn.execute("SELECT last_lt, last_utime FROM checkpoints WHERE address=?", (address,)).fetchone()
        if not row:
            return 0, 0
        return int(row["last_lt"]), int(row["last_utime"])

    def set_checkpoint(self, address: str, last_lt: int, last_utime: int) -> None:
        self.conn.execute(
            """
            INSERT INTO checkpoints(address, last_lt, last_utime, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                last_lt=MAX(checkpoints.last_lt, excluded.last_lt),
                last_utime=MAX(checkpoints.last_utime, excluded.last_utime),
                updated_at=excluded.updated_at
            """,
            (address, last_lt, last_utime, utc_now_iso()),
        )
        self.conn.commit()

    def save_movements(self, address: str, movements: Iterable[Movement]) -> int:
        inserted = 0
        for mv in movements:
            cur = self.conn.execute(
                """
                INSERT OR IGNORE INTO movements(
                    movement_id, address, direction, source, destination, amount_ton,
                    created_at, tx_hash, tx_lt, trace_id, message_hash, opcode,
                    decoded_opcode, comment, success, classification, confidence,
                    evidence_json, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mv.movement_id,
                    address,
                    mv.direction,
                    mv.source,
                    mv.destination,
                    mv.amount_ton,
                    mv.created_at,
                    mv.tx_hash,
                    mv.tx_lt,
                    mv.trace_id,
                    mv.message_hash,
                    mv.opcode,
                    mv.decoded_opcode,
                    mv.comment,
                    int(mv.success),
                    mv.classification,
                    mv.confidence,
                    json.dumps(mv.evidence, ensure_ascii=False),
                    utc_now_iso(),
                ),
            )
            inserted += cur.rowcount
        self.conn.commit()
        return inserted

    def save_nft_transfers(self, address: str, rows: Iterable[dict[str, Any]]) -> int:
        inserted = 0
        for row in rows:
            key = stable_id(row.get("transaction_hash"), row.get("nft_address"), row.get("direction"))
            cur = self.conn.execute(
                """
                INSERT OR IGNORE INTO nft_transfers(
                    id, address, direction, nft_address, collection_address,
                    old_owner, new_owner, tx_hash, tx_lt, tx_time,
                    payload_json, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    address,
                    row.get("direction"),
                    row.get("nft_address"),
                    row.get("nft_collection"),
                    row.get("old_owner"),
                    row.get("new_owner"),
                    row.get("transaction_hash"),
                    safe_int(row.get("transaction_lt")),
                    ts_to_iso(row.get("transaction_now")),
                    json.dumps(jsonable(row), ensure_ascii=False),
                    utc_now_iso(),
                ),
            )
            inserted += cur.rowcount
        self.conn.commit()
        return inserted

    def save_jetton_transfers(self, address: str, rows: Iterable[dict[str, Any]]) -> int:
        inserted = 0
        for row in rows:
            key = stable_id(
                row.get("transaction_hash"),
                row.get("jetton_master"),
                row.get("direction"),
                row.get("source"),
                row.get("destination"),
                row.get("amount"),
            )
            cur = self.conn.execute(
                """
                INSERT OR IGNORE INTO jetton_transfers(
                    id, address, direction, jetton_master, source, destination,
                    amount, tx_hash, tx_lt, tx_time, payload_json, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    address,
                    row.get("direction"),
                    row.get("jetton_master"),
                    row.get("source"),
                    row.get("destination"),
                    row.get("amount"),
                    row.get("transaction_hash"),
                    safe_int(row.get("transaction_lt")),
                    ts_to_iso(row.get("transaction_now")),
                    json.dumps(jsonable(row), ensure_ascii=False),
                    utc_now_iso(),
                ),
            )
            inserted += cur.rowcount
        self.conn.commit()
        return inserted
