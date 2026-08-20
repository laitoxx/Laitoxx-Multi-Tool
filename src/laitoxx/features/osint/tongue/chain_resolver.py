"""Public Telegram Gift to TON NFT resolution.

The public Telegram collectible page describes the hosted gift, but it does
not expose an NFT item address.  Exported gifts receive deterministic Fragment
metadata and a TEP-62 item contract.  This module keeps those two states
separate and resolves the on-chain object without a Telegram user session.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import requests

from laitoxx.core.settings.network_manager import get_session

from .domain.chain import GiftChainResolution, _account_address, _gift_slug_from_name
from .domain.models import GiftIdentity
from .persistence.gift_index import GiftIndex
from .provider.tonapi import (
    FRAGMENT_GIFT_METADATA,
    TONAPI_BASE,
    TONAPI_GRAPHQL,
    TonApiClientMixin,
)
from .provider.toncenter import OperationCancelled


class GiftChainResolver(TonApiClientMixin):
    """Resolve an exported Telegram Gift to its public TON contracts."""

    def __init__(
        self,
        cache_path: Path,
        *,
        api_key: str | None = None,
        timeout: float = 30.0,
        cancel_check: Callable[[], bool] | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.timeout = timeout
        self.cancel_check = cancel_check or (lambda: False)
        self.session = session or get_session()
        self.headers = {
            "User-Agent": "Laitoxx-TONgue/1.0 (+public TON investigation)",
            "Accept": "application/json",
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key.strip()}"
        self.index = GiftIndex(cache_path)

    def close(self) -> None:
        self.index.close()

    def _check_cancelled(self) -> None:
        if self.cancel_check():
            raise OperationCancelled("TONgue investigation cancelled")

    def resolve(self, gift: GiftIdentity, *, item_budget: int = 5000) -> GiftChainResolution:
        """Resolve the gift, preserving the difference between hosted and exported."""
        slug = gift.slug.casefold()
        metadata_url = FRAGMENT_GIFT_METADATA.format(slug=slug)
        collection_slug = gift.collection_slug or slug.rsplit("-", 1)[0]
        collection = self.index.get_collection(collection_slug)
        collection_address = collection[0] if collection else None
        collection_name = collection[1] if collection else None

        cached = self.index.get_item(slug)
        if cached:
            return GiftChainResolution(
                gift_slug=slug,
                status="exported",
                message="The gift has a TON NFT item contract (local index hit).",
                metadata_url=metadata_url,
                metadata=dict(cached["item"].get("metadata") or {}),
                evidence=["previously verified TonAPI NFT item cache entry"],
                sources=[{"name": "Local TONgue index", "status": "hit"}],
                cache_hit=True,
                **{
                    key: cached[key]
                    for key in (
                        "item_address",
                        "owner_address",
                        "collection_address",
                        "collection_name",
                        "verified",
                        "item",
                    )
                },
            )

        fragment = self._get(metadata_url)
        fragment_source = {
            "name": "Fragment NFT metadata",
            "url": metadata_url,
            "status": fragment.status_code,
        }
        if fragment.status_code == 404:
            return GiftChainResolution(
                gift_slug=slug,
                status="not_exported",
                message=(
                    "The collectible is hosted by Telegram and has not been exported to an individual TON NFT contract."
                ),
                metadata_url=metadata_url,
                collection_address=collection_address,
                collection_name=collection_name,
                evidence=[
                    "public Telegram collectible page exists",
                    "deterministic Fragment NFT metadata returns HTTP 404",
                    "no item contract or blockchain owner exists until export",
                ],
                sources=[fragment_source],
            )
        if fragment.status_code >= 400:
            return GiftChainResolution(
                gift_slug=slug,
                status="source_error",
                message=f"Fragment metadata lookup failed with HTTP {fragment.status_code}.",
                metadata_url=metadata_url,
                collection_address=collection_address,
                collection_name=collection_name,
                evidence=["on-chain state could not be proven from the public source"],
                sources=[fragment_source],
            )
        try:
            fragment_metadata = fragment.json()
        except ValueError:
            fragment_metadata = {}
        if not isinstance(fragment_metadata, dict):
            fragment_metadata = {}

        node = self._graphql_lookup(metadata_url)
        sources = [
            fragment_source,
            {
                "name": "TonAPI analytics index",
                "url": TONAPI_GRAPHQL,
                "status": "found" if node else "fallback",
            },
        ]
        if node and node.get("accountRawAddress"):
            item = self._item_details(str(node["accountRawAddress"]))
            if not item:
                item = {
                    "address": node.get("accountRawAddress"),
                    "owner": {"address": node.get("ownerRawAddress")},
                    "collection": {"address": node.get("collectionRawAddress")},
                    "verified": node.get("verified"),
                    "metadata": fragment_metadata,
                }
            return self._found(slug, metadata_url, fragment_metadata, item, sources, 0)

        if collection_address:
            item, checked, exhausted = self._scan_collection(collection_address, slug, max(1, item_budget))
            sources.append(
                {
                    "name": "TonAPI collection index",
                    "url": f"{TONAPI_BASE}/v2/nfts/collections/{collection_address}/items",
                    "status": "found" if item else ("exhausted" if exhausted else "budget_reached"),
                    "items_checked": checked,
                }
            )
            if item:
                return self._found(slug, metadata_url, fragment_metadata, item, sources, checked)
            return GiftChainResolution(
                gift_slug=slug,
                status="index_pending",
                message=(
                    "Fragment confirms an exported NFT, but its contract was not resolved "
                    "inside the configured public-index budget."
                ),
                metadata_url=metadata_url,
                collection_address=collection_address,
                collection_name=collection_name,
                metadata=fragment_metadata,
                evidence=[
                    "deterministic Fragment NFT metadata exists",
                    "exact TonAPI lookup returned no item",
                    f"collection fallback checked {checked} indexed items",
                ],
                sources=sources,
                indexed_items_checked=checked,
            )

        return GiftChainResolution(
            gift_slug=slug,
            status="index_pending",
            message=("Fragment confirms an exported NFT, but the public index did not return its contract address."),
            metadata_url=metadata_url,
            metadata=fragment_metadata,
            evidence=[
                "deterministic Fragment NFT metadata exists",
                "TonAPI exact lookup returned no item",
            ],
            sources=sources,
        )

    def _scan_collection(
        self, collection_address: str, gift_slug: str, item_budget: int
    ) -> tuple[dict[str, Any] | None, int, bool]:
        checked = 0
        page_size = min(1000, item_budget)
        offset = 0
        while checked < item_budget:
            limit = min(page_size, item_budget - checked)
            response = self._get(
                f"{TONAPI_BASE}/v2/nfts/collections/{collection_address}/items",
                params={"limit": limit, "offset": offset},
            )
            if response.status_code >= 400:
                return None, checked, False
            try:
                payload = response.json()
            except ValueError:
                return None, checked, False
            items = payload.get("nft_items") if isinstance(payload, Mapping) else None
            if not isinstance(items, list):
                return None, checked, False
            for row in items:
                if not isinstance(row, Mapping):
                    continue
                checked += 1
                metadata = row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {}
                row_slug = _gift_slug_from_name(metadata.get("name"))
                if row_slug:
                    self.index.save_item(row_slug, row)
                if row_slug == gift_slug:
                    return dict(row), checked, len(items) < limit
            if len(items) < limit:
                return None, checked, True
            offset += len(items)
        return None, checked, False

    def _found(
        self,
        gift_slug: str,
        metadata_url: str,
        fragment_metadata: Mapping[str, Any],
        item: Mapping[str, Any],
        sources: list[dict[str, Any]],
        checked: int,
    ) -> GiftChainResolution:
        self.index.save_item(gift_slug, item)
        owner = _account_address(item.get("owner"))
        collection = item.get("collection") if isinstance(item.get("collection"), Mapping) else {}
        return GiftChainResolution(
            gift_slug=gift_slug,
            status="exported",
            message="The gift is exported and has an individual TON NFT contract.",
            metadata_url=metadata_url,
            item_address=_account_address(item.get("address")),
            owner_address=owner,
            collection_address=_account_address(collection),
            collection_name=str(collection.get("name") or "") or None,
            verified=bool(item.get("verified")) if item.get("verified") is not None else None,
            metadata=dict(item.get("metadata") or fragment_metadata),
            item=dict(item),
            evidence=[
                "deterministic Fragment NFT metadata exists",
                "TonAPI resolved a TEP-62 NFT item contract",
                "owner and collection addresses were read from the indexed contract state",
            ],
            sources=sources,
            indexed_items_checked=checked,
        )
