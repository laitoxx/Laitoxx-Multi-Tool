# Project: Laitoxx Graph Editor OSINT Upgrade

## Architecture
The Laitoxx Multi-Tool contains a Graph Editor that currently visualizes nodes and edges using D3.js inside a PyQt `QWebEngineView`. The upgrade will transform it into a professional OSINT graph tool:
1. **Frontend Rendering**: Replace the CDN-based D3.js engine with a locally bundled `vis-network.min.js` library.
2. **Python-JS Bridge**: Setup a `QWebChannel` bridge between PyQt (Python) and the HTML rendering context (JS) to allow two-way interactions (node selection, context menu).
3. **Graph Operations & Merging**: Implement Entity Resolution (node merging) within the `Graph` model to combine duplicates and re-route edges cleanly.
4. **Drag-and-Drop metadata extraction**: Dragged files will be intercepted by the UI, analyzed by `MetadataEngine`, mapped to a `Document` node, and linked to author/creator entities.
5. **Temporal Graph Filtering**: Nodes and edges will store `valid_from` and `valid_to` dates. A timeline slider widget in PyQt will filter visible entities dynamically.
6. **NetworkX Algorithms**: Compute Degree Centrality (adjust node sizing) and Shortest Path (highlight path and dim other nodes) in Python using NetworkX and visualize the results.

## Code Layout
- `src/laitoxx/shared/graph/model.py` — Core `Node`, `Edge`, and `Graph` models (to be updated with temporal fields and node merging API)
- `src/laitoxx/shared/graph/entity_resolution.py` — Entity Resolution similarity and merging logic (new module)
- `src/laitoxx/shared/graph/algorithms.py` — NetworkX shortest path and centrality algorithms (new module)
- `src/laitoxx/shared/graph/mermaid.py` — Handles generation of Vis-network HTML and force layout options (to be updated/replaced)
- `src/laitoxx/interfaces/gui/graph_editor.py` — GUI window and glass panels containing `QWebEngineView`, layout, drag-and-drop events, and timeline slider (to be updated)
- `resources/js/vis-network.min.js` — Offline Vis-network javascript bundle (new resource)
- `tests/test_graph_api.py` — Automated unit test script to verify backend APIs (new test file)

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | Backend Models, Algorithms & Tests | Add temporal fields to Node/Edge, implement Node Merge API, write NetworkX helpers, and verify everything with `tests/test_graph_api.py`. | None | DONE |
| 2 | Vis-network rendering & WebChannel Bridge | Bundle `vis-network.min.js` locally. Establish two-way communication using `QWebChannel` and render force-directed physics graph. | M1 | DONE |
| 3 | Drag-and-Drop Metadata Extraction | Intercept drop events on GUI, run `MetadataEngine`, add document/entity nodes to the graph, and update view. | M2 | DONE |
| 4 | Graph Algorithms Integration | Implement UI triggers for Shortest Path and Centrality, executing calculations in NetworkX and rendering the highlighted path/node sizes. | M2 | DONE |
| 5 | Temporal Timeline Slider | Add dual date QSlider to the PyQt interface, filtering visible graph nodes/edges using `valid_from` and `valid_to` bounds. | M2 | DONE |

## Interface Contracts

### Backend Graph Models (`src/laitoxx/shared/graph/model.py`)
- `Node` has optional string attributes: `valid_from` and `valid_to` (ISO-8601 strings or empty/None).
- `Edge` has optional string attributes: `valid_from` and `valid_to`.
- `Graph.merge_nodes(primary_id: str, duplicate_ids: list[str]) -> None`: merging node attributes, descriptions, and re-routing edges without duplicating them.

### Entity Resolution API (`src/laitoxx/shared/graph/entity_resolution.py`)
- `EntityResolver.compute_similarity(n1: Node, n2: Node) -> float`: Returns a similarity ratio between 0.0 and 1.0.
- `EntityResolver.find_duplicates(graph: Graph, threshold: float) -> list[dict]`: Returns a list of potential duplicates (dict with `node1`, `node2`, `similarity`).

### NetworkX Integration (`src/laitoxx/shared/graph/algorithms.py`)
- `get_shortest_path(graph: Graph, source_id: str, target_id: str) -> list[str]`: Returns a list of node IDs forming the shortest path.
- `calculate_centralities(graph: Graph, metric: str = "degree") -> dict[str, float]`: Returns node ID to centrality value dictionary.

### Python-JS Bridge (`src/laitoxx/interfaces/gui/graph_editor.py` ↔ HTML)
- PyQt exposes `bridge` object to the JS page.
- JS calls:
  - `bridge.onNodeSelected(node_id: str)`
  - `bridge.onEdgeSelected(edge_id: str)`
  - `bridge.onContextMenu(item_type: str, item_id: str, x: int, y: int)`
- PyQt runs JavaScript to push updates:
  - `self._web.page().runJavaScript("highlightPath(node_ids)")`
  - `self._web.page().runJavaScript("applyCentralitySizes(sizes_dict)")`
  - `self._web.page().runJavaScript("filterByTimeRange(start_time, end_time)")`
