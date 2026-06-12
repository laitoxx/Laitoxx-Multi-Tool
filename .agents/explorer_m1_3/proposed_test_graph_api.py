"""
test_graph_api.py - Unit tests for the Graph API, Entity Resolution, and NetworkX integration.
"""
import pytest
from laitoxx.shared.graph.model import Graph, Node, Edge
from laitoxx.shared.graph.entity_resolution import EntityResolver
from laitoxx.shared.graph.algorithms import get_shortest_path, calculate_centralities

def test_temporal_fields_serialization():
    # Node serialization
    node = Node(
        label="Test Node",
        node_type="Person",
        valid_from="2026-01-01T00:00:00Z",
        valid_to="2026-12-31T23:59:59Z"
    )
    d_node = node.to_dict()
    assert d_node["valid_from"] == "2026-01-01T00:00:00Z"
    assert d_node["valid_to"] == "2026-12-31T23:59:59Z"

    node_loaded = Node.from_dict(d_node)
    assert node_loaded.valid_from == "2026-01-01T00:00:00Z"
    assert node_loaded.valid_to == "2026-12-31T23:59:59Z"

    # Edge serialization
    edge = Edge(
        source_id="N1",
        target_id="N2",
        valid_from="2026-02-01T00:00:00Z",
        valid_to="2026-11-30T23:59:59Z"
    )
    d_edge = edge.to_dict()
    assert d_edge["valid_from"] == "2026-02-01T00:00:00Z"
    assert d_edge["valid_to"] == "2026-11-30T23:59:59Z"

    edge_loaded = Edge.from_dict(d_edge)
    assert edge_loaded.valid_from == "2026-02-01T00:00:00Z"
    assert edge_loaded.valid_to == "2026-11-30T23:59:59Z"


def test_merge_nodes():
    g = Graph()
    n1 = Node(id="N1", label="Primary Node", description="Desc 1", metadata={"key1": "val1", "key2": "val2"})
    n2 = Node(id="N2", label="Duplicate A", description="Desc 2", metadata={"key2": "val2_new", "key3": "val3"})
    n3 = Node(id="N3", label="Duplicate B", description="", metadata={"key4": "val4"})

    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)

    # Add edges
    e1 = Edge(id="E1", source_id="N2", target_id="N4", label="linked", edge_type="Connected")
    n4 = Node(id="N4", label="Other")
    g.add_node(n4)
    g.add_edge(e1)

    e2 = Edge(id="E2", source_id="N3", target_id="N4", label="linked", edge_type="Connected")
    g.add_edge(e2)

    # Merge nodes N2 and N3 into N1
    g.merge_nodes("N1", ["N2", "N3"])

    # Check node removal
    assert g.get_node("N2") is None
    assert g.get_node("N3") is None
    assert g.get_node("N1") is not None

    # Check description combination
    assert "Desc 1" in n1.description
    assert "Desc 2" in n1.description

    # Check metadata combination
    assert n1.metadata["key1"] == "val1"
    assert "val2" in n1.metadata["key2"]
    assert "val2_new" in n1.metadata["key2"]
    assert n1.metadata["key3"] == "val3"
    assert n1.metadata["key4"] == "val4"

    # Check edge re-routing and deduplication
    assert len(g.edges) == 1
    remaining_edge = g.edges[0]
    assert remaining_edge.source_id == "N1"
    assert remaining_edge.target_id == "N4"


def test_entity_resolver_compute_similarity():
    # 1. Type mismatch -> 0.0
    n1 = Node(label="Alice", node_type="Person")
    n2 = Node(label="Alice", node_type="Company")
    assert EntityResolver.compute_similarity(n1, n2) == 0.0

    # 2. Exact match -> 1.0
    n3 = Node(label="Alice Smith", node_type="Person")
    n4 = Node(label="alice smith ", node_type="Person")
    assert EntityResolver.compute_similarity(n3, n4) == 1.0

    # 3. High similarity labels
    n5 = Node(label="Alice Smith", node_type="Person")
    n6 = Node(label="Alice Smyth", node_type="Person")
    sim = EntityResolver.compute_similarity(n5, n6)
    assert 0.7 < sim < 1.0

    # 4. Metadata boost logic
    n7 = Node(label="Alice", node_type="Person", metadata={"Phone": "+12345"})
    n8 = Node(label="Bob", node_type="Person", metadata={"phone": " +12345 "})
    assert EntityResolver.compute_similarity(n7, n8) >= 0.95


def test_entity_resolver_find_duplicates():
    g = Graph()
    n1 = Node(id="N1", label="Alice", node_type="Person")
    n2 = Node(id="N2", label="Alice Smith", node_type="Person")
    n3 = Node(id="N3", label="Bob", node_type="Person")
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)

    dups = EntityResolver.find_duplicates(g, 0.5)
    assert len(dups) >= 1
    assert dups[0]["similarity"] >= 0.5


def test_networkx_shortest_path():
    g = Graph()
    n1 = Node(id="N1", label="A")
    n2 = Node(id="N2", label="B")
    n3 = Node(id="N3", label="C")
    n4 = Node(id="N4", label="D")
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)
    g.add_node(n4)

    g.add_edge(Edge(source_id="N1", target_id="N2"))
    g.add_edge(Edge(source_id="N2", target_id="N3"))

    # Path from N1 to N3
    path = get_shortest_path(g, "N1", "N3")
    assert path == ["N1", "N2", "N3"]

    # Disconnected path from N1 to N4
    path2 = get_shortest_path(g, "N1", "N4")
    assert path2 == []

    # Non-existent node path
    path3 = get_shortest_path(g, "N1", "N99")
    assert path3 == []


def test_networkx_centralities():
    g = Graph()
    n1 = Node(id="N1", label="A")
    n2 = Node(id="N2", label="B")
    n3 = Node(id="N3", label="C")
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)

    g.add_edge(Edge(source_id="N1", target_id="N2"))
    g.add_edge(Edge(source_id="N2", target_id="N3"))

    cents = calculate_centralities(g, "degree")
    assert cents["N2"] > cents["N1"]
    assert cents["N2"] > cents["N3"]

    # Test empty graph
    empty_g = Graph()
    assert calculate_centralities(empty_g) == {}
