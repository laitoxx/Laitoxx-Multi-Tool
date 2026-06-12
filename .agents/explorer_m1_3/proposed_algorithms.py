"""
algorithms.py - NetworkX algorithms integration for shortest path and centralities.
"""
import networkx as nx
from typing import List, Dict
from laitoxx.shared.graph.model import Graph

def _build_networkx_graph(graph: Graph) -> nx.Graph:
    """
    Helper function to convert the internal Graph model to a NetworkX Graph.
    """
    g = nx.Graph()
    for node in graph.nodes:
        g.add_node(node.id)
    for edge in graph.edges:
        # Avoid adding edges for non-existent nodes in networkx representation
        if g.has_node(edge.source_id) and g.has_node(edge.target_id):
            g.add_edge(edge.source_id, edge.target_id)
    return g

def get_shortest_path(graph: Graph, source_id: str, target_id: str) -> List[str]:
    """
    Finds the shortest path between source_id and target_id.
    Returns a list of node IDs forming the path. If no path exists, returns an empty list.
    """
    g = _build_networkx_graph(graph)
    if source_id not in g or target_id not in g:
        return []
    try:
        return nx.shortest_path(g, source=source_id, target=target_id)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []

def calculate_centralities(graph: Graph, metric: str = "degree") -> Dict[str, float]:
    """
    Calculates the centrality values for all nodes in the graph based on the specified metric.
    Supported metrics:
      - 'degree': Degree centrality
      - 'betweenness': Betweenness centrality
      - 'closeness': Closeness centrality
      - 'eigenvector': Eigenvector centrality (with fallback to degree centrality if convergence fails)
    Returns a dictionary mapping node IDs to their centrality score.
    """
    g = _build_networkx_graph(graph)
    if not g.nodes:
        return {}

    metric = metric.lower().strip()
    if metric == "degree":
        return nx.degree_centrality(g)
    elif metric == "betweenness":
        return nx.betweenness_centrality(g)
    elif metric == "closeness":
        return nx.closeness_centrality(g)
    elif metric == "eigenvector":
        try:
            return nx.eigenvector_centrality(g, max_iter=1000)
        except Exception:
            # Fallback to degree centrality if eigenvector calculation fails to converge
            return nx.degree_centrality(g)
    else:
        # Default fallback
        return nx.degree_centrality(g)
