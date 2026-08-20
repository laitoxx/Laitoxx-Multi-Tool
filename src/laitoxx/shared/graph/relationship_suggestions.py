"""Explainable, local relationship inference for OSINT graph entities."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from laitoxx.shared.graph.model import Edge, Graph, Node


@dataclass(frozen=True)
class RelationshipSuggestion:
    source_id: str
    target_id: str
    label: str
    edge_type: str
    confidence: float
    reason: str


def _domain(node: Node) -> str:
    value = node.label.strip().lower()
    if node.node_type == "Email" and "@" in value:
        return value.rsplit("@", 1)[1]
    if node.node_type == "Website":
        if "://" in value:
            return urlparse(value).hostname or value
        return value.split("/", 1)[0]
    return ""


def suggest_relationships(graph: Graph) -> list[RelationshipSuggestion]:
    suggestions = []
    existing = {(edge.source_id, edge.target_id, edge.label) for edge in graph.edges}
    for source in graph.nodes:
        source_domain = _domain(source)
        for target in graph.nodes:
            if source.id == target.id:
                continue
            target_domain = _domain(target)
            suggestion = None
            if source.node_type == "Email" and target.node_type == "Website" and source_domain == target_domain:
                suggestion = RelationshipSuggestion(
                    source.id, target.id, "uses domain", "RelatedTo", 0.98, "Email domain equals website domain"
                )
            elif source.node_type == "Website" and target.node_type == "Website" and source_domain and target_domain:
                if source_domain != target_domain and source_domain.endswith("." + target_domain):
                    suggestion = RelationshipSuggestion(
                        source.id, target.id, "subdomain of", "RelatedTo", 0.97, "Hostname is a subdomain"
                    )
            elif source.node_type == "Username" and target.node_type == "SocialAccount":
                if source.label.casefold().lstrip("@") in target.label.casefold():
                    suggestion = RelationshipSuggestion(
                        source.id, target.id, "registered on", "RegisteredOn", 0.85, "Account label contains username"
                    )
            if suggestion and (suggestion.source_id, suggestion.target_id, suggestion.label) not in existing:
                suggestions.append(suggestion)
    unique = {(item.source_id, item.target_id, item.label): item for item in suggestions}
    return sorted(unique.values(), key=lambda item: item.confidence, reverse=True)


def apply_suggestions(graph: Graph, suggestions: list[RelationshipSuggestion]) -> int:
    added = 0
    for item in suggestions:
        edge = Edge(
            source_id=item.source_id,
            target_id=item.target_id,
            label=item.label,
            edge_type=item.edge_type,
            metadata={"confidence": f"{item.confidence:.2f}", "reason": item.reason},
        )
        if graph.add_edge(edge):
            added += 1
    return added
