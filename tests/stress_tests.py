"""
stress_tests.py — Robustness, boundary and stress tests for Laitoxx Graph Editor backend.
"""
from __future__ import annotations

import time
from laitoxx.shared.graph.model import Node, Edge, Graph
from laitoxx.shared.graph.entity_resolution import EntityResolver
from laitoxx.shared.graph.algorithms import get_shortest_path, calculate_centralities

def test_merge_nodes_non_string_metadata():
    """Test merging nodes where metadata values are not strings (e.g. integers, floats, lists)."""
    g = Graph("Metadata Stress")
    n_primary = Node(id="P", label="Primary", node_type="Person", metadata={"age": 30, "score": 9.5})
    n_dup = Node(id="D", label="Dup", node_type="Person", metadata={"age": 31, "score": 10.0})
    
    g.add_node(n_primary)
    g.add_node(n_dup)
    
    # This might fail with AttributeError if it tries to split on an integer or float
    try:
        g.merge_nodes("P", ["D"])
        print("SUCCESS: merge_nodes handled non-string metadata values.")
        # Let's verify what the merged values are
        print("Merged metadata:", g.get_node("P").metadata)
    except Exception as e:
        print(f"FAILED: merge_nodes crashed on non-string metadata: {type(e).__name__}: {e}")

def test_merge_nodes_invalid_dates():
    """Test merging nodes with malformed or mixed date formats."""
    g = Graph("Dates Stress")
    n1 = Node(id="N1", label="N1", valid_from="2026-01-01T12:00:00Z", valid_to="2026-05-01")
    n2 = Node(id="N2", label="N2", valid_from="invalid-date", valid_to="2026-06-01T15:00:00Z")
    n3 = Node(id="N3", label="N3", valid_from="2025-12-31", valid_to="N/A")
    
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)
    
    g.merge_nodes("N1", ["N2", "N3"])
    
    node = g.get_node("N1")
    print("Merged dates:")
    print("  valid_from:", repr(node.valid_from))
    print("  valid_to:", repr(node.valid_to))

def test_dangling_edges_in_algorithms():
    """Test NetworkX algorithms when there are dangling edges referencing non-existent node IDs."""
    g = Graph("Dangling Edge Graph")
    n1 = Node(id="N1", label="N1")
    n2 = Node(id="N2", label="N2")
    g.add_node(n1)
    g.add_node(n2)
    
    # Edge referencing non-existent nodes N3 and N4
    # Since we can't add it via add_edge (which returns False), we add it directly to edges list
    dangling_edge = Edge(source_id="N3", target_id="N4")
    g.edges.append(dangling_edge)
    
    # Also add edge from N1 to N3 (dangling)
    g.edges.append(Edge(source_id="N1", target_id="N3"))
    
    # 1. Shortest path to a dangling node
    path = get_shortest_path(g, "N1", "N4")
    print("Shortest path N1 -> N4:", path)
    
    # 2. Centrality calculation
    centralities = calculate_centralities(g, metric="degree")
    print("Centralities with dangling nodes:")
    for nid, val in centralities.items():
        print(f"  {nid}: {val}")

def test_similarity_extremely_long_strings():
    """Stress test SequenceMatcher performance with very large description/metadata strings."""
    n1 = Node(label="Alice", node_type="Person", description="A" * 5000)
    n2 = Node(label="Bob", node_type="Person", description="A" * 4999 + "B")
    
    t0 = time.perf_counter()
    sim = EntityResolver.compute_similarity(n1, n2)
    t1 = time.perf_counter()
    print(f"Similarity of 5000-char descriptions: {sim:.4f} (took {t1 - t0:.4f} seconds)")

def test_find_duplicates_scalability():
    """Measure performance of duplicate detection on a moderate number of nodes (e.g. 500)."""
    g = Graph()
    for i in range(500):
        g.add_node(Node(id=f"Node_{i}", label=f"User {i}", node_type="Person", description=f"Desc {i}"))
        
    t0 = time.perf_counter()
    dups = EntityResolver.find_duplicates(g, threshold=0.8)
    t1 = time.perf_counter()
    print(f"find_duplicates on 500 nodes took {t1 - t0:.4f} seconds. Found {len(dups)} duplicates.")

if __name__ == "__main__":
    print("--- Running Stress Tests ---")
    test_merge_nodes_non_string_metadata()
    print()
    test_merge_nodes_invalid_dates()
    print()
    test_dangling_edges_in_algorithms()
    print()
    test_similarity_extremely_long_strings()
    print()
    test_find_duplicates_scalability()
