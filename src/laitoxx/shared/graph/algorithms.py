"""
algorithms.py - NetworkX-based graph algorithms for the Laitoxx Graph Editor.
Provides shortest path finding and node centrality calculations.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from laitoxx.shared.graph.model import Graph
from .layout_algorithms import (
    _network_from_graph,
)
from .layout_algorithms import (
    calculate_cluster_layout as calculate_cluster_layout,
)
from .layout_algorithms import (
    detect_graph_communities as detect_graph_communities,
)


def find_relevant_connections(
    graph: Graph,
    mode: str,
    *,
    limit: int = 12,
) -> dict[str, object]:
    """Return a compact subgraph useful for common OSINT analysis pivots."""
    network = _network_from_graph(graph, max_nodes=1000, max_edges=4000)
    if not network:
        return {"nodes": [], "edges": [], "summary": "Graph is empty"}
    edges_by_pair: dict[frozenset[str], list] = {}
    edges_by_node: dict[str, list] = {identifier: [] for identifier in network}
    valid_edges = []
    for edge in graph.edges:
        if edge.source_id in network and edge.target_id in network and edge.source_id != edge.target_id:
            valid_edges.append(edge)
            edges_by_pair.setdefault(frozenset((edge.source_id, edge.target_id)), []).append(edge)
            edges_by_node[edge.source_id].append(edge)
            edges_by_node[edge.target_id].append(edge)

    def edge_score(edge) -> float:
        metadata = edge.metadata or {}
        try:
            confidence = float(metadata.get("confidence") or 0)
            confidence = confidence / 100 if confidence > 1 else confidence
        except (TypeError, ValueError):
            confidence = 0.0
        try:
            count = float(metadata.get("count") or 0)
        except (TypeError, ValueError):
            count = 0.0
        try:
            amount = abs(float(metadata.get("total_ton") or metadata.get("amount_ton") or 0))
        except (TypeError, ValueError):
            amount = 0.0
        return confidence * 4 + math.log1p(count) + math.log1p(amount) * 0.35 + 1.0

    selected_nodes: set[str] = set()
    selected_edges: set[str] = set()
    summary = ""
    if mode == "bridges":
        articulation = set(nx.articulation_points(network))
        bridge_pairs = list(nx.bridges(network))
        bridge_pairs.sort(key=lambda pair: -(network.degree(pair[0]) + network.degree(pair[1])))
        selected_nodes.update(sorted(articulation, key=lambda item: -network.degree(item))[:limit])
        for source, target in bridge_pairs[:limit]:
            selected_nodes.update((source, target))
            selected_edges.update(edge.id for edge in edges_by_pair.get(frozenset((source, target)), [])[:1])
        summary = f"{len(articulation)} articulation nodes · {len(bridge_pairs)} bridge links"
    elif mode == "strong":
        strongest = sorted(valid_edges, key=lambda edge: (-edge_score(edge), edge.id))[:limit]
        selected_edges.update(edge.id for edge in strongest)
        for edge in strongest:
            selected_nodes.update((edge.source_id, edge.target_id))
        summary = f"Top {len(strongest)} evidence-weighted links"
    elif mode == "target_paths":
        target = next(
            (node.id for node in graph.nodes if node.id in network and node.metadata.get("is_target")),
            max(network, key=network.degree),
        )
        interesting_types = {
            "Vulnerability",
            "Database",
            "AdminPanel",
            "RemoteAccess",
            "TelegramProfile",
            "TelegramGift",
            "Username",
            "PhoneNumber",
        }
        node_by_id = {node.id: node for node in graph.nodes}
        candidates = sorted(
            (identifier for identifier in network if identifier != target),
            key=lambda identifier: (
                0 if node_by_id[identifier].node_type in interesting_types else 1,
                -network.degree(identifier),
                identifier,
            ),
        )[:limit]
        selected_nodes.add(target)
        reached = 0
        for candidate in candidates:
            try:
                path = nx.shortest_path(network, target, candidate)
            except nx.NetworkXNoPath:
                continue
            reached += 1
            selected_nodes.update(path)
            for source, destination in zip(path, path[1:], strict=False):
                selected_edges.update(edge.id for edge in edges_by_pair.get(frozenset((source, destination)), [])[:1])
        summary = f"Routes from target to {reached} relevant entities"
    else:  # hubs
        degree = nx.degree_centrality(network)
        sample = min(64, len(network))
        betweenness = nx.betweenness_centrality(
            network,
            k=sample if sample < len(network) else None,
            seed=42,
        )
        ranked = sorted(
            network,
            key=lambda identifier: (-(degree[identifier] + betweenness[identifier] * 2), identifier),
        )[:limit]
        selected_nodes.update(ranked)
        for identifier in ranked:
            incident = sorted(
                edges_by_node[identifier],
                key=lambda edge: (-edge_score(edge), edge.id),
            )[:3]
            selected_edges.update(edge.id for edge in incident)
            for edge in incident:
                selected_nodes.update((edge.source_id, edge.target_id))
        summary = f"Top {len(ranked)} connectors by degree and betweenness"
    return {
        "nodes": sorted(selected_nodes),
        "edges": sorted(selected_edges),
        "summary": summary,
    }


def get_shortest_path(graph: Graph, source_id: str, target_id: str) -> list[str]:
    """
    Find the shortest path between source_id and target_id using NetworkX.
    Treats the graph as undirected to represent connectivity in general OSINT analysis.
    Returns a list of node IDs forming the path. If no path is found, returns an empty list.
    """
    G = nx.Graph()
    node_ids = {node.id for node in graph.nodes}
    for node in graph.nodes:
        G.add_node(node.id)
    for edge in graph.edges:
        if edge.source_id in node_ids and edge.target_id in node_ids:
            G.add_edge(edge.source_id, edge.target_id)

    try:
        path = nx.shortest_path(G, source=source_id, target=target_id)
        return path
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []


def calculate_centralities(graph: Graph, metric: str = "degree") -> dict[str, float]:
    """
    Calculate node centralities for nodes in the graph.
    Supported metrics:
    - 'degree': Degree Centrality (default)
    - 'betweenness': Betweenness Centrality
    - 'closeness': Closeness Centrality
    - 'eigenvector': Eigenvector Centrality (falls back to degree if convergence fails)

    Returns a dictionary mapping node IDs to their centrality scores.
    """
    G = nx.Graph()
    node_ids = {node.id for node in graph.nodes}
    for node in graph.nodes:
        G.add_node(node.id)
    for edge in graph.edges:
        if edge.source_id in node_ids and edge.target_id in node_ids:
            G.add_edge(edge.source_id, edge.target_id)

    if metric == "degree":
        return nx.degree_centrality(G)
    elif metric == "betweenness":
        return nx.betweenness_centrality(G)
    elif metric == "closeness":
        return nx.closeness_centrality(G)
    elif metric == "eigenvector":
        try:
            return nx.eigenvector_centrality(G, max_iter=1000)
        except nx.PowerIterationFailedConvergence:
            # Fallback to degree centrality if convergence fails in power iteration
            return nx.degree_centrality(G)
    else:
        raise ValueError(f"Unsupported centrality metric: '{metric}'")
