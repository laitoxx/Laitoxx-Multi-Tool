"""Wallet collectible enrichment behavior."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..domain.nft import telegram_collectible_from_nft
from ..domain.primitives import short, ts_to_iso


class GiftEnrichmentMixin:
    def enrich_wallet_collectibles(
        self,
        report: dict[str, Any],
        *,
        public_profiles: bool = True,
        collectible_budget: int = 60,
        public_profile_budget: int = 20,
    ) -> None:
        """Find current/historical Telegram collectibles and evidence transitions."""
        current_items = [dict(item) for item in report.get("nft_items") or [] if isinstance(item, Mapping)]
        transfers = [dict(row) for row in report.get("nft_transfers") or [] if isinstance(row, Mapping)]
        current_ids = {str(item.get("address") or item.get("nft_address") or "") for item in current_items}
        historical_ids = list(
            dict.fromkeys(
                str(row.get("nft_address") or "")
                for row in transfers
                if row.get("nft_address") and str(row.get("nft_address")) not in current_ids
            )
        )[: max(0, collectible_budget - len(current_items))]
        historical_items, historical_context = self.scanner.get_nft_items_by_addresses(historical_ids)
        context = {
            "address_book": {
                **dict(report.get("address_book") or {}),
                **dict(historical_context.get("address_book") or {}),
            },
            "metadata": {
                **dict(report.get("metadata") or {}),
                **dict(historical_context.get("metadata") or {}),
            },
        }
        items = current_items + historical_items
        collectibles: list[dict[str, Any]] = []
        transitions: list[dict[str, Any]] = []
        public_checks = 0
        graph = report.setdefault("graph", {"nodes": [], "edges": []})
        graph_nodes = graph.setdefault("nodes", [])
        graph_edges = graph.setdefault("edges", [])
        nodes_by_id = {
            str(node.get("id")): node for node in graph_nodes if isinstance(node, Mapping) and node.get("id")
        }

        for item in items[:collectible_budget]:
            collectible = telegram_collectible_from_nft(item, context)
            if not collectible:
                continue
            nft_address = str(collectible.get("nft_address") or "")
            owner = str(collectible.get("owner_address") or "")
            kind = str(collectible.get("kind") or "")
            identities: list[str] = []
            identity_evidence: list[str] = []
            if public_profiles and public_checks < public_profile_budget:
                if kind == "telegram_gift":
                    public_checks += 1
                    gift = self._resolve_gift(str(collectible["identifier"]), public_profiles=True)
                    identities = list(gift.public_profiles)
                    identity_evidence = list(gift.evidence)
                elif kind == "telegram_username":
                    public_checks += 1
                    active, evidence = self._verify_public_username(str(collectible["identifier"]))
                    if active:
                        identities = [str(collectible["identifier"]).lstrip("@")]
                        identity_evidence = evidence
            collectible["public_identities"] = identities
            collectible["identity_evidence"] = identity_evidence
            collectible["transfer_history"] = [
                row for row in transfers if str(row.get("nft_address") or "") == nft_address
            ]
            collectibles.append(collectible)

            entity_type = {
                "telegram_gift": "telegram_gift",
                "telegram_username": "telegram_username",
                "telegram_number": "telegram_number",
            }.get(kind, "nft")
            node = nodes_by_id.get(nft_address)
            if node is None:
                node = {
                    "id": nft_address,
                    "type": entity_type,
                    "label": str(collectible.get("identifier") or short(nft_address)),
                    "details": collectible,
                }
                graph_nodes.append(node)
                nodes_by_id[nft_address] = node
            else:
                node["type"] = entity_type
                node["label"] = str(collectible.get("identifier") or node.get("label"))
                if not isinstance(node.get("details"), dict):
                    node["details"] = {}
                node["details"].update(collectible)

            for transfer in collectible["transfer_history"]:
                old_owner = str(transfer.get("old_owner") or "")
                new_owner = str(transfer.get("new_owner") or "")
                for wallet, relation in (
                    (old_owner, "PREVIOUSLY_OWNED_COLLECTIBLE"),
                    (new_owner, "RECEIVED_COLLECTIBLE"),
                ):
                    if not wallet:
                        continue
                    if wallet not in nodes_by_id:
                        wallet_node = {
                            "id": wallet,
                            "type": "wallet",
                            "label": short(wallet),
                            "details": {},
                        }
                        graph_nodes.append(wallet_node)
                        nodes_by_id[wallet] = wallet_node
                    graph_edges.append(
                        {
                            "source": wallet,
                            "target": nft_address,
                            "relation": relation,
                            "confidence": 1.0,
                            "evidence": ["TON Center indexed NFT transfer"],
                        }
                    )

            for public_identity in identities:
                profile_id = f"telegram_profile:{public_identity.lstrip('@')}"
                if profile_id not in nodes_by_id:
                    profile_node = {
                        "id": profile_id,
                        "type": "telegram_profile",
                        "label": f"@{public_identity.lstrip('@')}",
                        "details": {"public": True},
                    }
                    graph_nodes.append(profile_node)
                    nodes_by_id[profile_id] = profile_node
                graph_edges.append(
                    {
                        "source": nft_address,
                        "target": profile_id,
                        "relation": "PUBLICLY_DISPLAYED_BY",
                        "confidence": 0.78,
                        "evidence": identity_evidence,
                    }
                )
                previous = self.db.observe_collectible_identity(
                    collectible_id=str(collectible.get("identifier") or nft_address),
                    collectible_kind=kind,
                    nft_address=nft_address,
                    chain_owner=owner or None,
                    public_identity=public_identity.lstrip("@"),
                    source=str(collectible.get("public_url") or "public Telegram page"),
                    evidence=[*collectible.get("evidence", []), *identity_evidence],
                )
                if not previous:
                    continue
                previous_owner = str(previous.get("chain_owner") or "")
                previous_identity = str(previous.get("public_identity") or "")
                matching_transfer = next(
                    (
                        row
                        for row in collectible["transfer_history"]
                        if str(row.get("old_owner") or "") == previous_owner
                        and str(row.get("new_owner") or "") == owner
                    ),
                    None,
                )
                if previous_identity == public_identity.lstrip("@") or not matching_transfer:
                    continue
                transition = {
                    "event_type": "PUBLIC_IDENTITY_TRANSFER",
                    "collectible_kind": kind,
                    "collectible_id": collectible.get("identifier"),
                    "nft_address": nft_address,
                    "old_owner": previous_owner,
                    "new_owner": owner,
                    "old_identity": previous_identity,
                    "new_identity": public_identity.lstrip("@"),
                    "transaction_time": ts_to_iso(matching_transfer.get("transaction_now")),
                    "transaction_hash": matching_transfer.get("transaction_hash"),
                    "confidence": 0.92,
                    "evidence": [
                        "previous locally timestamped public identity observation",
                        "TON NFT transfer old_owner → new_owner",
                        "new public identity observation",
                    ],
                }
                transitions.append(transition)
                old_profile = f"telegram_profile:{previous_identity}"
                if old_profile not in nodes_by_id:
                    old_profile_node = {
                        "id": old_profile,
                        "type": "telegram_profile",
                        "label": f"@{previous_identity}",
                        "details": {"historical": True},
                    }
                    graph_nodes.append(old_profile_node)
                    nodes_by_id[old_profile] = old_profile_node
                graph_edges.append(
                    {
                        "source": old_profile,
                        "target": profile_id,
                        "relation": "COLLECTIBLE_TRANSFER_A_TO_B",
                        "confidence": 0.92,
                        "evidence": transition["evidence"],
                    }
                )

        report["telegram_collectibles"] = collectibles
        report["identity_transitions"] = transitions
        report.setdefault("summary", {}).update(
            {
                "telegram_collectibles": len(collectibles),
                "telegram_gifts": sum(row.get("kind") == "telegram_gift" for row in collectibles),
                "collectible_usernames": sum(row.get("kind") == "telegram_username" for row in collectibles),
                "collectible_numbers": sum(row.get("kind") == "telegram_number" for row in collectibles),
                "identity_transitions": len(transitions),
            }
        )
