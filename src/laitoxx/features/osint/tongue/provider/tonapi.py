"""Reusable TonAPI HTTP operations for gift resolution."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import requests

from ..domain.chain import GiftChainError

TONAPI_BASE = "https://tonapi.io"
TONAPI_GRAPHQL = f"{TONAPI_BASE}/v2/graphql"
FRAGMENT_GIFT_METADATA = "https://nft.fragment.com/gift/{slug}.json"


class TonApiClientMixin:
    def _get(self, url: str, *, params: Mapping[str, Any] | None = None) -> requests.Response:
        self._check_cancelled()
        try:
            return self.session.get(url, params=params, headers=self.headers, timeout=self.timeout)
        except requests.RequestException as exc:
            raise GiftChainError(str(exc)) from exc

    def _post_json(self, url: str, payload: Mapping[str, Any]) -> dict[str, Any] | None:
        self._check_cancelled()
        try:
            response = self.session.post(url, json=payload, headers=self.headers, timeout=self.timeout)
        except requests.RequestException as exc:
            raise GiftChainError(str(exc)) from exc
        if response.status_code >= 400 or not response.content:
            return None
        try:
            data = response.json()
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    def _graphql_lookup(self, metadata_url: str) -> dict[str, Any] | None:
        # `condition` is an equality query over the indexed get_nft_data URL.
        query = """
        query GiftByMetadata($url: String!) {
          allGetNftData(first: 3, condition: {url: $url}) {
            nodes {
              accountRawAddress ownerRawAddress collectionRawAddress url index verified
            }
          }
        }
        """
        payload = self._post_json(TONAPI_GRAPHQL, {"query": query, "variables": {"url": metadata_url}})
        nodes = (((payload or {}).get("data") or {}).get("allGetNftData") or {}).get("nodes") or []
        return dict(nodes[0]) if nodes and isinstance(nodes[0], Mapping) else None

    def _item_details(self, address: str) -> dict[str, Any] | None:
        response = self._get(f"{TONAPI_BASE}/v2/nfts/{address}")
        if response.status_code >= 400:
            return None
        try:
            data = response.json()
        except ValueError:
            return None
        return dict(data) if isinstance(data, Mapping) else None
