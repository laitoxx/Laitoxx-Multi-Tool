"""Application-facing service for the bundled TONgue investigation engine."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from laitoxx.core.settings.paths import REPORTS_DIR

from .chain_resolver import GiftChainResolver
from .configuration import load_labels
from .domain.chain import GiftChainError, GiftChainResolution
from .domain.gifts import normalize_gift_slug
from .graph_adapter import _merge_primary_evidence
from .integration import _attach_chain_resolution
from .persistence.evidence import EvidenceDB
from .pricing import _enrich_movement_prices
from .provider.public_web import PublicWebClient
from .provider.toncenter import OperationCancelled, TonCenterClient, TonCenterError
from .scanner.gift import GiftCorrelationEngine
from .scanner.wallet import TonScanner
from .telegram_discovery import discover_telegram, discovery_report

ProgressCallback = Callable[[str], None]
CancelCheck = Callable[[], bool]


@dataclass(slots=True)
class TongueOptions:
    target: str
    target_kind: str = "auto"
    api_key: str = ""
    tonapi_key: str = ""
    blockchain_gifts: bool = True
    chain_item_budget: int = 5000
    recursive: bool = True
    max_depth: int = 3
    tx_limit: int = 250
    trace_limit: int = 25
    nft_limit: int = 250
    transfer_limit: int = 250
    history_limit: int = 1000
    wallet_budget: int = 20
    nft_budget: int = 200
    history_budget: int = 3000
    profile_budget: int = 100
    nfts_per_wallet: int = 100
    public_profiles: bool = True
    trace_sales: bool = False
    preserve_raw: bool = False
    wallet_hint: str = ""
    labels_path: str = ""
    output_dir: str = ""
    price_estimates: bool = True


def tongue_tool(_input_data=None) -> str:
    """Registry placeholder; the desktop tool is opened by its input controller."""
    return "TONgue opens in a separate investigation workspace."


def detect_target_kind(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("Enter a Telegram username/link, TON wallet, NFT item, or Telegram Gift link.")
    lowered = value.casefold()
    if "t.me/nft/" in lowered or lowered.startswith("tg://nft"):
        return "gift"
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*-\d+", value):
        return "gift"
    if (
        value.startswith("@")
        or value.isdigit()
        or re.search(r"(?i)(?:https?://)?(?:t\.me|telegram\.me)/(?!nft/)", value)
        or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{3,31}", value)
    ):
        return "telegram"
    return "wallet"


def default_output_dir() -> Path:
    return Path(REPORTS_DIR) / "tongue"


def _emit(callback: ProgressCallback | None, text: str) -> None:
    if callback:
        callback(text)


def run_investigation(
    options: TongueOptions,
    *,
    progress: ProgressCallback | None = None,
    cancelled: CancelCheck | None = None,
) -> dict[str, Any]:
    """Run one bounded investigation and return the structured report."""
    target = options.target.strip()
    kind = detect_target_kind(target) if options.target_kind == "auto" else options.target_kind
    if kind not in {"wallet", "nft", "gift", "telegram"}:
        raise ValueError(f"Unsupported TONgue target type: {kind}")

    cancel_check = cancelled or (lambda: False)
    if cancel_check():
        raise OperationCancelled("TONgue investigation cancelled")

    output_dir = Path(options.output_dir).expanduser() if options.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "evidence.sqlite3"
    raw_dir = output_dir / "raw" if options.preserve_raw else None
    labels = load_labels(options.labels_path or None)

    _emit(progress, "Connecting to public TON sources…")
    client = TonCenterClient(
        api_key=options.api_key.strip() or os.getenv("TONCENTER_API_KEY") or None,
        raw_dir=raw_dir,
        cancel_check=cancel_check,
    )
    public_web = PublicWebClient(
        raw_dir=(output_dir / "raw_public") if options.preserve_raw else None,
        cancel_check=cancel_check,
    )
    db = EvidenceDB(db_path)
    chain_resolver: GiftChainResolver | None = None
    telegram_data: dict[str, Any] | None = None
    try:
        if kind == "telegram":
            _emit(progress, "Searching public Telegram profile and extracting TON pivots…")
            telegram_data = discover_telegram(target, web=public_web, cancelled=cancel_check)
            gifts = telegram_data.get("gift_candidates") or []
            addresses = telegram_data.get("ton_candidates") or []
            if gifts:
                target = str(gifts[0])
                kind = "gift"
                _emit(progress, f"Found Telegram Gift {target}; continuing on TON…")
            elif addresses:
                target = str(addresses[0].get("address") or "")
                kind = "nft" if addresses[0].get("role") == "nft_candidate" else "wallet"
                _emit(progress, "Found a public TON address; continuing on-chain…")
            else:
                report = discovery_report(telegram_data)
                report["tongue"]["database"] = str(db_path)
                _emit(progress, "Telegram discovery complete; no public TON pivot was exposed")
                return report

        scanner = TonScanner(
            client=client,
            db=db,
            output_dir=output_dir,
            tx_limit=max(1, options.tx_limit),
            trace_limit=max(0, options.trace_limit),
            nft_limit=max(0, options.nft_limit),
            transfer_limit=max(0, options.transfer_limit),
            known_labels=labels,
            public_web=public_web,
        )
        engine = GiftCorrelationEngine(scanner)

        if options.target_kind == "auto" and kind == "wallet":
            # TON wallet and NFT item addresses share the same address syntax.
            # Probe the public NFT index so "auto" is semantic, not only regex-based.
            try:
                identity = scanner.normalize_address(target)
                indexed_item, _ = scanner.get_nft_item(identity.raw)
                if indexed_item:
                    kind = "nft"
            except TonCenterError:
                # The selected branch will produce the canonical validation error.
                pass

        _emit(progress, f"Resolving {kind} target…")
        if kind == "gift":
            chain_resolution = None
            if options.blockchain_gifts and scanner.gift_resolver:
                _emit(progress, "Checking whether the gift was exported to TON...")
                gift_identity = engine.resolve_gift(target, public_profiles=options.public_profiles)
                chain_resolver = GiftChainResolver(
                    output_dir / "gift_chain_index.sqlite3",
                    api_key=options.tonapi_key.strip() or os.getenv("TONAPI_KEY") or None,
                    cancel_check=cancel_check,
                )
                try:
                    chain_resolution = chain_resolver.resolve(
                        gift_identity,
                        item_budget=max(1, options.chain_item_budget),
                    )
                except GiftChainError as exc:
                    chain_resolution = GiftChainResolution(
                        gift_slug=gift_identity.slug,
                        status="source_error",
                        message=f"Public blockchain lookup failed: {exc}",
                        metadata_url=(f"https://nft.fragment.com/gift/{gift_identity.slug}.json"),
                        evidence=["Telegram page was parsed; blockchain source failed"],
                        sources=[{"name": "Public TON cascade", "status": "error"}],
                    )
                if chain_resolution.item_address:
                    gift_identity.ton_address_candidates.insert(
                        0,
                        {
                            "address": chain_resolution.item_address,
                            "role": "nft_candidate",
                            "source": "TonAPI/Fragment on-chain resolution",
                        },
                    )
                    gift_identity.evidence.extend(
                        row for row in chain_resolution.evidence if row not in gift_identity.evidence
                    )
            base = engine.investigate_gift(
                target,
                wallet_hint=options.wallet_hint.strip() or None,
                history_limit=max(1, options.history_limit),
                public_profiles=options.public_profiles,
                trace_sales=options.trace_sales,
            )
            if chain_resolution:
                _attach_chain_resolution(base, chain_resolution)
            seed_id = normalize_gift_slug(target)
        elif kind == "nft":
            base = engine.investigate_nft(
                target,
                history_limit=max(1, options.history_limit),
                public_profiles=options.public_profiles,
                trace_sales=options.trace_sales,
            )
            seed_id = scanner.normalize_address(target).raw
        else:
            base = scanner.scan(target)
            seed_id = str((base.get("summary") or {}).get("seed_raw") or target)
            _emit(progress, "Classifying Telegram collectibles and historical ownership…")
            engine.enrich_wallet_collectibles(
                base,
                public_profiles=options.public_profiles,
                collectible_budget=min(100, max(10, options.nft_limit)),
                # Public Telegram pages are verified individually.  Keep this
                # cascade bounded so one wallet with many NFTs cannot stall UI.
                public_profile_budget=min(12, max(0, options.profile_budget)),
            )

        if options.price_estimates and base.get("movements"):
            _emit(progress, "Estimating historical TON/USD values…")
            _enrich_movement_prices(base)

        if cancel_check():
            raise OperationCancelled("TONgue investigation cancelled")

        if options.recursive:
            _emit(progress, "Expanding evidence graph…")
            report = engine.recursive_explore(
                kind,
                seed_id,
                max_depth=max(0, options.max_depth),
                wallet_budget=max(1, options.wallet_budget),
                nft_budget=max(1, options.nft_budget),
                history_budget=max(0, options.history_budget),
                profile_budget=max(0, options.profile_budget),
                nfts_per_wallet=max(1, options.nfts_per_wallet),
                public_profiles=options.public_profiles,
                trace_sales=options.trace_sales,
                wallet_hint=options.wallet_hint.strip() or None,
            )
            report["primary_investigation"] = base
            _merge_primary_evidence(report, base)
            if kind == "gift" and chain_resolution:
                _attach_chain_resolution(report, chain_resolution)
            artifacts = engine.export(report)
            report["artifacts"] = {name: str(path) for name, path in artifacts.items()}
        else:
            report = base
            if kind in {"gift", "nft"}:
                artifacts = engine.export(report)
                report["artifacts"] = {name: str(path) for name, path in artifacts.items()}

        report["tongue"] = {
            "target_kind": kind,
            "recursive": options.recursive,
            "database": str(db_path),
            "public_only": True,
            "blockchain_gift_lookup": bool(options.blockchain_gifts),
        }
        if telegram_data:
            telegram_report = discovery_report(telegram_data)
            report["telegram_discovery"] = telegram_data
            report["summary"] = {
                **(report.get("summary") or {}),
                "telegram_seed": (telegram_data.get("profile") or {}).get("username"),
                "telegram_gift_candidates": len(telegram_data.get("gift_candidates") or []),
                "telegram_ton_candidates": len(telegram_data.get("ton_candidates") or []),
            }
            graph = report.setdefault("graph", {"nodes": [], "edges": []})
            known_nodes = {str(row.get("id")) for row in graph.get("nodes") or []}
            for node in (telegram_report.get("graph") or {}).get("nodes") or []:
                if str(node.get("id")) not in known_nodes:
                    graph.setdefault("nodes", []).append(node)
                    known_nodes.add(str(node.get("id")))
            graph.setdefault("edges", []).extend((telegram_report.get("graph") or {}).get("edges") or [])
        _emit(progress, "Investigation complete")
        return report
    finally:
        db.close()
        if chain_resolver:
            chain_resolver.close()
        public_web.close()
        client.close()
