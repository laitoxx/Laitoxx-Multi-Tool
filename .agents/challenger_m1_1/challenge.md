## Challenge Summary

**Overall risk assessment**: HIGH

Milestone 1 backend graph implementation was reviewed using static analysis and logical execution traces. While the basic functionality is implemented and tested, we identified 5 distinct correctness, integrity, and performance vulnerabilities that pose risks to data integrity and system stability.

---

## Challenges

### [High] Challenge 1: Unrelated Self-Loop Deletion in `Graph.merge_nodes`

- **Assumption challenged**: The assumption that self-loop filtering during a node merge should apply to all edges in the entire graph.
- **Attack scenario**: A user has a graph where some unrelated nodes have self-loop edges (e.g. `Node B -> Node B` representing self-referencing relationship types like "loopback"). When the user merges two other unrelated nodes `Node X` and `Node Y`, the merge method `Graph.merge_nodes` iterates over all edges in the graph, identifies `Node B -> Node B` as a self-loop (since `edge.source_id == edge.target_id`), and skips it. Consequently, all self-loops in the graph are silently deleted.
- **Blast radius**: High. Permanent loss of self-loops across the entire graph upon any merge operation, regardless of whether those nodes are part of the merge list.
- **Mitigation**: Update the self-loop check in `merge_nodes` to only discard self-loops if the edge's source and target match the `primary_id` or the `valid_dup_ids`. All other self-loops should be preserved.
  ```python
  if edge.source_id == edge.target_id and edge.source_id == primary_id:
      continue
  ```

### [Medium] Challenge 2: Unrelated Edge Deduplication and Metadata Merging in `Graph.merge_nodes`

- **Assumption challenged**: The assumption that deduplication and metadata merging should apply to all edges in the graph during a node merge.
- **Attack scenario**: A user has duplicate edges (multi-edges) between unrelated nodes `Node A` and `Node B` (e.g. two separate `colleague` edges representing different projects/contexts). When the user merges `Node X` and `Node Y`, the `merge_nodes` method groups all edges in the entire graph by `(source_id, target_id, edge_type, label)` and deduplicates them, combining their metadata. Unrelated multi-edges on nodes `A` and `B` are collapsed into a single representative edge and their metadata merged.
- **Blast radius**: Medium. Unintended modification and data loss (loss of separate edge objects) across the entire graph.
- **Mitigation**: Restrict edge re-routing, self-loop elimination, and deduplication logic exclusively to edges that are connected to `primary_id` or `valid_dup_ids`. Unrelated edges should be kept untouched.

### [Medium] Challenge 3: Inconsistent/Incorrect Chronological Date Aggregation due to Lexicographical Comparison

- **Assumption challenged**: The assumption that ISO-8601 or datetime strings can be chronologically sorted/aggregated using Python's raw `min()` and `max()` string comparisons.
- **Attack scenario**:
  - `Node A` (primary) has `valid_from = "2026-01-01T05:00:00Z"` (5:00 AM UTC).
  - `Node B` (duplicate) has `valid_from = "2026-01-01T09:00:00+05:00"` (4:00 AM UTC, which is earlier).
  - When merging, `merge_dates` compares `"2026-01-01T05:00:00Z"` and `"2026-01-01T09:00:00+05:00"` using `min()`.
  - Since `'5'` < `'9'` lexicographically, it returns `"2026-01-01T05:00:00Z"` as the earliest date. This is chronologically incorrect.
  - Similarly, mixed date formats like `"2026-06-01"` (YYYY-MM-DD) vs `"2026-06-01T00:00:00Z"` or `"01/06/2026"` will yield incorrect lexicographical min/max values.
- **Blast radius**: Medium. Corrupted or invalid merged chronological bounds for nodes and edges.
- **Mitigation**: Parse date strings into datetime objects using a parser (e.g., `dateutil.parser` or `datetime.fromisoformat` if standard format is enforced) before comparing, and format them back to string. Or, validate and normalize all date strings to UTC ISO-8601 format before doing lexicographical operations.

### [Medium] Challenge 4: Dangling Edges Injected into NetworkX Graphs causing Skewed Metrics

- **Assumption challenged**: The assumption that graphs loaded via `Graph.from_dict` contain only valid edges referencing existing nodes, or that NetworkX integration handles dangling edges correctly.
- **Attack scenario**: A user imports a JSON graph file containing an edge connecting node `A` to a non-existent node `C`.
  - `Graph.from_dict` loads all nodes and edges without validation.
  - When `calculate_centralities` is run, it builds a NetworkX graph `G` by adding all nodes and edges.
  - `G.add_edge("A", "C")` implicitly adds node `C` to `G`.
  - `calculate_centralities` computes degree centrality of `G`. The size of the graph `N` increases by 1, which changes the degree centrality of all other nodes (since degree centrality is divided by `N-1`).
  - The centrality scores return scores for node `C` (which doesn't exist in the Laitoxx Graph), and the scores of `A` and `B` are mathematically incorrect relative to the actual node set.
- **Blast radius**: Medium. Corrupted graph metrics and inconsistent UI node lists vs centrality key listings.
- **Mitigation**: Filter out edges with invalid/dangling node IDs in `from_dict` or before passing the graph to NetworkX algorithms, or raise a validation error during deserialization.

### [High] Challenge 5: Performance Bottleneck ($O(N^2)$ Quadratic Time Complexity) in Entity Resolution

- **Assumption challenged**: The assumption that the duplicate detection process (`find_duplicates`) is scalable.
- **Attack scenario**: A user loads an OSINT graph with 5,000 nodes and runs duplicate detection.
  - `find_duplicates` compares all pairs of nodes: $\frac{5000 \times 4999}{2} \approx 12.5 \text{ million}$ comparisons.
  - For each pair, it computes similarity. If the types match, it calls `difflib.SequenceMatcher` (which is $O(L^2)$ where $L$ is string length) on labels, descriptions, and metadata keys.
  - This process runs in pure Python and will take hours or run out of memory, causing the application to hang or crash (Time/Memory Limit Exceeded).
- **Blast radius**: High. System unresponsive or freeze when analyzing medium-to-large datasets.
- **Mitigation**:
  - Implement a blocking/indexing key strategy: group nodes by type first, and then group by a prefix/soundex/hash of the label. Only compare nodes within the same block.
  - Set a maximum limit on node count for full pairwise comparison.
  - Optimize string comparison: use faster libraries (like `rapidfuzz` or simple prefix/Jaro-Winkler) rather than the slow `difflib.SequenceMatcher`.

---

## Stress Test Results

- **Scenario 1: Merge nodes when unrelated self-loops exist**
  - Expected behavior: Unrelated self-loops are preserved.
  - Predicted behavior: All self-loops in the graph are deleted.
  - Result: **FAIL**

- **Scenario 2: Merge nodes when unrelated duplicate edges exist**
  - Expected behavior: Unrelated duplicate edges are preserved.
  - Predicted behavior: All duplicate edges in the graph matching by `(source_id, target_id, edge_type, label)` are collapsed and their metadata merged.
  - Result: **FAIL**

- **Scenario 3: Date aggregation with different timezone offsets**
  - Expected behavior: Chronological min/max is retrieved.
  - Predicted behavior: Lexicographical min/max is retrieved, which incorrectly identifies `"2026-01-01T05:00:00Z"` as earlier than `"2026-01-01T09:00:00+05:00"`.
  - Result: **FAIL**

- **Scenario 4: Centrality calculation with dangling edges**
  - Expected behavior: Centrality only computed over valid nodes, ignoring dangling edges.
  - Predicted behavior: NetworkX adds dummy nodes, changing `N` and skewing degree/betweenness centrality values.
  - Result: **FAIL**

- **Scenario 5: Large graph (5,000+ nodes) duplicate detection**
  - Expected behavior: Completes in a reasonable time (e.g. < 5 seconds).
  - Predicted behavior: Takes several hours/hangs due to $O(N^2)$ comparisons with slow `SequenceMatcher`.
  - Result: **FAIL**

---

## Unchallenged Areas

- **Visual Rendering (D3.js / HTML generation)** — Out of scope. The challenge focused on the models, merging logic, similarity algorithm, and NetworkX algorithms.
- **PyQt5 GUI integrations** — Out of scope.
