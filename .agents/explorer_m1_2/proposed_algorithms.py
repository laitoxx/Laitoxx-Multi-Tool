import networkx as nx
from laitoxx.shared.graph.model import Graph

def _build_nx_graph(graph: Graph, directed: bool = False) -> nx.Graph | nx.DiGraph:
    """Helper to convert Laitoxx Graph to NetworkX Graph."""
    nx_g = nx.DiGraph() if directed else nx.Graph()
    for node in graph.nodes:
        nx_g.add_node(node.id)
    for edge in graph.edges:
        if graph.get_node(edge.source_id) and graph.get_node(edge.target_id):
            nx_g.add_edge(edge.source_id, edge.target_id)
    return nx_g

def get_shortest_path(graph: Graph, source_id: str, target_id: str) -> list[str]:
    """
    Find shortest path between source_id and target_id using NetworkX.
    Returns list of node IDs, or empty list if no path exists or nodes don't exist.
    Calculated as undirected path.
    """
    nx_g = _build_nx_graph(graph, directed=False)
    if source_id not in nx_g or target_id not in nx_g:
        return []
    try:
        path = nx.shortest_path(nx_g, source=source_id, target=target_id)
        return list(path)
    except nx.NetworkXNoPath:
        return []
    except Exception:
        return []

def calculate_centralities(graph: Graph, metric: str = "degree") -> dict[str, float]:
    """
    Calculate node centralities using NetworkX.
    Supports: "degree", "betweenness", "closeness", "eigenvector".
    Returns a dict mapping node ID -> centrality value.
    If eigenvector centrality fails to converge, falls back to degree centrality.
    """
    nx_g = _build_nx_graph(graph, directed=False)
    if not nx_g.nodes:
        return {}

    metric = (metric or "degree").strip().lower()
    try:
        if metric == "degree":
            centrality = nx.degree_centrality(nx_g)
        elif metric == "betweenness":
            centrality = nx.betweenness_centrality(nx_g)
        elif metric == "closeness":
            centrality = nx.closeness_centrality(nx_g)
        elif metric == "eigenvector":
            try:
                centrality = nx.eigenvector_centrality(nx_g, max_iter=1000)
            except nx.PowerIterationFailedConvergence:
                # Fallback to degree centrality on convergence failure
                centrality = nx.degree_centrality(nx_g)
        else:
            centrality = nx.degree_centrality(nx_g)
            
        result = {}
        for node in graph.nodes:
            result[node.id] = centrality.get(node.id, 0.0)
        return result
    except Exception:
        return {node.id: 0.0 for node in graph.nodes}
