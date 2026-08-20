"""Normalize NFT metadata from TON provider payloads."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from .analysis import get_token_info
from .constants import GIFT_KEYWORDS
from .gifts import normalize_gift_slug
from .primitives import flatten_text, jsonable


def iter_key_values(value: Any, wanted: set[str], max_depth: int = 7) -> Iterator[Any]:
    def walk(obj: Any, depth: int) -> Iterator[Any]:
        if depth > max_depth:
            return
        if isinstance(obj, Mapping):
            for key, val in obj.items():
                if str(key).lower() in wanted:
                    yield val
                yield from walk(val, depth + 1)
        elif isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
            for item in obj[:200]:
                yield from walk(item, depth + 1)

    yield from walk(value, 0)


def nft_metadata_bundle(item: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    metadata = context.get("metadata") or {} if isinstance(context, Mapping) else {}
    nft_address = str(item.get("address") or item.get("nft_address") or "")
    collection_address = str(item.get("collection_address") or item.get("nft_collection") or "")
    token_info = get_token_info(metadata, nft_address) or {}
    collection_info = get_token_info(metadata, collection_address) or {}
    content = item.get("content") or {}
    collection = item.get("collection") or {}
    bundle = {
        "item": jsonable(item),
        "token_info": jsonable(token_info),
        "collection_token_info": jsonable(collection_info),
        "content": jsonable(content),
        "collection": jsonable(collection),
    }
    bundle["all_text"] = flatten_text(bundle, max_depth=8)
    return bundle


def exact_gift_slug_from_metadata(bundle: Mapping[str, Any]) -> str | None:
    # Prefer explicit Telegram collectible links; they are much stronger than a generic "slug" field.
    for value in iter_key_values(bundle, {"external_url", "url", "uri", "link"}):
        text = str(value or "")
        if "t.me/nft/" in text.lower() or "tg://nft" in text.lower():
            try:
                return normalize_gift_slug(text)
            except ValueError:
                pass
    text = str(bundle.get("all_text") or "")
    match = re.search(r"(?i)(?:https?://t\.me/nft/|tg://nft\?slug=)([a-z0-9][a-z0-9_-]*-\d+)", text)
    if match:
        return match.group(1).lower()
    for value in iter_key_values(bundle, {"gift_slug", "collectible_slug", "stargift_slug"}):
        candidate = str(value or "")
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*-\d+", candidate):
            return candidate.lower()
    lower = text.lower()
    if any(keyword in lower for keyword in GIFT_KEYWORDS):
        for value in iter_key_values(bundle, {"slug"}):
            candidate = str(value or "")
            if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*-\d+", candidate):
                return candidate.lower()
    return None


def traits_from_metadata(bundle: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for attrs in iter_key_values(bundle, {"attributes", "traits"}):
        if not isinstance(attrs, Sequence) or isinstance(attrs, (str, bytes, bytearray)):
            continue
        for row in attrs:
            if not isinstance(row, Mapping):
                continue
            key = str(row.get("trait_type") or row.get("type") or row.get("name") or "").strip()
            val = str(row.get("value") or row.get("text") or "").strip()
            if key and val:
                result[key.lower()] = val
    return result


def nft_effective_owner(item: Mapping[str, Any]) -> str | None:
    value = item.get("real_owner") or item.get("owner_address") or item.get("owner")
    return str(value) if value else None


def nft_custody_owner(item: Mapping[str, Any]) -> str | None:
    value = item.get("owner_address") or item.get("owner")
    return str(value) if value else None
