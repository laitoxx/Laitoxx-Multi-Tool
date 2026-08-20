"""Gift/NFT investigation orchestration."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..domain.models import GiftIdentity
from ..domain.primitives import jsonable
from ..reporting.export import write_csv
from ..reporting.investigation import render_investigation_html, render_investigation_mermaid
from .gift_enrichment import GiftEnrichmentMixin
from .gift_investigation import GiftInvestigationMixin
from .gift_public import GiftPublicMixin
from .gift_recursive import GiftRecursiveMixin
from .wallet import TonScanner


class GiftCorrelationEngine(
    GiftPublicMixin,
    GiftEnrichmentMixin,
    GiftInvestigationMixin,
    GiftRecursiveMixin,
):
    def __init__(self, scanner: TonScanner) -> None:
        self.scanner = scanner
        self.db = scanner.db
        self.resolver = scanner.gift_resolver
        self._wallet_cache: dict[str, tuple[list[dict[str, Any]], dict[str, Any]]] = {}
        self._gift_cache: dict[str, GiftIdentity] = {}

    def export(self, report: Mapping[str, Any]) -> dict[str, Path]:
        self.scanner.output_dir.mkdir(parents=True, exist_ok=True)
        seed = report.get("seed")
        if isinstance(seed, Mapping):
            seed_text = f"{seed.get('type')}_{seed.get('id')}"
        else:
            seed_text = str(seed or "investigation")
        slug = re.sub(r"[^A-Za-z0-9_-]", "_", seed_text)[:48]
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        prefix = self.scanner.output_dir / f"ton_gift_{slug}_{stamp}"
        json_path = prefix.with_suffix(".json")
        html_path = prefix.with_suffix(".html")
        mmd_path = prefix.with_suffix(".mmd")
        timeline_path = prefix.with_name(prefix.name + "_timeline.csv")
        json_path.write_text(json.dumps(jsonable(report), ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(render_investigation_html(report), encoding="utf-8")
        mmd_path.write_text(render_investigation_mermaid(report.get("graph") or {}), encoding="utf-8")
        timeline_rows: list[Mapping[str, Any]] = []
        if report.get("history"):
            timeline_rows.extend(report.get("history") or [])
        if report.get("nft_report") and isinstance(report.get("nft_report"), Mapping):
            timeline_rows.extend((report.get("nft_report") or {}).get("history") or [])
        for nft_address, rows in (report.get("timelines") or {}).items():
            for row in rows:
                timeline_rows.append({"timeline_nft": nft_address, **row})
        write_csv(timeline_path, timeline_rows)
        return {"json": json_path, "html": html_path, "mermaid": mmd_path, "timeline_csv": timeline_path}
