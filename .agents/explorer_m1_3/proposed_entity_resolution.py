"""
entity_resolution.py - Entity resolution algorithms for the Graph model.
"""
from difflib import SequenceMatcher
from typing import List, Dict, Any
from laitoxx.shared.graph.model import Graph, Node

class EntityResolver:
    @staticmethod
    def compute_similarity(n1: Node, n2: Node) -> float:
        """
        Computes similarity between two nodes. Returns a float between 0.0 and 1.0.
        Only nodes of the same type can be duplicates.
        Calculates similarity using difflib.SequenceMatcher on normalized labels,
        and boosts the score if they share identical values in critical metadata keys.
        """
        if n1.node_type != n2.node_type:
            return 0.0

        label1 = n1.label.strip().lower()
        label2 = n2.label.strip().lower()

        # Exact match check
        if label1 == label2:
            return 1.0

        # Difflib similarity
        ratio = SequenceMatcher(None, label1, label2).ratio()

        # Metadata matching boost (e.g. Phone, Email, IP, etc.)
        critical_keys = {"phone", "email", "ip", "username", "address", "website", "socialaccount"}
        for k1, v1 in n1.metadata.items():
            k1_norm = k1.strip().lower()
            v1_norm = str(v1).strip().lower()
            if k1_norm in critical_keys and v1_norm:
                for k2, v2 in n2.metadata.items():
                    k2_norm = k2.strip().lower()
                    v2_norm = str(v2).strip().lower()
                    if k1_norm == k2_norm and v1_norm == v2_norm:
                        return max(ratio, 0.95)

        return ratio

    @staticmethod
    def find_duplicates(graph: Graph, threshold: float) -> List[Dict[str, Any]]:
        """
        Searches the graph for pairs of nodes with a similarity score >= threshold.
        Returns a list of dicts: [{"node1": Node, "node2": Node, "similarity": float}]
        Sorted by similarity in descending order.
        """
        duplicates = []
        nodes = graph.nodes
        num_nodes = len(nodes)
        
        for i in range(num_nodes):
            for j in range(i + 1, num_nodes):
                n1 = nodes[i]
                n2 = nodes[j]
                sim = EntityResolver.compute_similarity(n1, n2)
                if sim >= threshold:
                    duplicates.append({
                        "node1": n1,
                        "node2": n2,
                        "similarity": sim
                    })
                    
        # Sort from highest similarity to lowest
        duplicates.sort(key=lambda x: x["similarity"], reverse=True)
        return duplicates
