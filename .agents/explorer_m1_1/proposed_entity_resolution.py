"""
entity_resolution.py — Entity Resolution similarity and merging logic for Node objects.
Uses difflib to compare node names, descriptions, and metadata.
"""
from __future__ import annotations

import difflib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from laitoxx.shared.graph.model import Node, Graph


class EntityResolver:
    @staticmethod
    def compute_similarity(n1: Node, n2: Node) -> float:
        """
        Compute similarity score between two Node objects in the range [0.0, 1.0].
        If node types differ, returns 0.0.
        Otherwise, computes a weighted similarity on label, description, and metadata.
        """
        if n1.node_type != n2.node_type:
            return 0.0

        # Exact match of cleaned labels is 1.0
        l1 = n1.label.strip().lower()
        l2 = n2.label.strip().lower()
        if l1 == l2:
            return 1.0

        label_sim = difflib.SequenceMatcher(None, l1, l2).ratio()

        # Check descriptions if both have them
        desc_sim = None
        d1 = n1.description.strip()
        d2 = n2.description.strip()
        if d1 and d2:
            desc_sim = difflib.SequenceMatcher(None, d1.lower(), d2.lower()).ratio()

        # Check shared metadata
        meta_sims = []
        shared_keys = set(n1.metadata.keys()) & set(n2.metadata.keys())
        for k in shared_keys:
            v1 = str(n1.metadata[k]).strip().lower()
            v2 = str(n2.metadata[k]).strip().lower()
            if v1 and v2:
                meta_sims.append(difflib.SequenceMatcher(None, v1, v2).ratio())

        # Aggregate similarity with dynamically adjusted weights
        total_weight = 0.7
        weighted_sum = label_sim * 0.7

        if desc_sim is not None:
            weighted_sum += desc_sim * 0.15
            total_weight += 0.15

        if meta_sims:
            avg_meta_sim = sum(meta_sims) / len(meta_sims)
            weighted_sum += avg_meta_sim * 0.15
            total_weight += 0.15

        return weighted_sum / total_weight

    @staticmethod
    def find_duplicates(graph: Graph, threshold: float) -> list[dict]:
        """
        Find and return all pairs of nodes with similarity >= threshold.
        Returns a list of dicts with keys: 'node1', 'node2', 'similarity',
        sorted by similarity descending.
        """
        duplicates = []
        num_nodes = len(graph.nodes)
        for i in range(num_nodes):
            for j in range(i + 1, num_nodes):
                n1 = graph.nodes[i]
                n2 = graph.nodes[j]
                similarity = EntityResolver.compute_similarity(n1, n2)
                if similarity >= threshold:
                    duplicates.append({
                        "node1": n1,
                        "node2": n2,
                        "similarity": similarity
                    })
        duplicates.sort(key=lambda x: x["similarity"], reverse=True)
        return duplicates
