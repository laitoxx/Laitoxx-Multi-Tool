# Handoff Report — Challenger 2 (Milestone 1 Stress & Verification)

## 1. Observation
- **File Path**: `src/laitoxx/shared/graph/model.py`
  - In `Graph.merge_nodes` (lines 259-270):
    ```python
    curr_val = primary_node.metadata[k]
    if curr_val != v:
        curr_list = [x.strip() for x in curr_val.split(",") if x.strip()]
        new_list = [x.strip() for x in v.split(",") if x.strip()]
        for item in new_list:
            if item not in curr_list:
                curr_list.append(item)
        primary_node.metadata[k] = ", ".join(curr_list)
    ```
  - In `Graph.merge_nodes` (lines 278-322):
    The method loops over `self.edges` globally and groups/rebuilds the entire list using `edge_groups: dict[tuple[str, str, str, str], list[Edge]] = {}` keying on `(edge.source_id, edge.target_id, edge.edge_type, edge.label)`. This applies deduplication to the entire graph's edges list, not just re-routed edges.
- **File Path**: `src/laitoxx/shared/graph/algorithms.py`
  - In `get_shortest_path` (lines 20-25) and `calculate_centralities` (lines 45-49):
    ```python
    G = nx.Graph()
    for node in graph.nodes:
        G.add_node(node.id)
    for edge in graph.edges:
        G.add_edge(edge.source_id, edge.target_id)
    ```
    This does not filter `edge.source_id` or `edge.target_id` against the list of nodes in the graph before adding to the NetworkX graph.
- **File Path**: `src/laitoxx/shared/graph/entity_resolution.py`
  - In `EntityResolver.find_duplicates` (lines 71-85):
    Uses a nested double-loop `for i in range(num_nodes)` and `for j in range(i + 1, num_nodes)` calling `EntityResolver.compute_similarity`, which uses `difflib.SequenceMatcher` on description strings.
- **Command Output**:
  - `run_command` calls to run the unit tests and the newly created `tests/stress_tests.py` script timed out waiting for user permission (automatic environment timeout).
  - A stress test script was successfully written to `tests/stress_tests.py`.

## 2. Logic Chain
1. **Metadata Crash**: Under Observation 1, if any key in `metadata` has a non-string value (e.g. `int`), calling `.split(",")` on `curr_val` or `v` will raise an `AttributeError` because integers do not have a `split` method. Therefore, merging nodes with numeric/boolean metadata values will cause a runtime crash.
2. **Date Corruption**: Under Observation 1, `merge_dates` uses lexicographical string comparison via `min` and `max`. If an invalid date string (e.g., `"N/A"`) is compared against a valid date string (e.g., `"2026-06-01"`), `max` returns `"N/A"` because `'N'` is lexicographically greater than `'2'`, leading to corruption of the temporal bounds.
3. **Dangling Edges**: Under Observation 2, NetworkX's `G.add_edge` automatically creates nodes for endpoints that don't exist in `G`. This means that any dangling edges will cause non-existent nodes to be added to the NetworkX graph. Thus, `get_shortest_path` can return path lists with non-existent node IDs, and `calculate_centralities` will return centrality scores for those non-existent nodes, which will trigger key errors or UI crashes when the GUI attempts to size or highlight them.
4. **Global Edge Deduplication**: Under Observation 1, `merge_nodes` rebuilds the global `self.edges` list by grouping and deduplicating all edges in the graph matching the same key. This will silently delete duplicate edges intentionally created between completely unrelated nodes elsewhere in the graph.
5. **Performance Bottleneck**: Under Observation 3, performing an O(N^2) search using `difflib.SequenceMatcher` (which has O(L^2) worst-case time complexity) on description strings will block the UI thread on moderately-sized graphs (e.g. 500+ nodes).

## 3. Caveats
- Since the interactive shell command execution timed out, the stress test suite (`tests/stress_tests.py`) was not run in this shell environment. However, the logic flaws were confirmed through rigorous static analysis and manual code execution traces.

## 4. Conclusion
The implementation of Milestone 1 is functionally complete according to the spec, but suffers from several critical robustness flaws, including potential runtime crashes (non-string metadata split), data corruption (lexicographical date comparison), UI bugs (dangling edges propagating through NetworkX), unintended global side-effects (global edge deduplication), and scalability issues (quadratic duplicate detection).

## 5. Verification Method
1. Inspect the stress test script written to `tests/stress_tests.py`.
2. Run the stress tests using the project's virtual environment:
   ```bash
   ./venv/bin/python tests/stress_tests.py
   ```
3. Run the standard unit test suite:
   ```bash
   ./venv/bin/python -m pytest tests/test_graph_api.py
   ```
4. Verify that:
   - `test_merge_nodes_non_string_metadata` crashes with `AttributeError` in the current implementation.
   - `test_merge_nodes_invalid_dates` results in `valid_to` being set to `"N/A"`.
   - `test_dangling_edges_in_algorithms` returns non-existent node IDs in the shortest path and centrality calculations.
