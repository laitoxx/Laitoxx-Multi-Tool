# Laitoxx Graph Editor OSINT Upgrade Analysis Report

This report provides the read-only architectural investigation and concrete code designs for Milestone 1 of the OSINT Graph Upgrade.

---

## 1. Temporal Field Additions & Serialization

### Node and Edge Modifications
In `src/laitoxx/shared/graph/model.py`, both `Node` and `Edge` must support temporal visibility constraints. These are implemented as optional ISO-8601 string fields.

- **`valid_from`**: Represents the start of the entity/relationship validity (lexicographically sortable string, e.g., `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SSZ`, or `None` if unbounded).
- **`valid_to`**: Represents the end of the entity/relationship validity (or `None` if unbounded).

Since the Python `@dataclass` decorator requires that fields with default values come after fields without defaults, these are added to the end of the dataclasses.

```python
# Node Class temporal fields additions
valid_from: Optional[str] = None
valid_to: Optional[str] = None

# Edge Class temporal fields additions
valid_from: Optional[str] = None
valid_to: Optional[str] = None
```

### Serialization Design
The `to_dict` and `from_dict` methods are updated to handle the new temporal fields:

```python
# Node Serialization
def to_dict(self) -> dict:
    return {
        "id": self.id,
        "label": self.label,
        "node_type": self.node_type,
        "description": self.description,
        "metadata": self.metadata,
        "mermaid_shape": self.mermaid_shape,
        "mermaid_style": self.mermaid_style,
        "valid_from": self.valid_from,
        "valid_to": self.valid_to,
    }

@classmethod
def from_dict(cls, d: dict) -> "Node":
    n = cls(
        label=d.get("label", ""),
        node_type=d.get("node_type", "Custom"),
        description=d.get("description", ""),
        metadata=d.get("metadata", {}),
        mermaid_shape=d.get("mermaid_shape", "[]"),
        mermaid_style=d.get("mermaid_style", ""),
        valid_from=d.get("valid_from"),
        valid_to=d.get("valid_to"),
    )
    n.id = d.get("id", n.id)
    return n
```

---

## 2. Graph Node Merging Design (`Graph.merge_nodes`)

When merging duplicate nodes into a primary node, the system must consolidate descriptions, merge metadata (resolving key collisions), determine the union date range, re-route edges, and deduplicate edges.

### A. Attributes & Descriptions Merging
- **Description**: Gather all non-empty descriptions from the primary and duplicate nodes, remove exact duplicates, and join them using ` | ` or `\n` to prevent data loss.
- **Metadata**: Add key-value pairs from duplicate nodes into the primary node. If a key already exists with a different value:
  - Extract comma-separated sub-elements from both values.
  - Form a union list of unique strings.
  - Save the merged values as a comma-separated string (e.g., `role: "Architect" + "Lead Developer" -> "Architect, Lead Developer"`).

### B. Temporal Bounds Union Logic
For OSINT graph usage, temporal bounds are optional annotations. If one node has dates and another does not, the dates must be preserved rather than overwritten by `None` (representing "not specified").
- **`valid_from`**: Minimum of the non-empty start dates.
- **`valid_to`**: Maximum of the non-empty end dates.

```python
def merge_dates(d1: Optional[str], d2: Optional[str], op_type: str) -> Optional[str]:
    if not d1:
        return d2
    if not d2:
        return d1
    return min(d1, d2) if op_type == "min" else max(d1, d2)
```

### C. Edge Re-routing & Deduplication
- Loop through all edges and replace `source_id` / `target_id` references to duplicate nodes with the `primary_id`.
- Discard self-loops (edges where `source_id == target_id`) to keep the visual graph clean.
- Group the re-routed edges by their signature: `(source_id, target_id, edge_type, label)`.
- For each duplicate group, merge their metadata and date ranges (earliest start, latest end) into a single representative edge, discarding the redundant ones.
- Finally, delete the duplicate nodes from the graph.

For the full Python implementation design, see `proposed_model.py`.

---

## 3. Entity Resolution Similarity Algorithms

Implemented in `src/laitoxx/shared/graph/entity_resolution.py` using `difflib`.

- **Type Matching**: Returns `0.0` if `n1.node_type != n2.node_type` (since resolving different entity classes is invalid in this domain model).
- **Label Similarity**: Computes similarity using `difflib.SequenceMatcher(None, l1, l2).ratio()` (normalized case/whitespace).
- **Description & Metadata**: If descriptions or shared metadata keys are present, their similarity ratios are also computed.
- **Dynamic Normalization Weighting**: Assigns weights to fields dynamically so that nodes lacking descriptions or metadata are not penalized.

```
Base Weight: Label (0.7)
Optional Weight: Description (0.15)
Optional Weight: Shared Metadata (0.15)
Formula: sum(weight * similarity) / sum(weights)
```

For the full implementation, see `proposed_entity_resolution.py`.

---

## 4. NetworkX Integrations

Implemented in `src/laitoxx/shared/graph/algorithms.py`.

- **`get_shortest_path`**:
  Builds an undirected `networkx.Graph` representing node connectivity. Runs `nx.shortest_path`. If no path is found, or if nodes do not exist, it catches exceptions (`NetworkXNoPath`, `NodeNotFound`) and returns `[]`.
- **`calculate_centralities`**:
  Computes metric-based centralities on the undirected graph. Supports:
  - `"degree"`: Normalized degree centrality (node degree divided by $N-1$).
  - `"betweenness"`: Betweenness centrality.
  - `"closeness"`: Closeness centrality.
  - `"eigenvector"`: Eigenvector centrality (includes error fallback to degree centrality if power iteration does not converge).

For the full implementation, see `proposed_algorithms.py`.

---

## 5. Automated Test Plan (`tests/test_graph_api.py`)

A comprehensive unit test suite has been designed using `pytest` to verify all backend functionality:
1. **Serialization**: Validates that temporal fields serialize/deserialize correctly.
2. **Merging**: Constructs a test scenario with complex metadata, descriptions, dates, and multiple edges to verify correctness of `merge_nodes`.
3. **Similarity**: Verifies `EntityResolver` behaves correctly under matching/mismatched labels, metadata, and different types.
4. **Graph Algorithms**: Tests shortest path calculations (including disconnected case) and degree centrality metrics.

For the complete planned test code, see `proposed_test_graph_api.py`.

---

## 6. GUI Window Capitalization Discrepancy

### Location of Discrepancy
In `src/laitoxx/features/utilities/metadata_viewer/gui_window.py` (lines 327-360), the metadata exporter instantiates `Node` and `Edge` objects:
- It passes lowercase node types `"document"`, `"person"`, `"custom"`.
- It passes `"default"` as the `edge_type`.
- It passes `shape="hexagon"` to the `Node` constructor.

### Root Cause
1. `model.py` defines capitalized types: `"Document"`, `"Person"`, `"Custom"`. Lowercase values bypass styling configs in `NODE_TYPE_DEFAULTS` and fail comparisons.
2. `Edge` default type is `"Connected"`, and `"default"` is not in `EDGE_TYPES`.
3. `Node` class does not have a `shape` field; the correct dataclass attribute is `mermaid_shape`. Passing `shape` causes a `TypeError` crash.

### Resolution
A diff patch (`gui_window.patch`) has been created to:
1. Capitalize `"Document"`, `"Person"`, and `"Custom"`.
2. Map edge types to `"Connected"`.
3. Replace the invalid `shape="hexagon"` parameter with `mermaid_shape="hexagon"`.
