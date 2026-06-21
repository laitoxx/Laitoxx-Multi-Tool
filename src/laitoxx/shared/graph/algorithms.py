"""
algorithms.py — NetworkX-based graph algorithms for the Laitoxx Graph Editor.
Provides shortest path finding and node centrality calculations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from laitoxx.shared.graph.model import Graph


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
