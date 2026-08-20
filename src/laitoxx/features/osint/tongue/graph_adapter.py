"""Adapt TONgue evidence reports to the shared graph model."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from laitoxx.shared.graph.model import Edge, Graph, Node

_GRAPH_PREFIXES = {
    "wallet",
    "nft",
    "gift",
    "telegram_profile",
    "ton_collection",
    "nft_event",
    "jetton",
}


def _canonical_graph_id(node_id: str, entity_type: str = "") -> str:
    """Give primary wallet evidence the same identifiers as recursive evidence."""
    if any(node_id.startswith(f"{prefix}:") for prefix in _GRAPH_PREFIXES):
        return node_id
    prefix = {
        "seed": "wallet",
        "account": "wallet",
        "wallet": "wallet",
        "nft": "nft",
        "possible_gift": "nft",
        "gift": "gift",
        "ton_collection": "ton_collection",
        "jetton": "jetton",
        "telegram_gift": "nft",
        "telegram_username": "nft",
        "telegram_number": "nft",
    }.get(entity_type, "wallet")
    return f"{prefix}:{node_id}"


def _merge_primary_evidence(report: dict[str, Any], primary: Mapping[str, Any]) -> None:
    """Keep wallet transactions visible when a recursive investigation is enabled."""
    target_graph = report.setdefault("graph", {"nodes": [], "edges": []})
    target_nodes = target_graph.setdefault("nodes", [])
    target_edges = target_graph.setdefault("edges", [])
    primary_graph = primary.get("graph") or {}

    node_ids: dict[str, str] = {}
    existing = {str(row.get("id")): row for row in target_nodes if isinstance(row, Mapping) and row.get("id")}
    for source in primary_graph.get("nodes") or []:
        if not isinstance(source, Mapping):
            continue
        old_id = str(source.get("id") or "")
        if not old_id:
            continue
        canonical = _canonical_graph_id(old_id, str(source.get("type") or ""))
        node_ids[old_id] = canonical
        row = dict(source)
        row["id"] = canonical
        if str(row.get("type") or "") in {"seed", "account"}:
            row["type"] = "wallet"
        previous = existing.get(canonical)
        if previous is None:
            target_nodes.append(row)
            existing[canonical] = row
        else:
            details = row.get("details")
            if isinstance(details, Mapping):
                previous.setdefault("details", {}).update(details)
            if float(row.get("weight") or 0) > float(previous.get("weight") or 0):
                previous["weight"] = row.get("weight")

    signatures = {
        (
            str(row.get("source") or row.get("source_id") or ""),
            str(row.get("target") or row.get("target_id") or ""),
            str(row.get("relation") or row.get("kind") or row.get("label") or ""),
        )
        for row in target_edges
        if isinstance(row, Mapping)
    }
    for source in primary_graph.get("edges") or []:
        if not isinstance(source, Mapping):
            continue
        raw_source = str(source.get("source") or source.get("source_id") or "")
        raw_target = str(source.get("target") or source.get("target_id") or "")
        source_id = node_ids.get(raw_source, _canonical_graph_id(raw_source))
        target_id = node_ids.get(raw_target, _canonical_graph_id(raw_target))
        relation = str(source.get("relation") or source.get("kind") or source.get("label") or "RELATED_TO")
        signature = (source_id, target_id, relation)
        if not raw_source or not raw_target or signature in signatures:
            continue
        row = dict(source)
        row.update({"source": source_id, "target": target_id, "relation": relation})
        target_edges.append(row)
        signatures.add(signature)

    movements = [row for row in primary.get("movements") or [] if isinstance(row, Mapping)]
    if movements:
        report["movements"] = movements
    primary_summary = primary.get("summary") or {}
    report["history_coverage"] = {
        key: primary_summary.get(key)
        for key in (
            "transactions_loaded",
            "movements_parsed",
            "history_newest",
            "history_oldest",
            "history_truncated",
            "history_anchor_loaded",
        )
    }
    report.setdefault("summary", {}).update(
        {
            "transaction_entities": len(movements),
            "history_oldest": primary_summary.get("history_oldest"),
            "history_newest": primary_summary.get("history_newest"),
            "history_truncated": primary_summary.get("history_truncated", False),
            "telegram_collectibles": primary_summary.get("telegram_collectibles", 0),
            "telegram_gifts": primary_summary.get("telegram_gifts", 0),
            "collectible_usernames": primary_summary.get("collectible_usernames", 0),
            "collectible_numbers": primary_summary.get("collectible_numbers", 0),
            "identity_transitions": primary_summary.get("identity_transitions", 0),
        }
    )


_NODE_TYPE_MAP = {
    "seed": "TONWallet",
    "account": "TONWallet",
    "wallet": "TONWallet",
    "nft": "TONNFT",
    "ton_collection": "TONCollection",
    "possible_gift": "TelegramGift",
    "gift": "TelegramGift",
    "telegram_profile": "TelegramProfile",
    "telegram_gift": "TelegramGift",
    "telegram_username": "Username",
    "telegram_number": "PhoneNumber",
    "nft_event": "BlockchainEvent",
    "transaction": "BlockchainEvent",
    "jetton": "Jetton",
}


def _stringify_metadata(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {"value": json.dumps(value, ensure_ascii=False, default=str)}
    result: dict[str, str] = {}
    for key, item in value.items():
        if item is None:
            continue
        if isinstance(item, (str, int, float, bool)):
            result[str(key)] = str(item)
        else:
            result[str(key)] = json.dumps(item, ensure_ascii=False, default=str)
    return result


def report_to_graph(report: Mapping[str, Any], max_nodes: int = 600, max_edges: int = 1400) -> tuple[Graph, int, int]:
    """Convert TONgue evidence to the editor model with a crash-safe projection."""
    source = report.get("graph") or {}
    raw_nodes = [row for row in source.get("nodes", []) if isinstance(row, Mapping)]
    raw_edges = [row for row in source.get("edges", []) if isinstance(row, Mapping)]

    priority = {
        "gift": 0,
        "telegram_gift": 0,
        "wallet": 1,
        "nft": 2,
        "telegram_username": 2,
        "telegram_number": 2,
        "telegram_profile": 3,
        "jetton": 4,
        "nft_event": 8,
    }
    unique: dict[str, Mapping[str, Any]] = {}
    for row in raw_nodes:
        node_id = str(row.get("id") or "")
        if node_id and node_id not in unique:
            unique[node_id] = row
    ordered = sorted(
        unique.values(),
        key=lambda row: (
            priority.get(str(row.get("type")), 6),
            -float(row.get("weight") or 0),
            str(row.get("id")),
        ),
    )
    kept_rows = ordered[: max(1, max_nodes)]
    kept_ids = {str(row.get("id")) for row in kept_rows}

    graph = Graph(
        name=f"TONgue: {(report.get('summary') or {}).get('seed') or (report.get('summary') or {}).get('seed_raw') or 'investigation'}"
    )
    seed_value = str(
        ((report.get("seed") or {}).get("id") if isinstance(report.get("seed"), Mapping) else "")
        or (report.get("summary") or {}).get("seed_raw")
        or ((report.get("primary_investigation") or {}).get("summary") or {}).get("seed_raw")
        or ""
    )
    nodes: dict[str, Node] = {}
    for row in kept_rows:
        source_id = str(row.get("id"))
        entity_type = str(row.get("type") or "custom")
        node = Node.from_type(str(row.get("label") or source_id), _NODE_TYPE_MAP.get(entity_type, "Custom"))
        node.description = str(row.get("description") or "")
        details = row.get("details")
        if details is None:
            details = {key: value for key, value in row.items() if key not in {"id", "label", "type"}}
        node.metadata = {
            "tongue_id": source_id,
            "entity_type": entity_type,
            "is_target": str(source_id) in {seed_value, f"wallet:{seed_value}"},
            **_stringify_metadata(details),
        }
        graph.add_node(node)
        nodes[source_id] = node

    seen_edges: set[tuple[str, str, str]] = set()
    kept_edge_count = 0
    for row in raw_edges:
        if kept_edge_count >= max_edges:
            break
        source_id = str(row.get("source") or row.get("source_id") or "")
        target_id = str(row.get("target") or row.get("target_id") or "")
        relation = str(row.get("relation") or row.get("label") or "RELATED_TO")
        signature = (source_id, target_id, relation)
        if source_id not in kept_ids or target_id not in kept_ids or signature in seen_edges:
            continue
        seen_edges.add(signature)
        edge = Edge(nodes[source_id].id, nodes[target_id].id, label=relation, edge_type="RelatedTo")
        confidence = row.get("confidence")
        edge.metadata = _stringify_metadata(
            {
                "confidence": confidence,
                "evidence": row.get("evidence") or [],
                "depth": row.get("depth"),
                "count": row.get("count"),
                "total_ton": row.get("total_ton"),
                "details": row.get("details") or {},
            }
        )
        if confidence is not None and float(confidence) < 0.55:
            edge.mermaid_line = "-.->"
        graph.add_edge(edge)
        kept_edge_count += 1

    return graph, max(0, len(unique) - len(kept_rows)), max(0, len(raw_edges) - kept_edge_count)
