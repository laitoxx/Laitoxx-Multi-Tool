"""NFT and Telegram collectible correlation rules."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict
from typing import Any

from ..provider.toncenter import TonCenterError
from .constants import GIFT_KEYWORDS
from .gifts import PUBLIC_PROFILE_EXCLUDES, normalize_name, parse_title_number, split_slug
from .models import GiftIdentity, NftGiftMatch, NftHistoryEvent
from .nft_metadata import (
    exact_gift_slug_from_metadata,
    iter_key_values,
    nft_effective_owner,
    nft_metadata_bundle,
    traits_from_metadata,
)
from .primitives import flatten_text, safe_int, stable_id, ts_to_iso


def telegram_collectible_from_nft(item: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any] | None:
    """Strictly classify Telegram-related NFTs without claiming account identity."""
    bundle = nft_metadata_bundle(item, context)
    text = str(bundle.get("all_text") or "")
    lower = text.casefold()
    nft_address = str(item.get("address") or item.get("nft_address") or "")
    collection_address = str(item.get("collection_address") or item.get("nft_collection") or "")
    verified = bool(item.get("verified"))
    links = [str(value) for value in iter_key_values(bundle, {"external_url", "url", "uri", "link"}) if value]
    phone_match = re.search(r"(?<!\d)(\+888[\d\s-]{4,20}\d)(?!\d)", text)
    phone_evidence = any(
        marker in lower
        for marker in (
            "anonymous telegram number",
            "telegram number",
            "fragment phone",
            "collectible phone",
        )
    ) or any("fragment.com/number" in link.casefold() for link in links)
    if phone_match and phone_evidence:
        number = re.sub(r"[\s-]+", "", phone_match.group(1))
        return {
            "kind": "telegram_number",
            "identifier": number,
            "nft_address": nft_address,
            "collection_address": collection_address,
            "owner_address": nft_effective_owner(item),
            "verified_collection": verified,
            "public_url": f"https://t.me/{number}",
            "confidence": 0.96 if verified else 0.82,
            "evidence": [
                "collectible +888 number in NFT metadata",
                "Telegram/Fragment phone collection markers",
            ],
        }

    username = ""
    for link in links:
        match = re.search(r"(?i)(?:fragment\.com/username/|t\.me/)([a-z][a-z0-9_]{3,31})", link)
        if match and match.group(1).casefold() not in PUBLIC_PROFILE_EXCLUDES:
            username = match.group(1)
            break
    if not username:
        match = re.search(r"(?<![\w@])@([A-Za-z][A-Za-z0-9_]{3,31})(?!\w)", text)
        username = match.group(1) if match else ""
    username_evidence = any(
        marker in lower for marker in ("telegram username", "fragment username", "collectible username")
    ) or any("fragment.com/username" in link.casefold() for link in links)
    if username and username_evidence:
        return {
            "kind": "telegram_username",
            "identifier": username,
            "nft_address": nft_address,
            "collection_address": collection_address,
            "owner_address": nft_effective_owner(item),
            "verified_collection": verified,
            "public_url": f"https://t.me/{username}",
            "confidence": 0.96 if verified else 0.82,
            "evidence": [
                "collectible username in NFT metadata",
                "Telegram/Fragment username collection markers",
            ],
        }

    gift, confidence, evidence = gift_identity_from_nft(item, context)
    if gift and confidence >= 0.40:
        return {
            "kind": "telegram_gift",
            "identifier": gift.slug,
            "nft_address": nft_address,
            "collection_address": collection_address,
            "owner_address": nft_effective_owner(item),
            "verified_collection": verified,
            "public_url": gift.source_url,
            "confidence": confidence,
            "evidence": evidence,
            "gift": asdict(gift),
        }
    return None


def gift_identity_from_nft(
    item: Mapping[str, Any], context: Mapping[str, Any]
) -> tuple[GiftIdentity | None, float, list[str]]:
    bundle = nft_metadata_bundle(item, context)
    slug = exact_gift_slug_from_metadata(bundle)
    all_text = str(bundle.get("all_text") or "")
    token = bundle.get("token_info") or {}
    title, number = parse_title_number(
        token.get("name") if isinstance(token, Mapping) else None,
        item.get("name"),
        all_text,
    )
    evidence: list[str] = []
    confidence = 0.0
    if slug:
        confidence = 0.96
        evidence.append("exact collectible slug found in NFT metadata")
    else:
        lower = all_text.lower()
        hits = [word for word in GIFT_KEYWORDS if word in lower]
        if title and number and hits:
            collection_slug = re.sub(r"[^a-z0-9]+", "", normalize_name(title))
            slug = f"{collection_slug}-{number}" if collection_slug else None
            confidence = 0.52 if len(hits) >= 2 else 0.40
            evidence.extend(["title and number parsed from NFT metadata", *[f"keyword: {x}" for x in hits[:4]]])
    if not slug:
        return None, 0.0, []
    collection_slug, slug_number = split_slug(slug)
    title = title or (str(token.get("name")) if isinstance(token, Mapping) and token.get("name") else None)
    traits = traits_from_metadata(bundle)
    owner = nft_effective_owner(item) or ""
    gift = GiftIdentity(
        slug=slug,
        source_url=f"https://t.me/nft/{slug}",
        title=title,
        number=number or slug_number,
        collection_slug=collection_slug,
        model=traits.get("model"),
        backdrop=traits.get("backdrop") or traits.get("background"),
        symbol=traits.get("symbol") or traits.get("pattern"),
        ton_address_candidates=[
            {
                "address": str(item.get("address") or item.get("nft_address") or ""),
                "role": "nft_candidate",
                "source": "nft_metadata",
            },
            *([{"address": owner, "role": "owner_candidate", "source": "nft_item"}] if owner else []),
        ],
        confidence=confidence,
        evidence=evidence,
    )
    return gift, confidence, evidence


def score_gift_nft(
    gift: GiftIdentity,
    item: Mapping[str, Any],
    context: Mapping[str, Any],
    owner_hint: str | None = None,
) -> NftGiftMatch:
    bundle = nft_metadata_bundle(item, context)
    text = str(bundle.get("all_text") or "")
    lower = text.lower()
    nft_address = str(item.get("address") or item.get("nft_address") or "")
    owner = nft_effective_owner(item) or "" or None
    collection_address = str(item.get("collection_address") or item.get("nft_collection") or "") or None
    evidence: list[str] = []
    score = 0.0
    exact_slug = exact_gift_slug_from_metadata(bundle)
    if exact_slug == gift.slug:
        score += 0.82
        evidence.append("exact gift slug in NFT metadata")
    elif gift.slug.lower() in lower:
        score += 0.62
        evidence.append("gift slug occurs in NFT metadata text")
    token = bundle.get("token_info") or {}
    candidate_title, candidate_number = parse_title_number(
        token.get("name") if isinstance(token, Mapping) else None,
        item.get("name"),
        text,
    )
    if gift.number and candidate_number == gift.number:
        score += 0.22
        evidence.append("collectible number matches")
    if gift.title and candidate_title and normalize_name(gift.title) == normalize_name(candidate_title):
        score += 0.22
        evidence.append("collectible title matches")
    traits = traits_from_metadata(bundle)
    expected = {
        "model": gift.model,
        "backdrop": gift.backdrop,
        "symbol": gift.symbol,
    }
    for key, expected_value in expected.items():
        if not expected_value:
            continue
        actual = (
            traits.get(key)
            or (traits.get("background") if key == "backdrop" else None)
            or (traits.get("pattern") if key == "symbol" else None)
        )
        if actual and normalize_name(actual) == normalize_name(expected_value):
            score += 0.09
            evidence.append(f"{key} trait matches")
    if owner_hint and owner and owner == owner_hint:
        score += 0.08
        evidence.append("current NFT owner matches wallet hint")
    score = min(score, 1.0)
    status = (
        "MATCH_VERIFIED"
        if score >= 0.90
        else "MATCH_STRONG"
        if score >= 0.75
        else "MATCH_PROBABLE"
        if score >= 0.55
        else "MATCH_WEAK"
        if score >= 0.35
        else "REJECT"
    )
    return NftGiftMatch(
        nft_address=nft_address,
        owner_address=owner,
        collection_address=collection_address,
        confidence=score,
        status=status,
        evidence=evidence,
        metadata=bundle,
    )


def is_zero_owner(address: str | None) -> bool:
    if not address:
        return True
    raw = address.lower().replace("0x", "")
    return raw in {"0", "-1:0", "0:" + "0" * 64, "-1:" + "0" * 64} or set(raw.replace(":", "")) <= {"0", "-"}


def classify_nft_history(
    nft_address: str,
    transfers: Iterable[Mapping[str, Any]],
    trace_lookup: Callable[[str], dict[str, Any] | None] | None = None,
) -> list[NftHistoryEvent]:
    events: list[NftHistoryEvent] = []
    for row in transfers:
        old_owner = str(row.get("old_owner") or "") or None
        new_owner = str(row.get("new_owner") or "") or None
        aborted = bool(row.get("transaction_aborted"))
        event_type = "ABORTED" if aborted else "TRANSFER"
        evidence = ["TON Center NFT transfer record"]
        confidence = 1.0
        if not aborted and is_zero_owner(old_owner):
            event_type = "MINT"
        elif not aborted and is_zero_owner(new_owner):
            event_type = "BURN"
        trace_id = str(row.get("trace_id") or "") or None
        if trace_lookup and trace_id and not aborted:
            try:
                trace = trace_lookup(trace_id)
            except TonCenterError:
                trace = None
            if trace:
                action_text = flatten_text(trace.get("actions") or []).lower()
                if any(
                    word in action_text
                    for word in ("nft sale", "nft_sale", "nft purchase", "auction sale", "auction_sale")
                ):
                    event_type = "SALE"
                    confidence = 0.88
                    evidence.append("trace contains a decoded NFT sale/auction action")
        tx_hash = str(row.get("transaction_hash") or "") or None
        tx_lt = safe_int(row.get("transaction_lt"))
        event_id = stable_id(nft_address, tx_hash or "", tx_lt, old_owner or "", new_owner or "")
        events.append(
            NftHistoryEvent(
                event_id=event_id,
                nft_address=nft_address,
                event_type=event_type,
                old_owner=old_owner,
                new_owner=new_owner,
                transaction_lt=tx_lt,
                transaction_time=ts_to_iso(row.get("transaction_now")),
                transaction_hash=tx_hash,
                trace_id=trace_id,
                success=not aborted,
                confidence=confidence,
                evidence=evidence,
            )
        )
    events.sort(key=lambda x: (x.transaction_lt, x.transaction_time or ""))
    return events
