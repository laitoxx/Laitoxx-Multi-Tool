# OSINT Graph Visualization & Extraction Upgrade Report

This report provides a comprehensive codebase exploration and architectural blueprint for the OSINT upgrades.

---

## 1. Core Component Locations
- **`QWebEngineView` & `_center_panel`**:
  - Located in `src/laitoxx/interfaces/gui/graph_editor.py`.
  - `QWebEngineView` and `QWebChannel` are conditionally imported from `PyQt6.QtWebEngineWidgets` and `PyQt6.QtWebChannel` inside a `try...except` block (lines 24-29). If missing, `HAS_WEB` is set to `False`.
  - `_center_panel` is constructed as a `GlassPanel` via `self._build_center_panel()` (lines 1402-1432). It acts as the container layout holding `self._mermaid_view` (which displays the HTML graph inside `QWebEngineView`) and `self._raw_code` (a `QTextEdit` displaying raw markdown).
- **`Graph`, `Node`, and `Edge` models**:
  - Defined in `src/laitoxx/shared/graph/model.py`.
  - `Node` (line 81) is a data class storing ID, label, type, description, metadata dictionary, and Mermaid styling/shape tokens.
  - `Edge` (line 128) represents relationship arrows, line styles, and metadata.
  - `Graph` (line 167) manages a list of node and edge objects and coordinates serialize/deserialize operations.
- **Mermaid.js**:
  - The codebase does NOT actually execute Mermaid.js for drawing.
  - Instead, `src/laitoxx/shared/graph/mermaid.py` provides `generate_mermaid(graph)` (generating raw text for the code preview sidebar) and `generate_html(graph)` which outputs an HTML page that loads **D3.js v7** from a CDN (`https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js`) and renders a custom force-directed interactive SVG.

---

## 2. Metadata Extraction & Node Mapping
- **`MetadataEngine`**:
  - Defined in `src/laitoxx/features/utilities/metadata_viewer/engine.py` (line 86). It uses PyExiv2, Mutagen, TinyTag, OleFile, PEFile, PDFiD, Hachoir, and Kreuzberg to extract metadata fields.
- **Document & Person Node Mapping**:
  - Export logic is in `src/laitoxx/features/utilities/metadata_viewer/gui_window.py` in `_export_to_graph` (lines 283-364).
  - It creates file nodes and author nodes:
    ```python
    file_node = Node(id=str(uuid.uuid4()), label=..., node_type="document")
    ...
    author_node = Node(id=str(uuid.uuid4()), label=..., node_type="person")
    ```
  - **Identified Bug / Discrepancy**: The node types are set as `"document"` and `"person"` (lowercase). However, `NODE_TYPE_DEFAULTS` in `src/laitoxx/shared/graph/model.py` and color keys in `src/laitoxx/shared/graph/mermaid.py` define them with capital letters: `"Document"` and `"Person"`. This casing mismatch prevents extracted metadata nodes from loading correct styling and emoji icons in the renderer.
  - **Proposed Fix**: Change lowercase keys to capitalize matching categories: `"Document"` and `"Person"`.

---

## 3. Testing Setup & Graph API Tests
- **Existing Setup**:
  - No `tests/` directory is present in the root folder, and no Python testing packages (`pytest`) are defined in `requirements.txt`.
- **Test File Location**:
  - Create `/home/vdox/github_repos/Laitoxx-Multi-Tool/tests/` directory.
  - Place `test_graph_api.py` at `/home/vdox/github_repos/Laitoxx-Multi-Tool/tests/test_graph_api.py`.
- **`test_graph_api.py` Structure**:
  ```python
  import pytest
  from unittest.mock import MagicMock
  from laitoxx.app.plugins.engine import HostAPI, LuaPluginMeta
  from laitoxx.shared.graph.model import Graph, Node, Edge

  def test_host_api_graph_operations():
      # Instantiate a dummy plugin metadata and engine host
      meta = LuaPluginMeta("/tmp/dummy.lua", {"id": "test_plugin"})
      lua_mock = MagicMock()
      host = HostAPI(meta, lua_mock)

      # 1. Test graph creation
      graph_id = host.graph_create("OSINT_Test_Graph", "TD")
      assert graph_id is not None
      assert graph_id in host._graphs

      g = host._graphs[graph_id]
      assert g.name == "OSINT_Test_Graph"
      assert g.direction == "TD"

      # 2. Test node addition
      n_id = host.graph_add_node(
          graph_id=graph_id,
          label="John Doe",
          node_type="Person",
          shape="round",
          style="fill:#FFD700",
          description="Investigated Target",
          metadata_table={"Phone": "+12345678"}
      )
      assert n_id is not None
      assert len(g.nodes) == 1
      assert g.nodes[0].id == n_id
      assert g.nodes[0].label == "John Doe"
      assert g.nodes[0].node_type == "Person"
      assert g.nodes[0].metadata == {"Phone": "+12345678"}

      # 3. Test edge linking
      doc_id = host.graph_add_node(graph_id, "Evidence.pdf", "Document")
      edge_id = host.graph_add_edge(graph_id, n_id, doc_id, "created", "Owns", "-->")
      assert edge_id is not None
      assert len(g.edges) == 1
      assert g.edges[0].source_id == n_id
      assert g.edges[0].target_id == doc_id
  ```

---

## 4. JS Bundling & Two-Way QWebChannel Communication
- **vis-network.min.js Bundling**:
  - Save `vis-network.min.js` to `/home/vdox/github_repos/Laitoxx-Multi-Tool/resources/js/vis-network.min.js`.
  - Add `JS_DIR = _rel("resources", "js")` in `src/laitoxx/core/settings/paths.py`.
  - Serve files by initializing `QWebEngineView` with a base URL of the resources folder. In `src/laitoxx/interfaces/gui/graph_editor.py` inside `render_graph`:
    ```python
    from PyQt6.QtCore import QUrl
    import os
    from laitoxx.core.settings.paths import RESOURCES_DIR
    
    # Set the local files path as base url so relative script tags resolve
    base_url = QUrl.fromLocalFile(os.path.abspath(RESOURCES_DIR) + "/")
    self._web.setHtml(html_content, base_url)
    ```
  - In the HTML output, reference it as `<script src="js/vis-network.min.js"></script>`.
- **Two-Way Python-JS Bridge (QWebChannel)**:
  1. Define a backend bridge in `src/laitoxx/interfaces/gui/graph_editor.py`:
     ```python
     class GraphWebBridge(QObject):
         node_selected = pyqtSignal(str)
         edge_selected = pyqtSignal(str)
         context_menu_requested = pyqtSignal(str, str, int, int) # type, id, x, y

         @pyqtSlot(str)
         def onNodeSelected(self, node_id: str):
             self.node_selected.emit(node_id)

         @pyqtSlot(str)
         def onEdgeSelected(self, edge_id: str):
             self.edge_selected.emit(edge_id)

         @pyqtSlot(str, str, int, int)
         def onContextMenu(self, item_type: str, item_id: str, x: int, y: int):
             self.context_menu_requested.emit(item_type, item_id, x, y)
     ```
  2. Bind the bridge in `MermaidView.__init__`:
     ```python
     self._bridge = GraphWebBridge()
     self._channel = QWebChannel(self._web.page())
     self._channel.registerObject("bridge", self._bridge)
     self._web.page().setWebChannel(self._channel)
     ```
  3. In the HTML JS side, configure listeners:
     ```javascript
     new QWebChannel(qt.webChannelTransport, function(channel) {
         window.bridge = channel.objects.bridge;
     });

     // Link Vis-Network events to PyQt signals
     network.on("selectNode", function(params) {
         if (window.bridge && params.nodes.length > 0) {
             window.bridge.onNodeSelected(params.nodes[0]);
         }
     });
     network.on("oncontext", function(params) {
         params.event.preventDefault();
         const node = network.getNodeAt(params.pointer.DOM);
         const edge = network.getEdgeAt(params.pointer.DOM);
         if (window.bridge) {
             if (node) {
                 window.bridge.onContextMenu("node", node, params.pointer.DOM.x, params.pointer.DOM.y);
             } else if (edge) {
                 window.bridge.onContextMenu("edge", edge, params.pointer.DOM.x, params.pointer.DOM.y);
             } else {
                 window.bridge.onContextMenu("background", "", params.pointer.DOM.x, params.pointer.DOM.y);
             }
         }
     });
     ```
  4. Send updates from Python to JS:
     - Execute `self._web.page().runJavaScript(f"updateTimeFilter('{start}', '{end}')")` or similar script actions directly.

---

## 5. API & Algorithm Implementations

### A. Entity Resolution (ER) API
Create `src/laitoxx/shared/graph/entity_resolution.py`:
- Use `difflib.SequenceMatcher` from Python's standard library to calculate string similarity.
- Consolidate matching metadata and merge edge links:
```python
from difflib import SequenceMatcher
from laitoxx.shared.graph.model import Graph, Node

class EntityResolver:
    @staticmethod
    def compute_similarity(n1: Node, n2: Node) -> float:
        if n1.node_type != n2.node_type:
            return 0.0
        # Check label similarity
        ratio = SequenceMatcher(None, n1.label.lower().strip(), n2.label.lower().strip()).ratio()
        
        # Check metadata match (e.g. same phone or email gives boost)
        for k, v in n1.metadata.items():
            if k in n2.metadata and v == n2.metadata[k] and v:
                return max(ratio, 0.95)
        return ratio

    def find_duplicates(self, graph: Graph, threshold: float = 0.8) -> list[dict]:
        nodes = graph.nodes
        duplicates = []
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                sim = self.compute_similarity(nodes[i], nodes[j])
                if sim >= threshold:
                    duplicates.append({
                        "node1": nodes[i],
                        "node2": nodes[j],
                        "similarity": sim
                    })
        return duplicates

    def merge_entities(self, graph: Graph, primary_id: str, duplicate_ids: list[str]) -> Graph:
        primary = next((n for n in graph.nodes if n.id == primary_id), None)
        if not primary:
            return graph

        for dup_id in duplicate_ids:
            dup = next((n for n in graph.nodes if n.id == dup_id), None)
            if not dup:
                continue
            # Concat description
            if dup.description:
                primary.description = f"{primary.description} | {dup.description}" if primary.description else dup.description
            # Merge metadata dict
            for k, v in dup.metadata.items():
                if k not in primary.metadata:
                    primary.metadata[k] = v

        # Relink edges
        for edge in graph.edges:
            if edge.source_id in duplicate_ids:
                edge.source_id = primary_id
            if edge.target_id in duplicate_ids:
                edge.target_id = primary_id

        # Clean duplicate nodes
        graph.nodes = [n for n in graph.nodes if n.id not in duplicate_ids]
        
        # De-duplicate edges
        seen = set()
        unique_edges = []
        for e in graph.edges:
            key = (e.source_id, e.target_id, e.label)
            if key not in seen:
                seen.add(key)
                unique_edges.append(e)
        graph.edges = unique_edges
        return graph
```

### B. NetworkX Analytics Integration
Create `src/laitoxx/shared/graph/algorithms.py`:
```python
import networkx as nx
from laitoxx.shared.graph.model import Graph

def to_networkx(graph: Graph) -> nx.Graph:
    g = nx.Graph()
    for n in graph.nodes:
        g.add_node(n.id)
    for e in graph.edges:
        g.add_edge(e.source_id, e.target_id, id=e.id)
    return g

def calculate_centralities(graph: Graph, metric: str = "degree") -> dict[str, float]:
    g = to_networkx(graph)
    if not g.nodes:
        return {}
    if metric == "degree":
        return nx.degree_centrality(g)
    elif metric == "betweenness":
        return nx.betweenness_centrality(g)
    elif metric == "closeness":
        return nx.closeness_centrality(g)
    elif metric == "eigenvector":
        try:
            return nx.eigenvector_centrality(g, max_iter=1000)
        except Exception:
            return nx.degree_centrality(g)
    return {}

def get_shortest_path(graph: Graph, src_id: str, dst_id: str) -> list[str]:
    g = to_networkx(graph)
    try:
        return nx.shortest_path(g, source=src_id, target=dst_id)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []
```
- **Front-End Integration**:
  - *Shortest Path*: Triggered when 2 nodes are selected. Calculates shortest path in Python, then executes `self._web.page().runJavaScript(f"highlightPath({node_ids_list})")` which dims other nodes by reducing opacity.
  - *Centrality*: Computed in Python, and the resulting node size mapping is pushed to Vis-Network to dynamically scale node sizes in the browser view.

### C. Temporal Slider / Filter
- **Data Model**: Add `timestamp: Optional[str] = None` parameter to `Node` and `Edge` classes in `model.py` (stores ISO-8601 timestamps like `"2026-06-11T12:00:00Z"`).
- **UI Widget**: Add a range slider widget (e.g. dual-slider or date picker combo) at the bottom of the center graph view panel.
- **JS Filtering (Highly performant, no reload)**:
  - PyQt calls `filterByTimeRange(start_iso, end_iso)` on the web page.
  - In JS, we use a `vis.DataView` to update the visibility filter dynamically:
    ```javascript
    const nodesView = new vis.DataView(nodes, {
        filter: function(item) {
            if (!item.timestamp) return true;
            const itemTime = new Date(item.timestamp);
            if (startTime && itemTime < startTime) return false;
            if (endTime && itemTime > endTime) return false;
            return true;
        }
    });
    ```
  - Vis-Network instantly hides excluded items while keeping node positioning and force simulation intact.

---

## 6. Milestone Decomposition & Interface Contracts

### Milestone 1: Backend Model Updates & Unit Testing
- **Deliverables**:
  - Add `timestamp` and `created_at` parameters to `Node` and `Edge` data models.
  - Fix lowercase/uppercase discrepancies (`"person"`/`"document"` mapping) in `gui_window.py`.
  - Create the `tests/` directory and populate `tests/test_graph_api.py`.
- **Interface Contract**:
  - `Node(id, label, node_type, timestamp=None, ...)`
  - `Edge(id, source_id, target_id, label, timestamp=None, ...)`

### Milestone 2: Vis-Network Rendering & QWebChannel Bridge
- **Deliverables**:
  - Bundle `vis-network.min.js` in `resources/js/`.
  - Update `paths.py` with `JS_DIR` and load resources using local `base_url` resolution.
  - Implement the `GraphWebBridge` QObject class in `graph_editor.py`.
  - Update `MermaidView` to render the Vis-Network template instead of D3.js.
- **Interface Contract**:
  - `@pyqtSlot` actions: `onNodeSelected(node_id)`, `onEdgeSelected(edge_id)`, `onContextMenu(type, id, x, y)`.

### Milestone 3: Entity Resolution Engine & GUI Dialog
- **Deliverables**:
  - Write `entity_resolution.py` using `difflib.SequenceMatcher`.
  - Build the Entity Resolution GUI Dialog to let users review merge candidates, resolve values, and commit merges.
- **Interface Contract**:
  - `EntityResolver.find_duplicates(graph, threshold) -> list[dict]`
  - `EntityResolver.merge_entities(graph, primary_id, duplicate_ids) -> Graph`

### Milestone 4: NetworkX Analytics Sidebar & Highlighting
- **Deliverables**:
  - Write `algorithms.py` wrapping NetworkX methods.
  - Add an "Analytics" tab in the right-hand panel of the Graph Editor.
  - Implement Shortest Path computation and visual path highlighting.
  - Implement Centrality-based node scaling.
- **Interface Contract**:
  - `calculate_centralities(graph, metric) -> dict[str, float]`
  - `get_shortest_path(graph, src_id, dst_id) -> list[str]`

### Milestone 5: Timeline Slider & Visual Playback
- **Deliverables**:
  - Add PyQt slider widget at the bottom of `_center_panel`.
  - Add time-based filtering `DataView` logic in the HTML script.
  - Build playback buttons (Play, Pause, Speed) to animate graph growth over time.
- **Interface Contract**:
  - `filterByTimeRange(start_iso, end_iso)` JS endpoint.

---

## Verification Method
1. **API Tests**:
   - Run `python3 -m pytest tests/test_graph_api.py` to verify node/edge APIs.
2. **Metadata Export Integration**:
   - Extract metadata from files using the GUI, export to Graph Editor, and verify that icons and colors display correctly without case mismatch failures.
3. **Offline Visual Check**:
   - Disable internet access, run `python3 start.py`, launch the Graph Editor, and verify that Vis-Network loads and operates normally without CDN resource warnings.
