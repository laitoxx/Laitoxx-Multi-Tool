"""Merge resolved on-chain gift identity into an investigation report."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .chain_resolver import GiftChainResolution


def _attach_chain_resolution(report: dict[str, Any], resolution: GiftChainResolution) -> None:
    """Attach explicit hosted/exported state and its contracts to a report."""
    chain = resolution.to_dict()
    report["chain_resolution"] = chain
    summary = report.setdefault("summary", {})
    summary.update(
        {
            "onchain_status": resolution.status,
            "nft_item_contract": resolution.item_address,
            "blockchain_owner": resolution.owner_address,
            "collection_contract": resolution.collection_address,
        }
    )

    graph = report.setdefault("graph", {"nodes": [], "edges": []})
    nodes = graph.setdefault("nodes", [])
    edges = graph.setdefault("edges", [])
    gift_id = f"gift:{resolution.gift_slug}"
    if not any(str(row.get("id")) == gift_id for row in nodes if isinstance(row, Mapping)):
        nodes.append(
            {
                "id": gift_id,
                "type": "gift",
                "label": resolution.gift_slug,
                "details": {"chain_status": resolution.status},
            }
        )

    if resolution.collection_address:
        collection_id = f"ton_collection:{resolution.collection_address}"
        nodes.append(
            {
                "id": collection_id,
                "type": "ton_collection",
                "label": resolution.collection_name or resolution.collection_address,
                "details": {
                    "address": resolution.collection_address,
                    "name": resolution.collection_name,
                    "verified_family": True,
                },
            }
        )
        edges.append(
            {
                "source": gift_id,
                "target": collection_id,
                "relation": "COLLECTION_FAMILY",
                "confidence": 0.98,
                "evidence": resolution.evidence,
            }
        )

    if resolution.item_address:
        nft_id = f"nft:{resolution.item_address}"
        nodes.append(
            {
                "id": nft_id,
                "type": "nft",
                "label": str(resolution.metadata.get("name") or resolution.gift_slug),
                "details": resolution.item or chain,
            }
        )
        edges.append(
            {
                "source": gift_id,
                "target": nft_id,
                "relation": "EXPORTED_AS_NFT",
                "confidence": 1.0,
                "evidence": resolution.evidence,
            }
        )
        if resolution.owner_address:
            owner_id = f"wallet:{resolution.owner_address}"
            nodes.append(
                {
                    "id": owner_id,
                    "type": "wallet",
                    "label": resolution.owner_address,
                    "details": {"role": "current blockchain owner"},
                }
            )
            edges.append(
                {
                    "source": nft_id,
                    "target": owner_id,
                    "relation": "CURRENTLY_OWNED_BY",
                    "confidence": 1.0,
                    "evidence": ["TonAPI indexed NFT owner contract state"],
                }
            )

    unique_nodes: dict[str, dict[str, Any]] = {}
    for row in nodes:
        if isinstance(row, Mapping) and row.get("id"):
            unique_nodes[str(row["id"])] = dict(row)
    graph["nodes"] = list(unique_nodes.values())

    unique_edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in edges:
        if not isinstance(row, Mapping):
            continue
        signature = (
            str(row.get("source") or ""),
            str(row.get("target") or ""),
            str(row.get("relation") or ""),
        )
        if all(signature):
            unique_edges[signature] = dict(row)
    graph["edges"] = list(unique_edges.values())
