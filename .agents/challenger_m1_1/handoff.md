# Handoff Report — Challenger 1 for Milestone 1

## 1. Observation
We observed the following in the codebase:
- In `src/laitoxx/shared/graph/model.py`, line 289-291:
  ```python
            # Avoid self-loops
            if edge.source_id == edge.target_id:
                continue
  ```
- In `src/laitoxx/shared/graph/model.py`, line 293-296:
  ```python
            key = (edge.source_id, edge.target_id, edge.edge_type, edge.label)
            if key not in edge_groups:
                edge_groups[key] = []
            edge_groups[key].append(edge)
  ```
- In `src/laitoxx/shared/graph/model.py`, line 239-247:
  ```python
        def merge_dates(d1: Optional[str], d2: Optional[str], op_type: str) -> Optional[str]:
            if not d1:
                return d2
            if not d2:
                return d1
            if op_type == "min":
                return min(d1, d2)
            else:
                return max(d1, d2)
  ```
- In `src/laitoxx/shared/graph/algorithms.py`, line 22-25:
  ```python
    for node in graph.nodes:
        G.add_node(node.id)
    for edge in graph.edges:
        G.add_edge(edge.source_id, edge.target_id)
  ```
- In `src/laitoxx/shared/graph/entity_resolution.py`, line 72-83:
  ```python
        num_nodes = len(graph.nodes)
        for i in range(num_nodes):
            for j in range(i + 1, num_nodes):
                n1 = graph.nodes[i]
                n2 = graph.nodes[j]
                similarity = EntityResolver.compute_similarity(n1, n2)
                if similarity >= threshold:
                    ...
  ```
- Additionally, running terminal commands via `run_command` in this environment timed out waiting for user approval.

## 2. Logic Chain
- **Self-Loop Deletion (Challenge 1)**: In `Graph.merge_nodes`, the loop iterates over all edges in `self.edges`. Line 290 checks `if edge.source_id == edge.target_id: continue`. Any edge where source equals target is skipped and thus excluded from the returned `new_edges` list. This applies universally to all edges in the graph, not just those connected to the merged nodes. Therefore, any pre-existing self-loops on unrelated nodes will be deleted from the graph.
- **Edge Deduplication Side-Effect (Challenge 2)**: In `Graph.merge_nodes`, the loop groups all edges in `self.edges` into `edge_groups` by `(source_id, target_id, edge_type, label)`. The final edge set `self.edges` is rebuilt using only the representative (first) edge from each group. This process occurs for every edge in the graph. Therefore, unrelated duplicate edges (multi-edges) between completely distinct nodes will be deduplicated and their metadata merged.
- **Date Comparison (Challenge 3)**: In `merge_dates`, the comparison uses standard Python string comparisons `min(d1, d2)` and `max(d1, d2)`. Lexicographically, `"2026-01-01T05:00:00Z"` < `"2026-01-01T09:00:00+05:00"` since `'5'` < `'9'`. However, `2026-01-01T09:00:00+05:00` represents `04:00:00Z` UTC, which is chronologically earlier. The raw string comparison thus selects the wrong date.
- **Dangling Edges in NetworkX (Challenge 4)**: In `algorithms.py`, NetworkX's `G.add_edge(edge.source_id, edge.target_id)` is called for all edges. If an edge has a source or target node ID that is not present in `graph.nodes`, NetworkX implicitly adds that node to the graph `G`. Centrality computations (such as degree centrality) are normalized by dividing by the number of nodes in `G` minus 1. Since `G` now contains extra dangling nodes, the centrality scores for all nodes will be calculated with an incorrect denominator, and the returned dictionary will include keys for non-existent nodes.
- **Entity Resolution Performance (Challenge 5)**: `find_duplicates` compares all pairs of nodes using nested loops. The complexity is $O(N^2)$. For each pair, it computes similarity using `difflib.SequenceMatcher`, which uses a slow quadratic algorithm in Python. For a graph with 5,000 nodes, this requires 12.5 million comparisons, which will lead to a Time Limit Exceeded (TLE) error.

## 3. Caveats
- Since command execution was not approved/available due to the environment's permission timeout, we could not run physical execution stress-tests (e.g. running pytest or executing custom scripts). However, the logical conclusions are derived directly from a complete review of the source code.

## 4. Conclusion
The Milestone 1 backend has multiple logical and performance vulnerabilities:
- Data corruption/loss risks via global self-loop deletion and global edge deduplication in `merge_nodes`.
- Chronological inaccuracies due to lexicographical date string comparison.
- Skewed graph metrics from dangling edges in NetworkX.
- Performance bottleneck in entity resolution on large graphs.

## 5. Verification Method
1. Inspect the source code files:
   - `src/laitoxx/shared/graph/model.py`
   - `src/laitoxx/shared/graph/algorithms.py`
   - `src/laitoxx/shared/graph/entity_resolution.py`
2. Run unit tests using pytest once permission is available:
   ```bash
   venv/bin/pytest tests/test_graph_api.py
   ```
3. Run the following validation scripts (mock verification) to reproduce the bugs:
   - Construct a graph with a self-loop on `Node B` and merge `Node X` and `Node Y`. Verify that the self-loop on `Node B` is deleted.
   - Construct a graph with two separate edges between `Node A` and `Node B` and merge `Node X` and `Node Y`. Verify that the edges between `Node A` and `Node B` are deduplicated.
