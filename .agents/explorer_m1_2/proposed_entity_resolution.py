import difflib
from laitoxx.shared.graph.model import Node, Graph

class EntityResolver:
    @staticmethod
    def compute_similarity(n1: Node, n2: Node) -> float:
        """
        Compute similarity between two nodes using difflib.
        Returns a float between 0.0 and 1.0.
        If node types differ (case-insensitive check), returns 0.0.
        Otherwise, computes a weighted similarity on label, description, and metadata.
        """
        # Node types must match (case-insensitive check)
        type1 = (n1.node_type or "Custom").strip().lower()
        type2 = (n2.node_type or "Custom").strip().lower()
        if type1 != type2:
            return 0.0

        weights = []
        scores = []

        # 1. Label Similarity (Weight: 0.7)
        label1 = (n1.label or "").strip().lower()
        label2 = (n2.label or "").strip().lower()
        if not label1 and not label2:
            label_sim = 1.0
        elif not label1 or not label2:
            label_sim = 0.0
        elif label1 == label2:
            label_sim = 1.0
        else:
            label_sim = difflib.SequenceMatcher(None, label1, label2).ratio()
        
        weights.append(0.7)
        scores.append(label_sim)

        # 2. Description Similarity (Weight: 0.1, only if both have descriptions)
        desc1 = (n1.description or "").strip().lower()
        desc2 = (n2.description or "").strip().lower()
        if desc1 and desc2:
            if desc1 == desc2:
                desc_sim = 1.0
            else:
                desc_sim = difflib.SequenceMatcher(None, desc1, desc2).ratio()
            weights.append(0.1)
            scores.append(desc_sim)

        # 3. Metadata Similarity (Weight: 0.2, only if they share keys)
        meta_sims = []
        common_keys = set(n1.metadata.keys()) & set(n2.metadata.keys())
        for key in common_keys:
            v1 = (n1.metadata[key] or "").strip().lower()
            v2 = (n2.metadata[key] or "").strip().lower()
            if v1 and v2:
                if v1 == v2:
                    val_sim = 1.0
                else:
                    val_sim = difflib.SequenceMatcher(None, v1, v2).ratio()
                meta_sims.append(val_sim)
            elif not v1 and not v2:
                meta_sims.append(1.0)
            else:
                meta_sims.append(0.0)

        if meta_sims:
            avg_meta_sim = sum(meta_sims) / len(meta_sims)
            weights.append(0.2)
            scores.append(avg_meta_sim)

        # Compute weighted average
        total_weight = sum(weights)
        if total_weight > 0:
            final_score = sum(w * s for w, s in zip(weights, scores)) / total_weight
        else:
            final_score = 0.0

        return round(final_score, 4)

    @staticmethod
    def find_duplicates(graph: Graph, threshold: float) -> list[dict]:
        """
        Identify potential duplicate nodes in the graph above the threshold.
        Returns a list of dicts: [{"node1": Node, "node2": Node, "similarity": float}]
        Sorted by similarity in descending order.
        """
        duplicates = []
        num_nodes = len(graph.nodes)
        
        for i in range(num_nodes):
            for j in range(i + 1, num_nodes):
                n1 = graph.nodes[i]
                n2 = graph.nodes[j]
                sim = EntityResolver.compute_similarity(n1, n2)
                if sim >= threshold:
                    duplicates.append({
                        "node1": n1,
                        "node2": n2,
                        "similarity": sim
                    })
                    
        # Sort by similarity descending
        duplicates.sort(key=lambda x: x["similarity"], reverse=True)
        return duplicates
