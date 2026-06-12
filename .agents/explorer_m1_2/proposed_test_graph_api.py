import os
import tempfile
import pytest

from laitoxx.shared.graph.model import Node, Edge, Graph
from laitoxx.shared.graph.entity_resolution import EntityResolver
from laitoxx.shared.graph.algorithms import get_shortest_path, calculate_centralities

def test_temporal_serialization():
    # 1. Create nodes and edge with temporal bounds
    n1 = Node(label="Alice", node_type="Person", valid_from="2020-01-01", valid_to="2025-12-31")
    n2 = Node(label="Bob", node_type="Person", valid_from="2021-06-01")
    edge = Edge(
        source_id=n1.id, 
        target_id=n2.id, 
        label="Connected", 
        valid_from="2021-06-01", 
        valid_to="2024-01-01"
    )

    assert n1.valid_from == "2020-01-01"
    assert n1.valid_to == "2025-12-31"
    assert n2.valid_to is None
    assert edge.valid_from == "2021-06-01"
    assert edge.valid_to == "2024-01-01"

    # 2. Test serialization (to_dict)
    n1_dict = n1.to_dict()
    assert n1_dict["valid_from"] == "2020-01-01"
    assert n1_dict["valid_to"] == "2025-12-31"

    edge_dict = edge.to_dict()
    assert edge_dict["valid_from"] == "2021-06-01"
    assert edge_dict["valid_to"] == "2024-01-01"

    # 3. Test deserialization (from_dict)
    n1_copy = Node.from_dict(n1_dict)
    assert n1_copy.valid_from == "2020-01-01"
    assert n1_copy.valid_to == "2025-12-31"
    assert n1_copy.id == n1.id

    edge_copy = Edge.from_dict(edge_dict)
    assert edge_copy.valid_from == "2021-06-01"
    assert edge_copy.valid_to == "2024-01-01"
    assert edge_copy.id == edge.id

    # 4. JSON Roundtrip check
    g = Graph()
    g.add_node(n1)
    g.add_node(n2)
    g.add_edge(edge)

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_graph.json")
        g.save_json(filepath)

        g_loaded = Graph.load_json(filepath)
        n1_loaded = g_loaded.get_node(n1.id)
        edge_loaded = g_loaded.get_edge(edge.id)

        assert n1_loaded is not None
        assert n1_loaded.valid_from == "2020-01-01"
        assert n1_loaded.valid_to == "2025-12-31"
        assert edge_loaded is not None
        assert edge_loaded.valid_from == "2021-06-01"
        assert edge_loaded.valid_to == "2024-01-01"


def test_merge_nodes_attributes():
    g = Graph()
    
    # Primary node
    p = Node(
        id="primary", 
        label="John Doe", 
        node_type="Person", 
        description="Lead developer.", 
        metadata={"email": "john.doe@company.com", "role": "admin"},
        valid_from="2020-01-01",
        valid_to="2025-01-01"
    )
    # Duplicate node 1
    d1 = Node(
        id="dup1", 
        label="John Doe Jr.", 
        node_type="Person", 
        description="Works on Multi-Tool.", 
        metadata={"phone": "123456", "email": "john.doe.alternate@company.com"},
        valid_from="2019-06-01",
        valid_to="2024-12-31"
    )
    # Duplicate node 2
    d2 = Node(
        id="dup2", 
        label="J. Doe", 
        node_type="Person", 
        description="Lead developer.",  # duplicate description, should not be duplicated in final
        metadata={"country": "USA"},
        valid_from="2021-01-01",
        valid_to="2026-06-01"
    )

    g.add_node(p)
    g.add_node(d1)
    g.add_node(d2)

    g.merge_nodes("primary", ["dup1", "dup2"])

    # Verify duplicates are removed and primary remains
    assert len(g.nodes) == 1
    assert g.get_node("primary") is not None
    assert g.get_node("dup1") is None
    assert g.get_node("dup2") is None

    # Verify descriptions are concatenated without duplicate content
    expected_desc = "Lead developer.\nWorks on Multi-Tool."
    assert p.description == expected_desc

    # Verify metadata is merged (with primary taking precedence for 'email')
    assert p.metadata["email"] == "john.doe@company.com"
    assert p.metadata["role"] == "admin"
    assert p.metadata["phone"] == "123456"
    assert p.metadata["country"] == "USA"

    # Verify temporal bounds are merged correctly
    # valid_from: min("2020-01-01", "2019-06-01", "2021-01-01") -> "2019-06-01"
    # valid_to: max("2025-01-01", "2024-12-31", "2026-06-01") -> "2026-06-01"
    assert p.valid_from == "2019-06-01"
    assert p.valid_to == "2026-06-01"


def test_merge_nodes_reroute_and_deduplicate_edges():
    g = Graph()
    
    p = Node(id="primary", label="Primary", node_type="Person")
    d = Node(id="dup", label="Duplicate", node_type="Person")
    other1 = Node(id="other1", label="Other 1", node_type="Website")
    other2 = Node(id="other2", label="Other 2", node_type="Email")
    
    g.add_node(p)
    g.add_node(d)
    g.add_node(other1)
    g.add_node(other2)

    # Edge from primary to other1
    e1 = Edge(source_id="primary", target_id="other1", label="visits", edge_type="Connected", valid_from="2020-01-01")
    # Edge from dup to other1 (should be re-routed to primary and deduplicated with e1)
    e2 = Edge(source_id="dup", target_id="other1", label="visits", edge_type="Connected", valid_from="2019-01-01", metadata={"browser": "Chrome"})
    # Edge from dup to other2 (should be re-routed, but NOT deduplicated since targets differ)
    e3 = Edge(source_id="dup", target_id="other2", label="owns", edge_type="Connected")

    g.add_edge(e1)
    g.add_edge(e2)
    g.add_edge(e3)

    g.merge_nodes("primary", ["dup"])

    # Verify edges list size (e2 is deduplicated/removed, leaving e1 and e3 re-routed)
    assert len(g.edges) == 2
    
    # Verify e1 has merged attributes from e2
    assert e1.source_id == "primary"
    assert e1.target_id == "other1"
    assert e1.valid_from == "2019-01-01"  # min of 2020 and 2019
    assert e1.metadata["browser"] == "Chrome"

    # Verify e3 is re-routed
    assert e3.source_id == "primary"
    assert e3.target_id == "other2"


def test_compute_similarity():
    # 1. Test different node types
    n_person = Node(label="Alice Smith", node_type="Person")
    n_email = Node(label="Alice Smith", node_type="Email")
    assert EntityResolver.compute_similarity(n_person, n_email) == 0.0

    # 2. Test exact match
    n_p1 = Node(label="John Doe", node_type="Person", description="A coder", metadata={"ip": "1.1.1.1"})
    n_p2 = Node(label="John Doe", node_type="Person", description="A coder", metadata={"ip": "1.1.1.1"})
    assert EntityResolver.compute_similarity(n_p1, n_p2) == 1.0

    # 3. Test slight differences
    n_p3 = Node(label="Jon Doe", node_type="Person")
    sim = EntityResolver.compute_similarity(n_p1, n_p3)
    assert 0.5 < sim < 1.0  # partial match due to diff in name and lack of other fields

    # 4. Test distinct names
    n_p4 = Node(label="Jane Miller", node_type="Person")
    assert EntityResolver.compute_similarity(n_p1, n_p4) < 0.3


def test_find_duplicates():
    g = Graph()
    n1 = Node(label="John Doe", node_type="Person")
    n2 = Node(label="Jon Doe", node_type="Person")
    n3 = Node(label="Jane Doe", node_type="Person")
    n4 = Node(label="John Doe", node_type="Email")  # different type

    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)
    g.add_node(n4)

    # Find duplicates with low threshold
    dups = EntityResolver.find_duplicates(g, threshold=0.7)
    
    # n1 ("John Doe") vs n2 ("Jon Doe") should be detected
    # n1 vs n3 ("Jane Doe") might be lower
    # n4 must not be in duplicates since types differ
    assert len(dups) >= 1
    
    # Verify shape of returning list
    first_dup = dups[0]
    assert "node1" in first_dup
    assert "node2" in first_dup
    assert "similarity" in first_dup
    assert first_dup["similarity"] >= 0.7
    
    # Ensure types are matching
    assert first_dup["node1"].node_type == first_dup["node2"].node_type


def test_get_shortest_path():
    g = Graph()
    n_a = Node(id="A", label="A")
    n_b = Node(id="B", label="B")
    n_c = Node(id="C", label="C")
    n_d = Node(id="D", label="D")
    
    g.add_node(n_a)
    g.add_node(n_b)
    g.add_node(n_c)
    g.add_node(n_d)

    # A -> B -> C
    g.add_edge(Edge(source_id="A", target_id="B"))
    g.add_edge(Edge(source_id="B", target_id="C"))

    # Test existing path
    path = get_shortest_path(g, "A", "C")
    assert path == ["A", "B", "C"]

    # Test disconnected path
    path2 = get_shortest_path(g, "A", "D")
    assert path2 == []

    # Test missing node
    path3 = get_shortest_path(g, "A", "NONEXISTENT")
    assert path3 == []


def test_calculate_centralities():
    g = Graph()
    
    # Build a star graph: Center 'C' connected to L1, L2, L3
    n_c = Node(id="C", label="Center")
    n_l1 = Node(id="L1", label="Leaf 1")
    n_l2 = Node(id="L2", label="Leaf 2")
    n_l3 = Node(id="L3", label="Leaf 3")

    g.add_node(n_c)
    g.add_node(n_l1)
    g.add_node(n_l2)
    g.add_node(n_l3)

    g.add_edge(Edge(source_id="C", target_id="L1"))
    g.add_edge(Edge(source_id="C", target_id="L2"))
    g.add_edge(Edge(source_id="C", target_id="L3"))

    centralities = calculate_centralities(g, metric="degree")

    # Center node has degree 3/3 = 1.0, leaf nodes have degree 1/3 = 0.333
    assert centralities["C"] == 1.0
    assert pytest.approx(centralities["L1"], 0.01) == 0.333
    assert pytest.approx(centralities["L2"], 0.01) == 0.333
    assert pytest.approx(centralities["L3"], 0.01) == 0.333

    # Test empty/fallback behaviors
    g_empty = Graph()
    assert calculate_centralities(g_empty) == {}
