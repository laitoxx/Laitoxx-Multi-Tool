"""
test_graph_api.py — Unit tests for the upgraded backend models, algorithms, and entity resolution.
"""
from __future__ import annotations

import pytest
from laitoxx.shared.graph.model import Node, Edge, Graph
from laitoxx.shared.graph.entity_resolution import EntityResolver
from laitoxx.shared.graph.algorithms import get_shortest_path, calculate_centralities


def test_node_edge_temporal_fields_and_serialization():
    """Verify Node and Edge accept valid_from/valid_to fields and serialize/deserialize correctly."""
    # Test Node defaults and temporal fields
    node = Node(
        label="Test Node",
        node_type="Person",
        description="A test entity",
        valid_from="2026-01-01T00:00:00Z",
        valid_to="2026-12-31T23:59:59Z"
    )
    assert node.valid_from == "2026-01-01T00:00:00Z"
    assert node.valid_to == "2026-12-31T23:59:59Z"

    # Serialize Node
    node_dict = node.to_dict()
    assert node_dict["valid_from"] == "2026-01-01T00:00:00Z"
    assert node_dict["valid_to"] == "2026-12-31T23:59:59Z"

    # Deserialize Node
    deserialized_node = Node.from_dict(node_dict)
    assert deserialized_node.label == "Test Node"
    assert deserialized_node.valid_from == "2026-01-01T00:00:00Z"
    assert deserialized_node.valid_to == "2026-12-31T23:59:59Z"

    # Test Edge defaults and temporal fields
    edge = Edge(
        source_id="N1",
        target_id="N2",
        label="knows",
        edge_type="Connected",
        valid_from="2026-06-01T12:00:00Z",
        valid_to=None
    )
    assert edge.valid_from == "2026-06-01T12:00:00Z"
    assert edge.valid_to is None

    # Serialize Edge
    edge_dict = edge.to_dict()
    assert edge_dict["valid_from"] == "2026-06-01T12:00:00Z"
    assert edge_dict["valid_to"] is None

    # Deserialize Edge
    deserialized_edge = Edge.from_dict(edge_dict)
    assert deserialized_edge.source_id == "N1"
    assert deserialized_edge.valid_from == "2026-06-01T12:00:00Z"
    assert deserialized_edge.valid_to is None


def test_graph_merge_nodes():
    """Verify Graph.merge_nodes combines metadata, descriptions, dates, and re-routes edges without duplicates."""
    g = Graph("Merge Test Graph")
    
    # Create nodes with distinct metadata, descriptions, and temporal bounds
    n_primary = Node(
        id="N_PRIMARY",
        label="John Doe",
        node_type="Person",
        description="Software Architect",
        metadata={"role": "Architect", "country": "US"},
        valid_from="2026-02-01",
        valid_to="2026-06-01"
    )
    n_dup1 = Node(
        id="N_DUP1",
        label="J. Doe",
        node_type="Person",
        description="Senior Dev",
        metadata={"skills": "Python, C++", "country": "USA"},
        valid_from="2026-01-01",
        valid_to="2026-05-01"
    )
    n_dup2 = Node(
        id="N_DUP2",
        label="John Doe",
        node_type="Person",
        description="Consultant",
        metadata={"role": "Lead Architect", "experience": "10y"},
        valid_from="2026-03-01",
        valid_to="2026-07-01"
    )
    n_other = Node(id="N_OTHER", label="Jane Smith", node_type="Person")
    
    g.add_node(n_primary)
    g.add_node(n_dup1)
    g.add_node(n_dup2)
    g.add_node(n_other)

    # Add edges
    # Primary to Other
    e1 = Edge(id="E1", source_id="N_PRIMARY", target_id="N_OTHER", label="colleague", edge_type="Connected")
    # Duplicate 1 to Other (should be merged/deduplicated into e1 since labels and types match)
    e2 = Edge(id="E2", source_id="N_DUP1", target_id="N_OTHER", label="colleague", edge_type="Connected",
              metadata={"project": "Alpha"}, valid_from="2026-01-01", valid_to="2026-04-01")
    # Duplicate 2 to Other (with different label - should NOT be deduplicated with e1, but re-routed)
    e3 = Edge(id="E3", source_id="N_DUP2", target_id="N_OTHER", label="manager", edge_type="Connected",
              valid_from="2026-03-01", valid_to="2026-08-01")
    # Self-loop candidate: Duplicate 1 to Primary (should be discarded)
    e4 = Edge(id="E4", source_id="N_DUP1", target_id="N_PRIMARY", label="self", edge_type="Connected")

    g.add_edge(e1)
    g.add_edge(e2)
    g.add_edge(e3)
    g.add_edge(e4)

    # Perform Merge
    g.merge_nodes("N_PRIMARY", ["N_DUP1", "N_DUP2"])

    # Verification:
    # 1. Duplicate nodes removed
    assert g.get_node("N_DUP1") is None
    assert g.get_node("N_DUP2") is None
    assert g.get_node("N_PRIMARY") is not None

    # 2. Descriptions merged with delimiter
    desc_list = g.get_node("N_PRIMARY").description.split(" | ")
    assert "Software Architect" in desc_list
    assert "Senior Dev" in desc_list
    assert "Consultant" in desc_list

    # 3. Metadata merged and conflicts resolved
    metadata = g.get_node("N_PRIMARY").metadata
    assert metadata["skills"] == "Python, C++"
    assert metadata["experience"] == "10y"
    # Merged conflicting fields
    role_list = [x.strip() for x in metadata["role"].split(",")]
    assert "Architect" in role_list
    assert "Lead Architect" in role_list
    country_list = [x.strip() for x in metadata["country"].split(",")]
    assert "US" in country_list
    assert "USA" in country_list

    # 4. Dates unioned correctly (earliest start, latest end)
    assert g.get_node("N_PRIMARY").valid_from == "2026-01-01"
    assert g.get_node("N_PRIMARY").valid_to == "2026-07-01"

    # 5. Edges re-routed and deduplicated
    # Remaining edges: 
    # e1 (re-routed / representative of e1 + e2)
    # e3 (re-routed, distinct label)
    # e4 (discarded self-loop)
    assert len(g.edges) == 2
    
    e1_actual = next((e for e in g.edges if e.id == "E1"), None)
    e3_actual = next((e for e in g.edges if e.id == "E3"), None)
    
    assert e1_actual is not None
    assert e1_actual.source_id == "N_PRIMARY"
    assert e1_actual.target_id == "N_OTHER"
    # Metadata merged from e2
    assert e1_actual.metadata["project"] == "Alpha"
    # Date ranges unioned for e1/e2
    assert e1_actual.valid_from == "2026-01-01"
    assert e1_actual.valid_to == "2026-04-01"

    assert e3_actual is not None
    assert e3_actual.source_id == "N_PRIMARY"
    assert e3_actual.target_id == "N_OTHER"
    assert e3_actual.label == "manager"


def test_entity_resolver():
    """Verify compute_similarity and find_duplicates handle matching and mismatched fields."""
    n1 = Node(label="Alice Johnson", node_type="Person", description="OSINT Researcher")
    n2 = Node(label="alice johnson", node_type="Person", description="OSINT investigator")
    n3 = Node(label="Bob Smith", node_type="Person")
    n4 = Node(label="Alice Johnson", node_type="Email") # Different type

    # Similarity tests
    assert EntityResolver.compute_similarity(n1, n2) > 0.8
    assert EntityResolver.compute_similarity(n1, n3) < 0.3
    assert EntityResolver.compute_similarity(n1, n4) == 0.0

    # Test duplicates search
    g = Graph()
    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)

    dups = EntityResolver.find_duplicates(g, threshold=0.7)
    assert len(dups) == 1
    assert dups[0]["node1"].id in (n1.id, n2.id)
    assert dups[0]["node2"].id in (n1.id, n2.id)
    assert dups[0]["similarity"] > 0.7


def test_networkx_integrations():
    """Verify get_shortest_path and calculate_centralities compute correct NetworkX metrics."""
    g = Graph()
    # Linear graph: A-B-C-D
    n_a = Node(id="A", label="Node A")
    n_b = Node(id="B", label="Node B")
    n_c = Node(id="C", label="Node C")
    n_d = Node(id="D", label="Node D")
    g.add_node(n_a)
    g.add_node(n_b)
    g.add_node(n_c)
    g.add_node(n_d)

    g.add_edge(Edge(source_id="A", target_id="B"))
    g.add_edge(Edge(source_id="B", target_id="C"))
    g.add_edge(Edge(source_id="C", target_id="D"))

    # Test shortest path
    path = get_shortest_path(g, "A", "D")
    assert path == ["A", "B", "C", "D"]

    # Test no path
    g.remove_edge(next(e.id for e in g.edges if e.source_id == "B" and e.target_id == "C"))
    path_disconnected = get_shortest_path(g, "A", "D")
    assert path_disconnected == []

    # Test centrality calculations (Degree Centrality)
    # A has 1 connection, B has 1 (since B-C is removed), C has 1, D has 1
    # Let's add B-C back
    g.add_edge(Edge(source_id="B", target_id="C"))
    centralities = calculate_centralities(g, metric="degree")
    # In degree centrality, normalized degree is degree / (N - 1) = degree / 3
    # A: degree 1 -> 0.333
    # B: degree 2 -> 0.666
    # C: degree 2 -> 0.666
    # D: degree 1 -> 0.333
    assert pytest.approx(centralities["A"], 0.01) == 0.333
    assert pytest.approx(centralities["B"], 0.01) == 0.666
    assert pytest.approx(centralities["C"], 0.01) == 0.666
    assert pytest.approx(centralities["D"], 0.01) == 0.333


def test_merge_nodes_unrelated_self_loops():
    """Verify that unrelated self-loops are NOT deleted when merging nodes."""
    g = Graph("Self Loop Test")
    n_primary = Node(id="N_PRIMARY", label="John")
    n_dup = Node(id="N_DUP", label="J.")
    n_other = Node(id="N_OTHER", label="Jane")
    
    g.add_node(n_primary)
    g.add_node(n_dup)
    g.add_node(n_other)
    
    # Self-loop on unrelated node
    e_unrelated_self = Edge(id="E_UNRELATED_SELF", source_id="N_OTHER", target_id="N_OTHER")
    # Connected self-loop candidate
    e_connected_self = Edge(id="E_CONNECTED_SELF", source_id="N_DUP", target_id="N_PRIMARY")
    
    g.edges.append(e_unrelated_self)
    g.add_edge(e_connected_self)
    
    g.merge_nodes("N_PRIMARY", ["N_DUP"])
    
    # Unrelated self loop must still exist
    assert any(e.id == "E_UNRELATED_SELF" for e in g.edges)
    # Connected self loop must be deleted
    assert not any(e.id == "E_CONNECTED_SELF" for e in g.edges)


def test_merge_nodes_unrelated_multi_edges():
    """Verify that unrelated multi-edges/duplicate edges are NOT merged when merging other nodes."""
    g = Graph("Multi Edge Test")
    n_primary = Node(id="N_PRIMARY", label="John")
    n_dup = Node(id="N_DUP", label="J.")
    n_other1 = Node(id="N_OTHER1", label="Jane")
    n_other2 = Node(id="N_OTHER2", label="Bob")
    
    g.add_node(n_primary)
    g.add_node(n_dup)
    g.add_node(n_other1)
    g.add_node(n_other2)
    
    # Multi-edges on unrelated nodes (same source, target, label, type)
    e1 = Edge(id="E1", source_id="N_OTHER1", target_id="N_OTHER2", label="knows")
    e2 = Edge(id="E2", source_id="N_OTHER1", target_id="N_OTHER2", label="knows")
    
    g.add_edge(e1)
    g.edges.append(e2) # bypass add_edge check for duplication just in case
    
    g.merge_nodes("N_PRIMARY", ["N_DUP"])
    
    # Both unrelated multi-edges must remain completely unchanged
    assert len(g.edges) == 2
    assert any(e.id == "E1" for e in g.edges)
    assert any(e.id == "E2" for e in g.edges)


def test_centralities_ignore_dangling_edges():
    """Verify that centrality calculations ignore dangling edges and do not skew metrics."""
    g = Graph("Dangling Edge Test")
    n_a = Node(id="A", label="Node A")
    n_b = Node(id="B", label="Node B")
    
    g.add_node(n_a)
    g.add_node(n_b)
    
    # Edge between existing nodes
    g.add_edge(Edge(source_id="A", target_id="B"))
    
    # Dangling edge (C does not exist as a node in the graph)
    g.edges.append(Edge(source_id="B", target_id="C"))
    
    # Calculate degree centrality
    centralities = calculate_centralities(g, metric="degree")
    
    # C should not be in centralities
    assert "C" not in centralities
    # Without C, N=2, so max degree is 1. Degree of A is 1, degree of B is 1.
    # Centrality = degree / (N-1) = 1/1 = 1.0
    assert pytest.approx(centralities["A"], 0.01) == 1.0
    assert pytest.approx(centralities["B"], 0.01) == 1.0

