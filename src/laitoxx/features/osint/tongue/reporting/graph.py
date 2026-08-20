"""Build the normalized wallet evidence graph."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import asdict
from typing import Any

from ..domain.analysis import address_label
from ..domain.models import GraphEdge, GraphNode, Movement
from ..domain.primitives import short


def build_graph(
    *,
    seed: str,
    movements: Iterable[Movement],
    nft_items: Iterable[Mapping[str, Any]],
    nft_transfers: Iterable[Mapping[str, Any]],
    jetton_transfers: Iterable[Mapping[str, Any]],
    address_book: Mapping[str, Any],
    known_labels: Mapping[str, Any],
) -> dict[str, Any]:
    nodes: dict[str, GraphNode] = {}
    edge_acc: dict[tuple[str, str, str, str], GraphEdge] = {}

    def ensure_node(node_id: str, node_type: str = "account", label: str | None = None, **details: Any) -> None:
        if not node_id:
            return
        if node_id not in nodes:
            nodes[node_id] = GraphNode(
                id=node_id,
                type=node_type,
                label=label or address_label(node_id, address_book, known_labels),
                details=details,
            )
        else:
            nodes[node_id].details.update({k: v for k, v in details.items() if v is not None})

    def add_edge(
        source: str,
        target: str,
        kind: str,
        label: str,
        *,
        total_ton: float = 0.0,
        confidence: float = 1.0,
        asset: str = "",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        if not source or not target:
            return
        key = (source, target, kind, asset)
        if key not in edge_acc:
            edge_acc[key] = GraphEdge(
                source=source,
                target=target,
                kind=kind,
                label=label,
                count=0,
                weight=0.0,
                total_ton=0.0,
                confidence=confidence,
                details=dict(details or {}),
            )
        edge = edge_acc[key]
        edge.count += 1
        edge.weight += max(total_ton, 0.01)
        edge.total_ton += total_ton
        edge.confidence = max(edge.confidence, confidence)

    ensure_node(seed, "seed", "TARGET", canonical_address=seed)

    for mv in movements:
        ensure_node(mv.source)
        ensure_node(mv.destination)
        add_edge(
            mv.source,
            mv.destination,
            "TON_TRANSFER",
            "TON",
            total_ton=mv.amount_ton,
            confidence=1.0 if mv.success else 0.7,
            details={"classification": mv.classification},
        )

    for item in nft_items:
        nft = str(item.get("address") or "")
        if not nft:
            continue
        possible_gift = bool(item.get("possible_telegram_collectible"))
        info = item.get("token_info") or {}
        nft_label = str(info.get("name") or ("Possible Gift" if possible_gift else f"NFT {short(nft)}"))
        ensure_node(
            nft,
            "possible_gift" if possible_gift else "nft",
            nft_label,
            collection=item.get("collection_address"),
            gift_confidence=item.get("gift_confidence"),
        )
        owner = str(item.get("real_owner") or item.get("owner_address") or seed)
        ensure_node(owner)
        add_edge(owner, nft, "OWNS_NFT", "owns", confidence=1.0, asset=nft)

    for transfer in nft_transfers:
        old = str(transfer.get("old_owner") or "")
        new = str(transfer.get("new_owner") or "")
        nft = str(transfer.get("nft_address") or "")
        ensure_node(old)
        ensure_node(new)
        if old and new:
            add_edge(old, new, "NFT_TRANSFER", f"NFT {short(nft)}", confidence=1.0, asset=nft)

    for transfer in jetton_transfers:
        source = str(transfer.get("source") or "")
        destination = str(transfer.get("destination") or "")
        master = str(transfer.get("jetton_master") or "")
        ensure_node(source)
        ensure_node(destination)
        token_label = address_label(master, address_book, known_labels) if master else "Jetton"
        add_edge(
            source,
            destination,
            "JETTON_TRANSFER",
            token_label,
            confidence=1.0,
            asset=master,
            details={"amount_raw": transfer.get("amount"), "jetton_master": master},
        )

    # Node weight based on adjacent activity.
    for edge in edge_acc.values():
        if edge.source in nodes:
            nodes[edge.source].weight += math.log1p(edge.weight) + edge.count * 0.15
        if edge.target in nodes:
            nodes[edge.target].weight += math.log1p(edge.weight) + edge.count * 0.15

    return {
        "nodes": [asdict(node) for node in nodes.values()],
        "edges": [asdict(edge) for edge in edge_acc.values()],
    }
