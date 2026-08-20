"""Wallet-centric TON scanner orchestration."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..domain.primitives import (
    jsonable,
    safe_int,
)
from ..persistence.evidence import EvidenceDB
from ..provider.public_gift import PublicGiftResolver
from ..provider.public_web import PublicWebClient
from ..provider.toncenter import TonCenterClient
from ..reporting.export import write_csv
from ..reporting.wallet import render_html_report, render_mermaid
from .wallet_analysis import WalletAnalysisMixin
from .wallet_data import WalletDataMixin
from .wallet_report import WalletReportMixin


class TonScanner(WalletDataMixin, WalletAnalysisMixin, WalletReportMixin):
    def __init__(
        self,
        client: TonCenterClient,
        db: EvidenceDB,
        output_dir: Path,
        tx_limit: int = 250,
        trace_limit: int = 25,
        nft_limit: int = 250,
        transfer_limit: int = 250,
        known_labels: Mapping[str, Any] | None = None,
        public_web: PublicWebClient | None = None,
    ) -> None:
        self.client = client
        self.db = db
        self.output_dir = output_dir
        self.tx_limit = tx_limit
        self.trace_limit = trace_limit
        self.nft_limit = nft_limit
        self.transfer_limit = transfer_limit
        self.known_labels = dict(known_labels or {})
        self.public_web = public_web
        self.gift_resolver = PublicGiftResolver(public_web) if public_web else None
        self._nft_item_cache: dict[str, tuple[dict[str, Any] | None, dict[str, Any]]] = {}
        self._wallet_nft_cache: dict[str, tuple[list[dict[str, Any]], dict[str, Any]]] = {}
        self._nft_history_cache: dict[str, tuple[list[dict[str, Any]], dict[str, Any]]] = {}

    def scan(
        self,
        target: str,
        incremental: bool = False,
        auto_selection: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        identity = self.normalize_address(target)
        seed = identity.raw
        checkpoint_lt, checkpoint_utime = self.db.get_checkpoint(seed)
        start_lt = checkpoint_lt + 1 if incremental and checkpoint_lt > 0 else 0
        scan_id = self.db.begin_scan(seed, "incremental" if incremental else "snapshot")

        state = self.get_state(seed)
        transactions, tx_context = self.get_transactions(seed, start_lt=start_lt)
        traces, trace_context = self.get_traces(seed, start_lt=start_lt)
        nft_items, nft_context = self.get_nfts(seed)
        nft_transfers, nft_transfer_context = self.get_nft_transfers(seed, start_lt=start_lt)
        jetton_transfers, jetton_context = self.get_jetton_transfers(seed, start_lt=start_lt)

        address_book: dict[str, Any] = {}
        metadata: dict[str, Any] = {}
        for context in (
            state,
            tx_context,
            trace_context,
            nft_context,
            nft_transfer_context,
            jetton_context,
        ):
            if isinstance(context, Mapping):
                address_book.update(context.get("address_book") or {})
                metadata.update(context.get("metadata") or {})

        movements = self.parse_movements(seed, transactions, address_book)
        new_movements = self.db.save_movements(seed, movements)
        new_nft_transfers = self.db.save_nft_transfers(seed, nft_transfers)
        new_jetton_transfers = self.db.save_jetton_transfers(seed, jetton_transfers)

        max_lt = max([checkpoint_lt] + [safe_int(tx.get("lt")) for tx in transactions])
        max_utime = max([checkpoint_utime] + [safe_int(tx.get("now")) for tx in transactions])
        if max_lt > checkpoint_lt:
            self.db.set_checkpoint(seed, max_lt, max_utime)

        report = self.build_report(
            identity=identity,
            state=state,
            transactions=transactions,
            traces=traces,
            movements=movements,
            nft_items=nft_items,
            nft_transfers=nft_transfers,
            jetton_transfers=jetton_transfers,
            address_book=address_book,
            metadata=metadata,
            incremental=incremental,
            start_lt=start_lt,
            auto_selection=auto_selection,
            inserted_counts={
                "movements": new_movements,
                "nft_transfers": new_nft_transfers,
                "jetton_transfers": new_jetton_transfers,
            },
        )
        paths = self.export_report(report)
        report["artifacts"] = {k: str(v) for k, v in paths.items()}
        self.db.finish_scan(scan_id, report.get("summary") or {})
        return report

    def export_report(self, report: Mapping[str, Any]) -> dict[str, Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        seed = str((report.get("summary") or {}).get("seed_raw") or "wallet")
        slug = re.sub(r"[^a-zA-Z0-9_-]", "_", seed)[:32]
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        prefix = self.output_dir / f"ton_scan_{slug}_{stamp}"

        json_path = prefix.with_suffix(".json")
        html_path = prefix.with_suffix(".html")
        mermaid_path = prefix.with_suffix(".mmd")
        movement_csv = prefix.with_name(prefix.name + "_movements.csv")
        counterparties_csv = prefix.with_name(prefix.name + "_counterparties.csv")
        nfts_csv = prefix.with_name(prefix.name + "_nfts.csv")

        json_path.write_text(json.dumps(jsonable(report), ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(render_html_report(report), encoding="utf-8")
        mermaid_path.write_text(render_mermaid(report.get("graph") or {}), encoding="utf-8")
        write_csv(movement_csv, report.get("movements") or [])
        write_csv(counterparties_csv, report.get("counterparties") or [])
        write_csv(nfts_csv, report.get("nft_items") or [])

        return {
            "json": json_path,
            "html": html_path,
            "mermaid": mermaid_path,
            "movements_csv": movement_csv,
            "counterparties_csv": counterparties_csv,
            "nfts_csv": nfts_csv,
        }


# ---------------------------------------------------------------------------
# Gift/NFT correlation and recursive discovery
# ---------------------------------------------------------------------------
