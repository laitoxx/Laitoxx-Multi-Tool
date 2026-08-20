"""Assemble normalized wallet scan reports."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from ..domain.analysis import address_label, get_token_info, summarize_traces
from ..domain.constants import GIFT_KEYWORDS
from ..domain.models import AddressIdentity, Movement
from ..domain.primitives import flatten_text, jsonable, ton_amount, ts_to_iso, utc_now_iso
from ..reporting.graph import build_graph


class WalletReportMixin:
    def build_report(
        self,
        *,
        identity: AddressIdentity,
        state: Mapping[str, Any],
        transactions: list[dict[str, Any]],
        traces: list[dict[str, Any]],
        movements: list[Movement],
        nft_items: list[dict[str, Any]],
        nft_transfers: list[dict[str, Any]],
        jetton_transfers: list[dict[str, Any]],
        address_book: Mapping[str, Any],
        metadata: Mapping[str, Any],
        incremental: bool,
        start_lt: int,
        auto_selection: Mapping[str, Any] | None,
        inserted_counts: Mapping[str, int],
    ) -> dict[str, Any]:
        gift_candidates = []
        normalized_nfts = []
        for item in nft_items:
            nft_addr = str(item.get("address") or "")
            collection_addr = str(item.get("collection_address") or "")
            token_info = get_token_info(metadata, nft_addr)
            collection_info = get_token_info(metadata, collection_addr)
            text = " ".join(
                [
                    flatten_text(item.get("content")),
                    flatten_text(item.get("collection")),
                    flatten_text(token_info),
                    flatten_text(collection_info),
                ]
            ).lower()
            gift_hits = [word for word in GIFT_KEYWORDS if word in text]
            possible_gift = bool(gift_hits)
            row = {
                **item,
                "token_info": token_info,
                "collection_token_info": collection_info,
                "possible_telegram_collectible": possible_gift,
                "gift_confidence": 0.55 if len(gift_hits) >= 2 else (0.35 if gift_hits else 0.0),
                "gift_evidence": gift_hits,
            }
            normalized_nfts.append(row)
            if possible_gift:
                gift_candidates.append(row)

        counterparties: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "incoming_count": 0,
                "outgoing_count": 0,
                "incoming_ton": 0.0,
                "outgoing_ton": 0.0,
                "comments": [],
                "classifications": Counter(),
                "max_confidence": 0.0,
            }
        )
        seed = identity.raw
        for mv in movements:
            cp = mv.source if mv.direction == "in" else mv.destination
            row = counterparties[cp]
            if mv.direction == "in":
                row["incoming_count"] += 1
                row["incoming_ton"] += mv.amount_ton
            else:
                row["outgoing_count"] += 1
                row["outgoing_ton"] += mv.amount_ton
            if mv.comment:
                row["comments"].append(mv.comment)
            row["classifications"][mv.classification] += 1
            row["max_confidence"] = max(row["max_confidence"], mv.confidence)

        cp_rows = []
        for address, row in counterparties.items():
            info = address_book.get(address) if isinstance(address_book, Mapping) else None
            label = address_label(address, address_book, self.known_labels)
            total_count = row["incoming_count"] + row["outgoing_count"]
            # Interaction-frequency heuristic is reported separately, never promoted to verified identity.
            service_like_score = min(0.55, 0.15 + math.log1p(total_count) / 10) if total_count >= 10 else 0.0
            cp_rows.append(
                {
                    "address": address,
                    "label": label,
                    "address_book": info,
                    "incoming_count": row["incoming_count"],
                    "outgoing_count": row["outgoing_count"],
                    "incoming_ton": round(row["incoming_ton"], 9),
                    "outgoing_ton": round(row["outgoing_ton"], 9),
                    "comments": list(dict.fromkeys(row["comments"]))[:20],
                    "classification": row["classifications"].most_common(1)[0][0]
                    if row["classifications"]
                    else "unclassified",
                    "classification_confidence": row["max_confidence"],
                    "service_like_score": service_like_score,
                }
            )
        cp_rows.sort(key=lambda x: x["incoming_ton"] + x["outgoing_ton"], reverse=True)

        trace_summary = summarize_traces(traces)
        graph = build_graph(
            seed=seed,
            movements=movements,
            nft_items=normalized_nfts,
            nft_transfers=nft_transfers,
            jetton_transfers=jetton_transfers,
            address_book=address_book,
            known_labels=self.known_labels,
        )

        wallet_state = state.get("wallet") or {}
        account_state = state.get("account") or {}
        transaction_times = sorted(
            timestamp for timestamp in (ts_to_iso(tx.get("now")) for tx in transactions) if timestamp
        )
        summary = {
            "generated_at": utc_now_iso(),
            "mode": "incremental" if incremental else "snapshot",
            "seed_raw": seed,
            "seed_bounceable": identity.bounceable,
            "seed_non_bounceable": identity.non_bounceable,
            "wallet_type": wallet_state.get("wallet_type"),
            "is_wallet": wallet_state.get("is_wallet"),
            "status": wallet_state.get("status") or account_state.get("status"),
            "balance_ton": ton_amount(wallet_state.get("balance") or account_state.get("balance")),
            "transactions_loaded": len(transactions),
            "history_newest": transaction_times[-1] if transaction_times else None,
            "history_oldest": transaction_times[0] if transaction_times else None,
            # A full page at the configured budget means older records may exist.
            "history_truncated": len(transactions) >= self.tx_limit,
            "history_anchor_loaded": bool(getattr(self, "_history_anchor_loaded", False)),
            "movements_parsed": len(movements),
            "counterparties": len(cp_rows),
            "traces_loaded": len(traces),
            "nft_items": len(normalized_nfts),
            "possible_telegram_collectibles": len(gift_candidates),
            "nft_transfers": len(nft_transfers),
            "jetton_transfers": len(jetton_transfers),
            "start_lt": start_lt,
            "inserted": dict(inserted_counts),
        }

        return {
            "summary": summary,
            "identity": asdict(identity),
            "auto_selection": jsonable(auto_selection),
            "state": jsonable(state),
            "transactions": jsonable(transactions),
            "movements": [asdict(x) for x in movements],
            "counterparties": jsonable(cp_rows),
            "traces": jsonable(traces),
            "trace_summary": jsonable(trace_summary),
            "nft_items": jsonable(normalized_nfts),
            "gift_candidates": jsonable(gift_candidates),
            "nft_transfers": jsonable(nft_transfers),
            "jetton_transfers": jsonable(jetton_transfers),
            "address_book": jsonable(address_book),
            "metadata": jsonable(metadata),
            "graph": graph,
        }
