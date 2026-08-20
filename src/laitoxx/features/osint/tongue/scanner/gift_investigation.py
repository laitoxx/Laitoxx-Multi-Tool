"""Bounded gift and NFT investigation behavior."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..domain.models import GiftIdentity, NftGiftMatch
from ..domain.nft import (
    classify_nft_history,
    gift_identity_from_nft,
    score_gift_nft,
)
from ..domain.nft_metadata import nft_custody_owner, nft_effective_owner
from ..domain.primitives import jsonable, utc_now_iso
from ..provider.toncenter import TonCenterError


class GiftInvestigationMixin:
    def match_gift_on_wallet(self, gift: GiftIdentity, wallet: str, max_items: int = 500) -> list[NftGiftMatch]:
        identity = self.scanner.normalize_address(wallet)
        items, context = self._wallet_nfts(identity.raw, max_items)
        matches = [score_gift_nft(gift, item, context, owner_hint=identity.raw) for item in items]
        return sorted((m for m in matches if m.confidence >= 0.35), key=lambda m: m.confidence, reverse=True)

    def validate_public_candidates(self, gift: GiftIdentity) -> tuple[list[NftGiftMatch], list[str]]:
        matches: list[NftGiftMatch] = []
        wallets: list[str] = []
        seen: set[str] = set()
        for candidate in gift.ton_address_candidates[:20]:
            address = str(candidate.get("address") or "")
            if not address or address in seen:
                continue
            seen.add(address)
            try:
                item, context = self.scanner.get_nft_item(address)
            except TonCenterError:
                continue
            if item:
                match = score_gift_nft(gift, item, context)
                if match.confidence < 0.75:
                    # The page explicitly linked this address; item contract validation is strong evidence.
                    match.confidence = max(match.confidence, 0.78)
                    match.status = "MATCH_STRONG"
                    match.evidence.append("public page address resolves to an NFT item contract")
                matches.append(match)
            else:
                try:
                    identity = self.scanner.normalize_address(address)
                except TonCenterError:
                    continue
                wallets.append(identity.raw)
        return matches, list(dict.fromkeys(wallets))

    def investigate_nft(
        self,
        nft_address: str,
        history_limit: int = 1000,
        public_profiles: bool = True,
        trace_sales: bool = False,
    ) -> dict[str, Any]:
        identity = self.scanner.normalize_address(nft_address)
        item, context = self.scanner.get_nft_item(identity.raw)
        if not item:
            raise TonCenterError(f"Address is not indexed as an NFT item: {nft_address}")
        gift, gift_confidence, gift_evidence = gift_identity_from_nft(item, context)
        public_gift = None
        if gift:
            public_gift = self._resolve_gift(gift.slug, public_profiles=public_profiles)
            self.db.save_gift_resolution(
                gift.slug,
                "NFT_METADATA_IDENTIFIES_GIFT",
                gift_confidence,
                "TON NFT metadata",
                gift_evidence,
                nft_address=identity.raw,
                ton_owner=nft_effective_owner(item),
            )
        rows, history_context = self.scanner.get_nft_history(identity.raw, history_limit)
        events = classify_nft_history(
            identity.raw,
            rows,
            trace_lookup=self.scanner.get_trace_by_id if trace_sales else None,
        )
        self.db.save_nft_history_events(events)
        report = {
            "kind": "nft_investigation",
            "generated_at": utc_now_iso(),
            "seed": identity.raw,
            "identity": asdict(identity),
            "nft_item": jsonable(item),
            "nft_context": jsonable(context),
            "gift_from_metadata": jsonable(asdict(gift)) if gift else None,
            "public_gift": jsonable(asdict(public_gift)) if public_gift else None,
            "history": [asdict(x) for x in events],
            "history_raw": jsonable(rows),
            "history_context": jsonable(history_context),
        }
        report["graph"] = self._graph_for_nft_report(report)
        report["summary"] = {
            "kind": report["kind"],
            "seed": identity.raw,
            "gift_slug": gift.slug if gift else None,
            "current_owner": nft_effective_owner(item),
            "custody_owner": nft_custody_owner(item),
            "history_events": len(events),
            "first_event": events[0].transaction_time if events else None,
            "last_event": events[-1].transaction_time if events else None,
            "public_profiles": public_gift.public_profiles if public_gift else [],
        }
        return report

    def investigate_gift(
        self,
        gift_input: str,
        wallet_hint: str | None = None,
        history_limit: int = 1000,
        public_profiles: bool = True,
        trace_sales: bool = False,
    ) -> dict[str, Any]:
        gift = self._resolve_gift(gift_input, public_profiles=public_profiles)
        matches, candidate_wallets = self.validate_public_candidates(gift)
        if wallet_hint:
            matches.extend(self.match_gift_on_wallet(gift, wallet_hint, max_items=max(self.scanner.nft_limit, 500)))
        for wallet in candidate_wallets[:5]:
            try:
                matches.extend(self.match_gift_on_wallet(gift, wallet, max_items=max(self.scanner.nft_limit, 500)))
            except TonCenterError:
                continue
        by_nft: dict[str, NftGiftMatch] = {}
        for match in matches:
            current = by_nft.get(match.nft_address)
            if current is None or match.confidence > current.confidence:
                by_nft[match.nft_address] = match
        matches = sorted(by_nft.values(), key=lambda x: x.confidence, reverse=True)
        nft_report = None
        if matches and matches[0].confidence >= 0.55:
            nft_report = self.investigate_nft(
                matches[0].nft_address,
                history_limit=history_limit,
                public_profiles=public_profiles,
                trace_sales=trace_sales,
            )
            best = matches[0]
            self.db.save_gift_resolution(
                gift.slug,
                "MATCHED_TO_NFT_ITEM",
                best.confidence,
                "public bridge + TON metadata",
                best.evidence,
                nft_address=best.nft_address,
                ton_owner=best.owner_address,
            )
        report = {
            "kind": "gift_investigation",
            "generated_at": utc_now_iso(),
            "seed": gift.slug,
            "gift": asdict(gift),
            "wallet_hint": wallet_hint,
            "candidate_wallets": candidate_wallets,
            "matches": [asdict(x) for x in matches],
            "nft_report": nft_report,
        }
        report["graph"] = self._graph_for_gift_report(report)
        report["summary"] = {
            "kind": report["kind"],
            "seed": gift.slug,
            "title": gift.title,
            "public_profiles": gift.public_profiles,
            "ton_candidates": len(gift.ton_address_candidates),
            "nft_matches": len(matches),
            "best_match": matches[0].nft_address if matches else None,
            "best_confidence": matches[0].confidence if matches else 0.0,
            "history_events": len((nft_report or {}).get("history") or []),
        }
        return report
