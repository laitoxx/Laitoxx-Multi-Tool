"""Persist NFT chronology and discovery graph edges."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from ..domain.models import NftHistoryEvent
from ..domain.primitives import jsonable, safe_int, stable_id, utc_now_iso


class HistoryEvidenceMixin:
    def save_nft_history_events(self, events: Iterable[NftHistoryEvent]) -> int:
        inserted = 0
        for event in events:
            cur = self.conn.execute(
                """
                INSERT OR REPLACE INTO nft_history_events(
                    id, nft_address, event_type, old_owner, new_owner,
                    transaction_lt, transaction_time, transaction_hash, trace_id,
                    success, price_ton, confidence, evidence_json, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.nft_address,
                    event.event_type,
                    event.old_owner,
                    event.new_owner,
                    event.transaction_lt,
                    event.transaction_time,
                    event.transaction_hash,
                    event.trace_id,
                    int(event.success),
                    event.price_ton,
                    event.confidence,
                    json.dumps(event.evidence, ensure_ascii=False),
                    utc_now_iso(),
                ),
            )
            inserted += cur.rowcount
        self.conn.commit()
        return inserted

    def save_discovery_edges(self, edges: Iterable[Mapping[str, Any]]) -> int:
        inserted = 0
        for edge in edges:
            key = stable_id(edge.get("source"), edge.get("target"), edge.get("relation"), edge.get("depth"))
            cur = self.conn.execute(
                """
                INSERT OR REPLACE INTO discovery_edges(
                    id, source_id, target_id, relation, confidence,
                    evidence_json, depth, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    edge.get("source"),
                    edge.get("target"),
                    edge.get("relation"),
                    float(edge.get("confidence") or 0),
                    json.dumps(jsonable(edge.get("evidence") or []), ensure_ascii=False),
                    safe_int(edge.get("depth")),
                    utc_now_iso(),
                ),
            )
            inserted += cur.rowcount
        self.conn.commit()
        return inserted
