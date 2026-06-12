# M1.2 Backend Models, Algorithms & Tests Analysis Report

**Executive Summary**: This report delivers the complete designs and proposed code/patches for adding temporal metadata to Laitoxx graphs, resolving duplicate entities, computing path and centrality metrics with NetworkX, and resolving a GUI capitalization bug.

---

## 1. Direct Observations

### 1.1 Model & Serialization Structure
- File: `/home/vdox/github_repos/Laitoxx-Multi-Tool/src/laitoxx/shared/graph/model.py`
- Line 80-91: `Node` dataclass currently does not define temporal attributes.
  ```python
  @dataclass
  class Node:
      label: str
      node_type: str = "Custom"
      description: str = ""
      metadata: dict[str, str] = field(default_factory=dict)
      # Mermaid display
      mermaid_shape: str = "[]"          # e.g. "[]", "()", "(())", "{}"
      mermaid_style: str = ""            # CSS style string
      # Internal
      id: str = field(default_factory=lambda: f"N{uuid.uuid4().hex[:6].upper()}")
  ```
- Line 128-138: `Edge` dataclass similarly lacks temporal attributes.
- Line 102-124 (Node serialization) and 140-164 (Edge serialization) do not handle `valid_from` or `valid_to` fields.
- Line 208-237: `Graph` does not contain any duplicate-resolution or node-merging method.

### 1.2 GUI Capitalization & Shape Discrepancy
- File: `/home/vdox/github_repos/Laitoxx-Multi-Tool/src/laitoxx/features/utilities/metadata_viewer/gui_window.py`
- Line 330:
  ```python
  file_node = Node(
      id=str(uuid.uuid4()),
      label=data.get("FileName", os.path.basename(filepath)),
      node_type="document"
  )
  ```
  *Discrepancy*: `node_type` is passed as `"document"` (lowercase), whereas `NODE_TYPE_DEFAULTS` in `model.py` maps default styles and shapes using title case `"Document"`.
- Line 341:
  ```python
  author_node = Node(id=str(uuid.uuid4()), label=val_str, node_type="person")
  ```
  *Discrepancy*: `node_type` is `"person"` (lowercase) instead of title case `"Person"`.
- Line 354:
  ```python
  software_node = Node(id=str(uuid.uuid4()), label=val_str, node_type="custom", shape="hexagon")
  ```
  *Discrepancy*: `node_type` is `"custom"` (lowercase) instead of `"Custom"`. Additionally, it passes `shape="hexagon"` to the `Node` constructor. However, `Node` has no attribute `shape` defined; it defines `mermaid_shape`. This results in a runtime `TypeError` when exporting metadata.

### 1.3 Dependencies
- File: `/home/vdox/github_repos/Laitoxx-Multi-Tool/requirements.txt`
- Line 16: `networkx` is listed as a dependency, confirming NetworkX is available for import in the project's environment.

---

## 2. Design Specifications

Detailed implementation proposals are saved as separate files in the agent directory:
- `proposed_model.py` & `model.patch`
- `proposed_entity_resolution.py`
- `proposed_algorithms.py`
- `proposed_test_graph_api.py`
- `gui_window.patch`

### 2.1 Task 1: Temporal Fields & Serialization (`model.py`)
- **Node & Edge additions**:
  Add `valid_from: Optional[str] = None` and `valid_to: Optional[str] = None` properties. The fields accept ISO-8601 string representations (e.g. `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SSZ`) or `None`/empty strings.
- **Placement**:
  Fields must be defined after non-default fields to comply with Python's `@dataclass` constraints. In `Node`, placing them after `mermaid_style` and before `id` maintains semantic grouping.
- **to_dict() / from_dict()**:
  - `to_dict` includes `"valid_from": self.valid_from` and `"valid_to": self.valid_to`.
  - `from_dict` retrieves them with `d.get("valid_from", None)` and `d.get("valid_to", None)`.

### 2.2 Task 2: Node Merging API (`model.py`)
- **Method Signature**: `Graph.merge_nodes(self, primary_id: str, duplicate_ids: list[str]) -> None`.
- **Merging Logic**:
  1. **Description & Metadata**: Concatenates descriptions of primary and duplicate nodes with newline delimiters, preventing duplicate lines/paragraphs. Merges metadata dictionaries; primary node keys have precedence.
  2. **Temporal Bounds**: Performs union of valid ranges. `valid_from` gets the minimum of non-None values; `valid_to` gets the maximum of non-None values.
  3. **Re-routing Edges**: Re-routes all edges whose `source_id` or `target_id` matches any `duplicate_ids` to point to `primary_id`.
  4. **Deduplicating Edges**: Groups edges by `(source_id, target_id, label, edge_type)`. If duplicates exist, it retains one edge, merges metadata keys (preserving primary), calculates min/max on temporal fields, and deletes other duplicates.
  5. **Removal**: Deletes duplicate node instances from `self.nodes`.

### 2.3 Task 3: Entity Resolution (`entity_resolution.py`)
- **Similarity Metric (`compute_similarity`)**:
  - Compares nodes of the **same type** (case-insensitive). If types differ, returns `0.0`.
  - Calculates similarity ratios using `difflib.SequenceMatcher(None, str1, str2).ratio()`.
  - Computes weighted average:
    - **Label Similarity** (Weight: 0.7) - Compares lowercased node labels.
    - **Description Similarity** (Weight: 0.1) - Compares lowercased descriptions (only if both are present).
    - **Metadata Similarity** (Weight: 0.2) - Compares lowercased metadata values for matching keys.
  - Dynamically recalculates weights if descriptions or metadata keys are absent.
- **Duplicate Detection (`find_duplicates`)**:
  - Iterates over all unique node pairs `(n1, n2)` in `graph.nodes`.
  - Filters pairs with similarity >= `threshold`.
  - Returns a list of dicts: `[{"node1": Node, "node2": Node, "similarity": float}]`, sorted descending by similarity.

### 2.4 Task 4: NetworkX Integration (`algorithms.py`)
- **NetworkX Graph Construction**:
  Converts the internal `Graph` representation into a NetworkX graph structure using an undirected representation (`nx.Graph`).
- **Shortest Path (`get_shortest_path`)**:
  - Leverages `nx.shortest_path(nx_g, source=source_id, target=target_id)`.
  - Catches `nx.NetworkXNoPath` or missing node exceptions, returning `[]` to ensure robust integration.
- **Centralities (`calculate_centralities`)**:
  - Supports `"degree"`, `"betweenness"`, `"closeness"`, and `"eigenvector"`.
  - Safely handles convergence errors in `nx.eigenvector_centrality` by catching `nx.PowerIterationFailedConvergence` and falling back to degree centrality.
  - Returns a dictionary mapping all node IDs to float values.

### 2.5 Task 5: Test Suite (`tests/test_graph_api.py`)
Plans unit test coverage covering:
1. `test_temporal_serialization` (Node/Edge serialization & JSON roundtrip)
2. `test_merge_nodes_attributes` (Descriptions concatenation, metadata hierarchy, temporal min/max merging)
3. `test_merge_nodes_reroute_and_deduplicate_edges` (Edge re-routing, metadata combination, temporal range updates, duplicates removal)
4. `test_compute_similarity` (Type checking, exact string match, difflib weights)
5. `test_find_duplicates` (Threshold filtering, type safety)
6. `test_get_shortest_path` (Valid path, disconnected nodes, nonexistent IDs)
7. `test_calculate_centralities` (Line, star, and clique structures; star center correctness; fallback scenarios)

### 2.6 Task 6: GUI Discrepancies (`gui_window.py`)
- Corrects lowercase strings in `Node` instantiations within `_export_to_graph` to match title-case defaults:
  - `"document"` -> `"Document"`
  - `"person"` -> `"Person"`
  - `"custom"` -> `"Custom"`
- Replaces parameter `shape="hexagon"` with `mermaid_shape="hexagon"` to match standard `Node` attributes and prevent `TypeError`.

---

## 3. Logic Chain

1. **Observations 1.1 & 1.2** demonstrate that temporal fields are absent in backend model classes, and `gui_window.py` will fail with a `TypeError` due to using the nonexistent `shape` argument when calling the `Node` constructor.
2. In **Observation 1.2**, we see that `node_type` values are instantiated as lowercase (`"document"`, `"person"`, `"custom"`), whereas the default styling configurations in `model.py` are mapped to title-cased keys (`"Document"`, `"Person"`, `"Custom"`). Case-sensitive lookups in future layout scripts will fail to apply styling.
3. Therefore, standardizing capitalization in `gui_window.py` and renaming `shape` to `mermaid_shape` resolves layout issues and prevents runtime errors.
4. Implementing `valid_from` and `valid_to` in models and serialization enables temporal query capabilities required for timeline UI widgets.
5. In **Observation 1.3**, NetworkX is verified as available. Converting Laitoxx Graphs to `nx.Graph` instances allows utilizing Python's most robust and standard library for shortest path and centrality calculations.
6. The proposed code structure is completely isolated into the `.agents/explorer_m1_2` directory as requested, avoiding any direct modifications to existing workspace source code.

---

## 4. Caveats
- No temporal validity timezone conversion is designed; dates are compared as standard ISO-8601 strings lexicographically, which is robust if timestamps are formatted consistently (e.g. UTC Z format).
- NetworkX algorithms are calculated on an undirected graph representation, which is typical for standard centrality layout rendering and navigation.

---

## 5. Conclusion
The designs are fully compatible with existing contracts and provide robust implementations for the Milestone 1 features. The proposed files are ready for integration.

---

## 6. Verification Method

Once the changes are implemented, they can be verified by running the test suite:
```bash
pytest tests/test_graph_api.py
```
To run manually using the proposed tests:
```bash
PYTHONPATH=src pytest .agents/explorer_m1_2/proposed_test_graph_api.py
```
Verification will succeed if all 7 tests pass without error.
