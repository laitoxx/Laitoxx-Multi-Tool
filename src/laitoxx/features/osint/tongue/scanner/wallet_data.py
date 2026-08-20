"""TON Center data-access behavior for wallet scans."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..domain.analysis import dedupe_dicts
from ..domain.models import AddressIdentity
from ..domain.primitives import repeated_params, safe_int, stable_id
from ..provider.toncenter import TonCenterError


class WalletDataMixin:
    def normalize_address(self, address: str) -> AddressIdentity:
        payload = self.client.v2("detectAddress", {"address": address})
        result = payload.get("result", {}) if isinstance(payload, Mapping) else {}
        if not result:
            raise TonCenterError(f"Address is not valid: {address}")
        return AddressIdentity(
            input=address,
            raw=str(result.get("raw_form") or address),
            bounceable=(result.get("bounceable") or {}).get("b64url"),
            non_bounceable=(result.get("non_bounceable") or {}).get("b64url"),
        )

    def auto_select_public_wallet(
        self,
        top_offset: int = 200,
        pool_size: int = 100,
        candidate_index: int = 0,
    ) -> tuple[str, dict[str, Any]]:
        top = self.client.v3(
            "topAccountsByBalance",
            {"limit": max(1, min(pool_size, 1000)), "offset": max(0, top_offset)},
        )
        if not isinstance(top, list):
            raise TonCenterError("topAccountsByBalance returned an unexpected response")
        accounts = [str(x.get("account")) for x in top if isinstance(x, Mapping) and x.get("account")]
        if not accounts:
            raise TonCenterError("No public accounts returned")

        payload = self.client.v3("walletStates", repeated_params("address", accounts))
        wallets = payload.get("wallets", []) if isinstance(payload, Mapping) else []
        candidates = [
            w
            for w in wallets
            if isinstance(w, Mapping)
            and w.get("is_wallet") is True
            and str(w.get("status", "")).lower() == "active"
            and safe_int(w.get("last_transaction_lt")) > 0
            and safe_int(w.get("seqno")) > 0
        ]
        if not candidates:
            candidates = [w for w in wallets if isinstance(w, Mapping) and w.get("is_wallet") is True]
        if not candidates:
            # Fallback: still return a public account; the later state report will show that it is a contract.
            return accounts[0], {"fallback": True, "rank_offset": top_offset}

        idx = min(max(candidate_index, 0), len(candidates) - 1)
        chosen = dict(candidates[idx])
        chosen["rank_offset"] = top_offset
        chosen["candidate_count"] = len(candidates)
        return str(chosen["address"]), chosen

    def get_state(self, address: str) -> dict[str, Any]:
        wallet_payload = self.client.v3("walletStates", [("address", address)])
        account_payload = self.client.v3("accountStates", [("address", address), ("include_boc", "false")])
        return {
            "wallet": (wallet_payload.get("wallets") or [None])[0] if isinstance(wallet_payload, Mapping) else None,
            "account": (account_payload.get("accounts") or [None])[0] if isinstance(account_payload, Mapping) else None,
            "address_book": {
                **(wallet_payload.get("address_book") or {} if isinstance(wallet_payload, Mapping) else {}),
                **(account_payload.get("address_book") or {} if isinstance(account_payload, Mapping) else {}),
            },
            "metadata": {
                **(wallet_payload.get("metadata") or {} if isinstance(wallet_payload, Mapping) else {}),
                **(account_payload.get("metadata") or {} if isinstance(account_payload, Mapping) else {}),
            },
        }

    def get_transactions(self, address: str, start_lt: int = 0) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        params: dict[str, Any] = {"account": address, "sort": "desc"}
        if start_lt > 0:
            params["start_lt"] = start_lt
        self._history_anchor_loaded = False
        recent_limit = self.tx_limit if start_lt > 0 or self.tx_limit <= 1 else self.tx_limit - 1
        transactions, context = self.client.paginate(
            "transactions",
            "transactions",
            params,
            recent_limit,
        )
        # High-volume custodial wallets can burn through the entire budget in
        # minutes. Reserve one row for the oldest transaction so the report
        # still exposes the account's true historical lower bound.
        if start_lt <= 0 and self.tx_limit > 1 and len(transactions) >= recent_limit:
            payload = self.client.v3(
                "transactions",
                {
                    "account": address,
                    "sort": "asc",
                    "limit": 1,
                    "offset": 0,
                },
            )
            if isinstance(payload, Mapping):
                oldest = next(
                    (row for row in payload.get("transactions") or [] if isinstance(row, dict)),
                    None,
                )
                known = {(str(row.get("hash") or ""), safe_int(row.get("lt"))) for row in transactions}
                if oldest and (str(oldest.get("hash") or ""), safe_int(oldest.get("lt"))) not in known:
                    transactions.append(oldest)
                    self._history_anchor_loaded = True
                for key in ("address_book", "metadata"):
                    value = payload.get(key)
                    if isinstance(value, Mapping):
                        context.setdefault(key, {}).update(value)
        return transactions[: self.tx_limit], context

    def get_traces(self, address: str, start_lt: int = 0) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        params: dict[str, Any] = {
            "account": address,
            "include_actions": "true",
            "sort": "desc",
        }
        if start_lt > 0:
            params["start_lt"] = start_lt
        return self.client.paginate("traces", "traces", params, self.trace_limit, chunk_size=25)

    def get_nfts(self, address: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return self.client.paginate(
            "nft/items",
            "nft_items",
            {"owner_address": address, "include_on_sale": "true"},
            self.nft_limit,
        )

    def get_nft_item(self, nft_address: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        cached = self._nft_item_cache.get(nft_address)
        if cached is not None:
            return cached
        payload = self.client.v3("nft/items", [("address", nft_address), ("limit", 10), ("offset", 0)])
        if not isinstance(payload, Mapping):
            result = (None, {})
        else:
            items = payload.get("nft_items") or []
            item = next((x for x in items if isinstance(x, Mapping)), None)
            context = {
                "address_book": dict(payload.get("address_book") or {}),
                "metadata": dict(payload.get("metadata") or {}),
            }
            result = (dict(item) if item else None, context)
        self._nft_item_cache[nft_address] = result
        return result

    def get_nft_items_by_addresses(self, addresses: Sequence[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        unique = list(dict.fromkeys(str(address) for address in addresses if address))[:100]
        if not unique:
            return [], {"address_book": {}, "metadata": {}}
        payload = self.client.v3(
            "nft/items",
            [
                *(("address", address) for address in unique),
                ("limit", len(unique)),
                ("offset", 0),
            ],
        )
        if not isinstance(payload, Mapping):
            return [], {"address_book": {}, "metadata": {}}
        return (
            [dict(item) for item in payload.get("nft_items") or [] if isinstance(item, Mapping)],
            {
                "address_book": dict(payload.get("address_book") or {}),
                "metadata": dict(payload.get("metadata") or {}),
            },
        )

    def get_nft_history(self, nft_address: str, max_items: int = 1000) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        cache_key = f"{nft_address}:{max_items}"
        cached = self._nft_history_cache.get(cache_key)
        if cached is not None:
            return cached
        result = self.client.paginate(
            "nft/transfers",
            "nft_transfers",
            {"item_address": nft_address, "sort": "asc"},
            max_items=max_items,
        )
        self._nft_history_cache[cache_key] = result
        return result

    def get_trace_by_id(self, trace_id: str) -> dict[str, Any] | None:
        if not trace_id:
            return None
        payload = self.client.v3(
            "traces",
            [("trace_id", trace_id), ("include_actions", "true"), ("limit", 1), ("offset", 0)],
        )
        if not isinstance(payload, Mapping):
            return None
        traces = payload.get("traces") or []
        return dict(traces[0]) if traces and isinstance(traces[0], Mapping) else None

    def get_nft_transfers(self, address: str, start_lt: int = 0) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        context: dict[str, Any] = {"address_book": {}, "metadata": {}}
        for direction in ("in", "out"):
            params: dict[str, Any] = {"owner_address": address, "direction": direction, "sort": "desc"}
            if start_lt > 0:
                params["start_lt"] = start_lt
            page, ctx = self.client.paginate("nft/transfers", "nft_transfers", params, self.transfer_limit)
            for row in page:
                row["direction"] = direction
            rows.extend(page)
            context["address_book"].update(ctx.get("address_book") or {})
            context["metadata"].update(ctx.get("metadata") or {})
        return dedupe_dicts(
            rows, lambda x: stable_id(x.get("transaction_hash"), x.get("nft_address"), x.get("direction"))
        ), context

    def get_jetton_transfers(self, address: str, start_lt: int = 0) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        context: dict[str, Any] = {"address_book": {}, "metadata": {}}
        for direction in ("in", "out"):
            params: dict[str, Any] = {"owner_address": address, "direction": direction, "sort": "desc"}
            if start_lt > 0:
                params["start_lt"] = start_lt
            page, ctx = self.client.paginate("jetton/transfers", "jetton_transfers", params, self.transfer_limit)
            for row in page:
                row["direction"] = direction
            rows.extend(page)
            context["address_book"].update(ctx.get("address_book") or {})
            context["metadata"].update(ctx.get("metadata") or {})
        return dedupe_dicts(
            rows,
            lambda x: stable_id(
                x.get("transaction_hash"),
                x.get("jetton_master"),
                x.get("direction"),
                x.get("source"),
                x.get("destination"),
                x.get("amount"),
            ),
        ), context
