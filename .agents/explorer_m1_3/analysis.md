# Milestone 1: Backend Models, Algorithms & Test Design

This report contains the structured analysis and complete designs for the Laitoxx Graph Editor OSINT upgrades under Milestone 1.

---

## 1. Temporal Fields Design (`src/laitoxx/shared/graph/model.py`)
To support temporal filtering of nodes and edges via the PyQt timeline slider widget, we introduce optional `valid_from` and `valid_to` string attributes (ISO-8601 strings or `None`) to the `Node` and `Edge` classes. 

### Node Model Additions
- Added `valid_from: Optional[str] = None` and `valid_to: Optional[str] = None` properties.
- Updated `to_dict()` and `from_dict()` for full serialization/deserialization.

```python
@dataclass
class Node:
    label: str
    node_type: str = "Custom"
    description: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    # Mermaid display
    mermaid_shape: str = "[]"
    mermaid_style: str = ""
    # Temporal fields
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    # Internal
    id: str = field(default_factory=lambda: f"N{uuid.uuid4().hex[:6].upper()}")

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
            valid_from=d.get("valid_from", None),
            valid_to=d.get("valid_to", None),
        )
        n.id = d.get("id", n.id)
        return n
```

### Edge Model Additions
- Added identical fields to `Edge` and updated serialization routines similarly.

```python
@dataclass
class Edge:
    source_id: str
    target_id: str
    label: str = ""
    edge_type: str = "Connected"
    metadata: dict[str, str] = field(default_factory=dict)
    # Mermaid display
    mermaid_line: str = "-->"
    mermaid_style: str = ""
    # Temporal fields
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    # Internal
    id: str = field(default_factory=lambda: f"E{uuid.uuid4().hex[:6].upper()}")
```

Refer to `model.patch` in our agent directory for the exact patch payload.

---

## 2. Node Merging Design (`Graph.merge_nodes`)
The `Graph.merge_nodes(primary_id: str, duplicate_ids: list[str]) -> None` method is designed to safely fold duplicate nodes into a primary node, resolving metadata conflicts, combining descriptions, re-routing edges, and deduplicating them.

### Algorithm Steps:
1. **Validation**: Retrieve primary node from graph. If not found, raise a `ValueError`.
2. **Metadata Combination**: Iterate through valid duplicate nodes:
   - **Descriptions**: Concatenated using a newline `"\n"` character if both are non-empty.
   - **Metadata Table**: If a key does not exist on primary, insert it. If it exists but has a different value, combine values using `", "`.
   - **Temporal Bounds**: Broaden the temporal range of the primary node by keeping the earliest `valid_from` and the latest `valid_to`.
3. **Edge Re-routing**: Update all edge `source_id` and `target_id` references that point to duplicate node IDs to point to the `primary_id`.
4. **Edge Deduplication**: Scan all edges. Deduplicate edges that share the same `(source_id, target_id, edge_type, label)`. For duplicate edges:
   - Combine their metadata keys (concatenating conflicts).
   - Resolve temporal fields (`valid_from` / `valid_to`) using the broadened range strategy.
5. **Clean up**: Remove duplicate nodes from the `self.nodes` list.

---

## 3. Entity Resolution API Design (`entity_resolution.py`)
Entity Resolution computes the similarity between two nodes and discovers duplicate clusters.

### Similarity Calculation (`compute_similarity`):
- Returns a float score between `0.0` and `1.0`.
- **Type Check**: Nodes of different types cannot be duplicates (returns `0.0`).
- **Label Match**: Utilizes `difflib.SequenceMatcher` on lowercase, stripped node labels.
- **Metadata Booster**: If the nodes share identical values for critical OSINT keys (e.g., `Phone`, `Email`, `IP`, `Username`, `Address`, `Website`, `SocialAccount`), the similarity is boosted to at least `0.95`.

### Duplicate Cluster Finder (`find_duplicates`):
- Checks all unique node pairs in the graph.
- Pairs with a similarity score >= the specified `threshold` are returned.
- Results are sorted in descending order of similarity.

---

## 4. NetworkX Analytics Integration Design (`algorithms.py`)
Integrates NetworkX to run graph calculations in Python.

- **Conversion Helper**: Builds an undirected `nx.Graph` from the `Graph` class's nodes and edges.
- **Shortest Path**: Uses `nx.shortest_path`. If no path exists, or if source/target nodes are missing, it catches `nx.NetworkXNoPath` / `nx.NodeNotFound` and returns an empty list `[]`.
- **Centrality calculations**: Calculates centralities for all nodes.
  - Supports metrics: `'degree'`, `'betweenness'`, `'closeness'`, and `'eigenvector'`.
  - Fallback mechanism: Eigenvector centrality uses standard power iteration. In case of convergence failure, it gracefully catches exceptions and falls back to degree centrality.

---

## 5. Test Case Planning (`test_graph_api.py`)
To ensure full coverage and regression testing, we design test cases to verify:
1. **Temporal Serialization**: Test node and edge `to_dict` and `from_dict` when temporal fields are populated vs when they are omitted (`None`).
2. **Node Merging**: 
   - Verify descriptions are combined correctly.
   - Verify metadata keys are merged and conflict values concatenated.
   - Verify edges are correctly re-routed to primary node.
   - Verify that duplicate edges are merged and their metadata consolidated.
   - Verify duplicate nodes are completely deleted from the graph.
3. **Entity Resolution**:
   - Verify that type mismatches return `0.0`.
   - Verify exact matches return `1.0`.
   - Verify label fuzzy matching returns expected ratio bounds.
   - Verify metadata boost triggers when critical keys match.
4. **NetworkX Integrations**:
   - Verify shortest path returns valid lists for connected nodes, and `[]` for disconnected nodes or invalid/non-existent targets.
   - Verify degree centrality assigns higher scores to high-degree hub nodes.
   - Verify fallback mechanism for eigenvector calculation.

---

## 6. GUI Window Capitalization Fix (`gui_window.py`)
A casing mismatch was found in `src/laitoxx/features/utilities/metadata_viewer/gui_window.py` under `_export_to_graph` (lines 330, 341, and 354). 
- Extracted nodes were mapped with lowercase node types (`"document"`, `"person"`, `"custom"`), whereas the graph defaults require capitalized styles (`"Document"`, `"Person"`, `"Custom"`).
- In addition, software node creation attempted to pass `shape="hexagon"` to the `Node` constructor. Because `Node` does not have a `shape` argument (the correct attribute is `mermaid_shape`), this causes an instantiation failure.

### Proposed Fix:
1. Change `"document"` to `"Document"`.
2. Change `"person"` to `"Person"`.
3. Change `"custom"` to `"Custom"`, and replace parameter `shape="hexagon"` with `mermaid_shape="hexagon"`.

Refer to `gui_window.patch` in our agent directory for the exact patch payload.
