"""Recursive evidence graph discovery behavior."""

from __future__ import annotations

import heapq
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any

from ..domain.models import DiscoveryTask
from ..domain.nft import classify_nft_history, gift_identity_from_nft
from ..domain.nft_metadata import nft_effective_owner
from ..domain.primitives import jsonable, short, utc_now_iso
from ..provider.public_web import PublicWebError
from ..provider.toncenter import TonCenterError


class GiftRecursiveMixin:
    def recursive_explore(
        self,
        seed_type: str,
        seed_id: str,
        max_depth: int = 3,
        wallet_budget: int = 20,
        nft_budget: int = 200,
        history_budget: int = 3000,
        profile_budget: int = 100,
        nfts_per_wallet: int = 100,
        public_profiles: bool = True,
        trace_sales: bool = False,
        wallet_hint: str | None = None,
    ) -> dict[str, Any]:
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        timelines: dict[str, list[dict[str, Any]]] = {}
        observations: list[dict[str, Any]] = []
        queue: list[DiscoveryTask] = []
        visited_depth: dict[tuple[str, str], int] = {}
        counts = {"wallets": 0, "nfts": 0, "history": 0, "profiles": 0, "gifts": 0}

        def node_id(kind: str, value: str) -> str:
            return f"{kind}:{value}"

        def add_node(kind: str, value: str, label: str | None = None, **details: Any) -> str:
            nid = node_id(kind, value)
            existing = nodes.get(nid)
            row = {"id": nid, "type": kind, "label": label or short(value), "details": jsonable(details)}
            if existing:
                existing["details"].update(row["details"])
                if label:
                    existing["label"] = label
            else:
                nodes[nid] = row
            return nid

        def add_edge(
            source: str, target: str, relation: str, confidence: float, depth: int, evidence: Sequence[str]
        ) -> None:
            row = {
                "source": source,
                "target": target,
                "relation": relation,
                "confidence": round(float(confidence), 4),
                "depth": depth,
                "evidence": list(evidence),
            }
            signature = (source, target, relation)
            for old in edges:
                if (old["source"], old["target"], old["relation"]) == signature:
                    if row["confidence"] > old["confidence"]:
                        old.update(row)
                    return
            edges.append(row)

        def push(
            kind: str,
            value: str,
            depth: int,
            priority: int,
            parent: str | None = None,
            relation: str | None = None,
            confidence: float = 1.0,
        ) -> None:
            if value and depth <= max_depth:
                heapq.heappush(queue, DiscoveryTask(priority, depth, kind, value, parent, relation, confidence))

        push(seed_type, seed_id, 0, 100)
        if wallet_hint:
            push("wallet", wallet_hint, 0, 96, node_id(seed_type, seed_id), "WALLET_HINT", 0.60)

        while queue:
            task = heapq.heappop(queue)
            key = (task.entity_type, task.entity_id)
            previous_depth = visited_depth.get(key)
            if previous_depth is not None and previous_depth <= task.depth:
                continue
            visited_depth[key] = task.depth
            if task.entity_type == "wallet" and counts["wallets"] >= wallet_budget:
                continue
            if task.entity_type == "nft" and counts["nfts"] >= nft_budget:
                continue
            if task.entity_type == "gift" and counts["gifts"] >= nft_budget:
                continue

            if task.entity_type == "gift":
                counts["gifts"] += 1
                try:
                    gift = self._resolve_gift(task.entity_id, public_profiles=public_profiles)
                except (ValueError, PublicWebError):
                    continue
                gid = add_node(
                    "gift", gift.slug, gift.title and f"{gift.title} #{gift.number}" or gift.slug, **asdict(gift)
                )
                if task.parent_id and task.relation:
                    add_edge(task.parent_id, gid, task.relation, task.confidence, task.depth, ["recursive discovery"])
                for profile in gift.public_profiles:
                    if counts["profiles"] >= profile_budget:
                        break
                    counts["profiles"] += 1
                    pid = add_node("telegram_profile", profile, profile, public=True)
                    add_edge(gid, pid, "PUBLICLY_DISPLAYED_BY", 0.75, task.depth, ["public t.me/Fragment link"])
                matches, wallets = self.validate_public_candidates(gift)
                for match in matches:
                    nid = add_node("nft", match.nft_address, gift.slug, match=asdict(match))
                    add_edge(gid, nid, "MATCHED_TO_NFT_ITEM", match.confidence, task.depth, match.evidence)
                    push("nft", match.nft_address, task.depth + 1, 98, gid, "MATCHED_TO_NFT_ITEM", match.confidence)
                for wallet in wallets:
                    wid = add_node("wallet", wallet, short(wallet), public_candidate=True)
                    add_edge(
                        gid,
                        wid,
                        "PUBLIC_TON_ADDRESS_CANDIDATE",
                        0.45,
                        task.depth,
                        ["address exposed on public collectible page"],
                    )
                    push("wallet", wallet, task.depth + 1, 72, gid, "PUBLIC_TON_ADDRESS_CANDIDATE", 0.45)

            elif task.entity_type == "nft":
                counts["nfts"] += 1
                try:
                    identity = self.scanner.normalize_address(task.entity_id)
                    item, context = self.scanner.get_nft_item(identity.raw)
                except TonCenterError:
                    continue
                if not item:
                    continue
                nft_address = identity.raw
                gift, gift_confidence, gift_evidence = gift_identity_from_nft(item, context)
                nid = add_node("nft", nft_address, gift.slug if gift else short(nft_address), item=item)
                if task.parent_id and task.relation:
                    add_edge(task.parent_id, nid, task.relation, task.confidence, task.depth, ["recursive discovery"])
                owner = nft_effective_owner(item) or ""
                if owner:
                    wid = add_node("wallet", owner, short(owner), current_owner=True)
                    add_edge(nid, wid, "CURRENTLY_OWNED_BY", 1.0, task.depth, ["NFT item owner_address"])
                    push("wallet", owner, task.depth + 1, 80, nid, "CURRENTLY_OWNED_BY", 1.0)
                if gift:
                    gid = add_node(
                        "gift",
                        gift.slug,
                        gift.title and f"{gift.title} #{gift.number}" or gift.slug,
                        metadata=asdict(gift),
                    )
                    add_edge(nid, gid, "NFT_METADATA_IDENTIFIES_GIFT", gift_confidence, task.depth, gift_evidence)
                    push("gift", gift.slug, task.depth + 1, 95, nid, "NFT_METADATA_IDENTIFIES_GIFT", gift_confidence)
                if counts["history"] < history_budget:
                    remaining = history_budget - counts["history"]
                    try:
                        rows, _ = self.scanner.get_nft_history(
                            nft_address, min(remaining, self.scanner.transfer_limit or remaining)
                        )
                    except TonCenterError:
                        rows = []
                    events = classify_nft_history(
                        nft_address,
                        rows,
                        trace_lookup=self.scanner.get_trace_by_id if trace_sales else None,
                    )
                    counts["history"] += len(events)
                    self.db.save_nft_history_events(events)
                    timelines[nft_address] = [asdict(x) for x in events]
                    for event in events:
                        eid = add_node(
                            "nft_event",
                            event.event_id,
                            f"{event.event_type} · {event.transaction_time or event.transaction_lt}",
                            **asdict(event),
                        )
                        add_edge(eid, nid, "ASSET", 1.0, task.depth, event.evidence)
                        if event.old_owner:
                            old_id = add_node("wallet", event.old_owner, short(event.old_owner))
                            add_edge(old_id, eid, "FROM", event.confidence, task.depth, event.evidence)
                            push("wallet", event.old_owner, task.depth + 1, 60, eid, "PREVIOUS_OWNER", event.confidence)
                        if event.new_owner:
                            new_id = add_node("wallet", event.new_owner, short(event.new_owner))
                            add_edge(eid, new_id, "TO", event.confidence, task.depth, event.evidence)
                            push("wallet", event.new_owner, task.depth + 1, 62, eid, "NEXT_OWNER", event.confidence)

            elif task.entity_type == "wallet":
                counts["wallets"] += 1
                try:
                    identity = self.scanner.normalize_address(task.entity_id)
                except TonCenterError:
                    continue
                wallet = identity.raw
                wid = add_node("wallet", wallet, short(wallet), normalized=asdict(identity))
                if task.parent_id and task.relation:
                    add_edge(task.parent_id, wid, task.relation, task.confidence, task.depth, ["recursive discovery"])
                try:
                    items, context = self._wallet_nfts(wallet, nfts_per_wallet)
                except TonCenterError:
                    continue
                observations.append({"wallet": wallet, "nft_items_loaded": len(items), "depth": task.depth})
                for item in items:
                    if counts["nfts"] >= nft_budget:
                        break
                    gift, confidence, evidence = gift_identity_from_nft(item, context)
                    if not gift or confidence < 0.40:
                        continue
                    nft_address = str(item.get("address") or item.get("nft_address") or "")
                    if not nft_address:
                        continue
                    nid = add_node("nft", nft_address, gift.slug, item=item)
                    add_edge(wid, nid, "OWNS_GIFT_NFT", 1.0, task.depth, ["NFT owner_address query"])
                    gid = add_node(
                        "gift",
                        gift.slug,
                        gift.title and f"{gift.title} #{gift.number}" or gift.slug,
                        metadata=asdict(gift),
                    )
                    add_edge(nid, gid, "NFT_METADATA_IDENTIFIES_GIFT", confidence, task.depth, evidence)
                    push("nft", nft_address, task.depth + 1, 90, wid, "OWNS_GIFT_NFT", 1.0)
                    push("gift", gift.slug, task.depth + 1, 86, nid, "NFT_METADATA_IDENTIFIES_GIFT", confidence)

        self.db.save_discovery_edges(edges)
        report = {
            "kind": "recursive_investigation",
            "generated_at": utc_now_iso(),
            "seed": {"type": seed_type, "id": seed_id},
            "limits": {
                "max_depth": max_depth,
                "wallet_budget": wallet_budget,
                "nft_budget": nft_budget,
                "history_budget": history_budget,
                "profile_budget": profile_budget,
                "nfts_per_wallet": nfts_per_wallet,
            },
            "counts": counts,
            "nodes": list(nodes.values()),
            "edges": edges,
            "timelines": timelines,
            "observations": observations,
            "graph": {"nodes": list(nodes.values()), "edges": edges},
        }
        report["summary"] = {
            "kind": report["kind"],
            "seed": report["seed"],
            "nodes": len(nodes),
            "edges": len(edges),
            **counts,
        }
        return report

    def _graph_for_nft_report(self, report: Mapping[str, Any]) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        nft = str(report.get("seed"))
        nodes.append({"id": f"nft:{nft}", "type": "nft", "label": short(nft), "details": report.get("nft_item")})
        gift = report.get("public_gift") or report.get("gift_from_metadata")
        if isinstance(gift, Mapping) and gift.get("slug"):
            gid = f"gift:{gift['slug']}"
            nodes.append({"id": gid, "type": "gift", "label": str(gift.get("title") or gift["slug"]), "details": gift})
            edges.append(
                {
                    "source": f"nft:{nft}",
                    "target": gid,
                    "relation": "NFT_METADATA_IDENTIFIES_GIFT",
                    "confidence": float(gift.get("confidence") or 0.5),
                    "evidence": gift.get("evidence") or [],
                }
            )
            for profile in gift.get("public_profiles") or []:
                pid = f"telegram_profile:{profile}"
                nodes.append({"id": pid, "type": "telegram_profile", "label": profile, "details": {"public": True}})
                edges.append(
                    {
                        "source": gid,
                        "target": pid,
                        "relation": "PUBLICLY_DISPLAYED_BY",
                        "confidence": 0.75,
                        "evidence": ["public collectible page"],
                    }
                )
        for event in report.get("history") or []:
            eid = f"nft_event:{event['event_id']}"
            nodes.append(
                {
                    "id": eid,
                    "type": "nft_event",
                    "label": f"{event['event_type']} · {event.get('transaction_time') or event.get('transaction_lt')}",
                    "details": event,
                }
            )
            edges.append(
                {
                    "source": eid,
                    "target": f"nft:{nft}",
                    "relation": "ASSET",
                    "confidence": 1.0,
                    "evidence": event.get("evidence") or [],
                }
            )
            for key, relation in (("old_owner", "FROM"), ("new_owner", "TO")):
                owner = event.get(key)
                if owner:
                    oid = f"wallet:{owner}"
                    nodes.append({"id": oid, "type": "wallet", "label": short(owner), "details": {}})
                    if relation == "FROM":
                        edges.append(
                            {
                                "source": oid,
                                "target": eid,
                                "relation": relation,
                                "confidence": event.get("confidence", 1),
                                "evidence": event.get("evidence") or [],
                            }
                        )
                    else:
                        edges.append(
                            {
                                "source": eid,
                                "target": oid,
                                "relation": relation,
                                "confidence": event.get("confidence", 1),
                                "evidence": event.get("evidence") or [],
                            }
                        )
        unique_nodes = {x["id"]: x for x in nodes}
        return {"nodes": list(unique_nodes.values()), "edges": edges}

    def _graph_for_gift_report(self, report: Mapping[str, Any]) -> dict[str, Any]:
        gift = report.get("gift") or {}
        gid = f"gift:{gift.get('slug')}"
        nodes = [{"id": gid, "type": "gift", "label": gift.get("title") or gift.get("slug"), "details": gift}]
        edges = []
        for profile in gift.get("public_profiles") or []:
            pid = f"telegram_profile:{profile}"
            nodes.append({"id": pid, "type": "telegram_profile", "label": profile, "details": {"public": True}})
            edges.append(
                {
                    "source": gid,
                    "target": pid,
                    "relation": "PUBLICLY_DISPLAYED_BY",
                    "confidence": 0.75,
                    "evidence": ["public collectible page"],
                }
            )
        for match in report.get("matches") or []:
            nid = f"nft:{match.get('nft_address')}"
            nodes.append({"id": nid, "type": "nft", "label": short(str(match.get("nft_address"))), "details": match})
            edges.append(
                {
                    "source": gid,
                    "target": nid,
                    "relation": "MATCHED_TO_NFT_ITEM",
                    "confidence": match.get("confidence", 0),
                    "evidence": match.get("evidence") or [],
                }
            )
        nested = (report.get("nft_report") or {}).get("graph") or {}
        nodes.extend(nested.get("nodes") or [])
        edges.extend(nested.get("edges") or [])
        return {"nodes": list({x["id"]: x for x in nodes}.values()), "edges": edges}
