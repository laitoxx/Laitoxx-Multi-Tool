"""Domain records and normalization for on-chain gift resolution."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

# Verified from the collection returned by TonAPI for exported Lol Pop gifts.
# More collections are learned into the local cache as exact lookups succeed.
KNOWN_GIFT_COLLECTIONS: dict[str, tuple[str, str]] = {
    "lolpop": (
        "0:bace389df2f24d116a9c5e4d745e3b1d0cb44a6dc3d9cdb1eeb2e116e85a2439",
        "Lol Pops",
    ),
}


class GiftChainError(RuntimeError):
    pass


@dataclass(slots=True)
class GiftChainResolution:
    gift_slug: str
    status: str
    message: str
    metadata_url: str
    item_address: str | None = None
    owner_address: str | None = None
    collection_address: str | None = None
    collection_name: str | None = None
    verified: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    item: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    indexed_items_checked: int = 0
    cache_hit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _gift_slug_from_name(value: Any) -> str:
    match = re.search(r"^\s*(.+?)\s*#\s*(\d+)\s*$", str(value or ""))
    if not match:
        return ""
    title = re.sub(r"[^a-z0-9]+", "", match.group(1).casefold())
    return f"{title}-{match.group(2)}"


def _account_address(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = value.get("address") or value.get("account_address")
    text = str(value or "").strip()
    return text or None
