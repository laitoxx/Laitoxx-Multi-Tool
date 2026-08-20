"""Pure wallet transaction classification and movement parsing."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ..domain.constants import SERVICE_KEYWORDS
from ..domain.models import Movement
from ..domain.primitives import (
    extract_comment,
    flatten_text,
    is_numeric_memo,
    safe_int,
    stable_id,
    ton_amount,
    ts_to_iso,
    tx_succeeded,
)


class WalletAnalysisMixin:
    def classify_counterparty(
        self,
        address: str,
        comment: str,
        address_book: Mapping[str, Any],
    ) -> tuple[str, float, list[str]]:
        evidence: list[str] = []
        known = self.known_labels.get(address)
        if known:
            if isinstance(known, str):
                return known, 1.0, ["local verified label"]
            if isinstance(known, Mapping):
                return (
                    str(known.get("label") or known.get("name") or "known service"),
                    float(known.get("confidence", 1.0)),
                    [str(x) for x in known.get("evidence", ["local label database"])],
                )

        info = address_book.get(address) if isinstance(address_book, Mapping) else None
        info_text = flatten_text(info).lower()
        if info_text:
            evidence.append(f"TON Center address book: {flatten_text(info)[:180]}")
            if any(word in info_text for word in SERVICE_KEYWORDS):
                return "publicly labeled custodial/service address", 0.95, evidence

        if is_numeric_memo(comment):
            evidence.append("numeric memo/tag (weak custodial indicator)")
            return "possible custodial deposit", 0.35, evidence

        return "unclassified counterparty", 0.10, evidence

    def parse_movements(
        self,
        seed: str,
        transactions: Iterable[dict[str, Any]],
        address_book: Mapping[str, Any],
    ) -> list[Movement]:
        movements: list[Movement] = []
        seen: set[str] = set()

        for tx in transactions:
            tx_hash = str(tx.get("hash") or "")
            tx_lt = safe_int(tx.get("lt"))
            trace_id = tx.get("trace_id")
            success = tx_succeeded(tx)
            tx_time = ts_to_iso(tx.get("now"))

            in_msg = tx.get("in_msg") or {}
            if isinstance(in_msg, Mapping):
                src = str(in_msg.get("source") or "")
                dst = str(in_msg.get("destination") or seed)
                value = ton_amount(in_msg.get("value"))
                comment = extract_comment(in_msg)
                msg_hash = str(in_msg.get("hash") or "") or None
                if src and (value > 0 or comment or in_msg.get("opcode") is not None):
                    classification, confidence, evidence = self.classify_counterparty(src, comment, address_book)
                    key = stable_id(tx_hash, msg_hash, "in", src, dst, in_msg.get("created_lt"))
                    if key not in seen:
                        seen.add(key)
                        movements.append(
                            Movement(
                                movement_id=key,
                                direction="in",
                                source=src,
                                destination=dst,
                                amount_ton=value,
                                created_at=ts_to_iso(in_msg.get("created_at")) or tx_time,
                                tx_hash=tx_hash,
                                tx_lt=tx_lt,
                                trace_id=str(trace_id) if trace_id else None,
                                message_hash=msg_hash,
                                opcode=in_msg.get("opcode") if isinstance(in_msg.get("opcode"), int) else None,
                                decoded_opcode=str(in_msg.get("decoded_opcode"))
                                if in_msg.get("decoded_opcode")
                                else None,
                                comment=comment,
                                success=success,
                                classification=classification,
                                confidence=confidence,
                                evidence=evidence,
                            )
                        )

            out_msgs = tx.get("out_msgs") or []
            if isinstance(out_msgs, list):
                for msg in out_msgs:
                    if not isinstance(msg, Mapping):
                        continue
                    src = str(msg.get("source") or seed)
                    dst = str(msg.get("destination") or "")
                    value = ton_amount(msg.get("value"))
                    comment = extract_comment(msg)
                    msg_hash = str(msg.get("hash") or "") or None
                    if not dst or not (value > 0 or comment or msg.get("opcode") is not None):
                        continue
                    classification, confidence, evidence = self.classify_counterparty(dst, comment, address_book)
                    key = stable_id(tx_hash, msg_hash, "out", src, dst, msg.get("created_lt"))
                    if key in seen:
                        continue
                    seen.add(key)
                    movements.append(
                        Movement(
                            movement_id=key,
                            direction="out",
                            source=src,
                            destination=dst,
                            amount_ton=value,
                            created_at=ts_to_iso(msg.get("created_at")) or tx_time,
                            tx_hash=tx_hash,
                            tx_lt=tx_lt,
                            trace_id=str(trace_id) if trace_id else None,
                            message_hash=msg_hash,
                            opcode=msg.get("opcode") if isinstance(msg.get("opcode"), int) else None,
                            decoded_opcode=str(msg.get("decoded_opcode")) if msg.get("decoded_opcode") else None,
                            comment=comment,
                            success=success,
                            classification=classification,
                            confidence=confidence,
                            evidence=evidence,
                        )
                    )

        return movements
