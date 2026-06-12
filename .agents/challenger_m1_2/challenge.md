# Challenge Report — Milestone 1 Stress Verification

## Challenge Summary

**Overall risk assessment**: HIGH

While the core functionality of the Graph Editor backend models, merging logic, similarity, and NetworkX algorithms exists, several critical logic bugs and scalability vulnerabilities were discovered via stress testing and static code analysis. These issues present risks ranging from application crashes to data corruption and UI freezes under realistic OSINT graph scenarios.

---

## Challenges

### [Critical] Challenge 1: Non-string Metadata Attribute Crash

- **Assumption challenged**: Assumes all values in `metadata` dictionaries are string types.
- **Attack scenario**: If a node contains non-string metadata values (e.g., integers like age, floats like confidence scores, or boolean flags) populated programmatically or parsed from JSON, `Graph.merge_nodes` attempts to call `.split(",")` on them. Since non-string types do not have a `.split` method, it raises an `AttributeError` and crashes the merge process.
- **Blast radius**: Completely halts the entity resolution/merging flow for any nodes containing numeric or boolean metadata.
- **Mitigation**: Convert all metadata values to strings before processing them in `merge_nodes`, or sanitize the input values:
  ```python
  curr_val = str(primary_node.metadata[k])
  new_val = str(v)
  ```

### [High] Challenge 2: Lexicographical Date Corruption

- **Assumption challenged**: Assumes all `valid_from` and `valid_to` bounds are valid ISO-8601 date strings that can be correctly compared lexicographically.
- **Attack scenario**: If a user enters non-standard date formats or invalid strings (e.g., `"N/A"`, `"invalid-date"`, or `"2026/05/01"`), `merge_dates` uses Python's standard `min` and `max` on strings. For example:
  - `max("2026-06-01", "N/A")` returns `"N/A"` (since `'N'` > `'2'`).
  - `min("2026-01-01", "invalid-date")` returns `"2026-01-01"` (since `'2'` < `'i'`).
  This corrupts the temporal bounds, changing valid date ranges to non-date strings.
- **Blast radius**: Causes corruption of the graph timeline bounds, leading to crashes or incorrect filtering when the timeline slider filters nodes.
- **Mitigation**: Parse dates using `datetime.fromisoformat()` or a similar utility before comparison, or enforce strict ISO-8601 validation at the model boundary.

### [High] Challenge 3: Dangling Edges Leading to NetworkX Inconsistencies and GUI Crashes

- **Assumption challenged**: Assumes edges only connect nodes that exist in the `graph.nodes` list.
- **Attack scenario**: If a graph loaded from a JSON file contains dangling edges (edges referencing non-existent node IDs), the NetworkX algorithm population (`G.add_edge(edge.source_id, edge.target_id)`) automatically creates these non-existent nodes in the NetworkX graph `G`.
  - `get_shortest_path` can return a path containing node IDs that do not exist in the actual graph nodes list.
  - `calculate_centralities` returns centrality scores for these non-existent nodes, and the normalization denominator `N - 1` includes them, skewing calculations for valid nodes.
- **Blast radius**: The GUI will crash or throw key errors when it tries to apply shortest path highlights or node size modifications on the non-existent node IDs.
- **Mitigation**: Filter out edges referencing non-existent nodes when building the NetworkX graph in `algorithms.py`:
  ```python
  node_ids = {n.id for n in graph.nodes}
  for edge in graph.edges:
      if edge.source_id in node_ids and edge.target_id in node_ids:
          G.add_edge(edge.source_id, edge.target_id)
  ```

### [Medium] Challenge 4: Unintended Global Edge Deduplication Side-Effect

- **Assumption challenged**: Assumes `Graph.merge_nodes` only groups and deduplicates edges connected to the merged nodes.
- **Attack scenario**: When `merge_nodes` executes, it loops through the entire `self.edges` list and groups all edges by source, target, type, and label to rebuild `self.edges`. This causes global deduplication of *all* edges in the graph, even those completely unrelated to the nodes being merged.
- **Blast radius**: Silently deletes duplicate edges that users intentionally created between unrelated nodes elsewhere in the graph.
- **Mitigation**: Restrict edge grouping and deduplication to only those edges whose source or target matches `primary_id` or was in the `valid_dup_ids` list.

### [High] Challenge 5: Performance Bottleneck in Similarity Computation & Duplicate Detection

- **Assumption challenged**: Assumes the graph size will remain small enough that O(N^2) comparison with O(L^2) string matching is feasible on the main thread.
- **Attack scenario**: `EntityResolver.find_duplicates` compares every pair of nodes. Inside the loop, it calls `difflib.SequenceMatcher` to compare description strings. If the graph contains 500+ nodes with descriptions, this requires 124,750 comparisons, which will block the main thread for several seconds. For larger graphs (2,000+ nodes), it will hang the UI.
- **Blast radius**: Application UI freezes during duplicate detection on moderately sized graphs.
- **Mitigation**: Implement a fast pre-filtering step (e.g., hash matching or length heuristics) to avoid calling `SequenceMatcher` on obviously disjoint pairs, and run duplicate detection in a background worker thread.

---

## Stress Test Results

| Scenario | Expected Behavior | Predicted Behavior | Pass/Fail |
|---|---|---|---|
| Merge nodes with integer metadata values | Handle and convert integers to strings | Crashes with `AttributeError` (no `split` method) | **FAIL** |
| Merge nodes with invalid temporal strings (e.g., "N/A") | Gracefully fallback or validate | Corrupts dates using lexicographical comparison | **FAIL** |
| Run NetworkX algorithms with dangling edges | Ignore dangling edges or report only on valid nodes | Includes non-existent nodes in path and centrality results | **FAIL** |
| Merge unrelated duplicate edges during `merge_nodes` | Leave unrelated edges unchanged | Silently deduplicates/deletes unrelated duplicate edges | **FAIL** |
| Perform duplicate detection on 1000 nodes | Execute within a reasonable timeframe (e.g., < 1s) | Hangs/Freezes UI due to O(N^2) SequenceMatcher loop | **FAIL** |

---

## Unchallenged Areas

- **Frontend Qt/JS rendering**: Out of scope for Milestone 1.
- **File Metadata extraction**: Out of scope for Milestone 1.
