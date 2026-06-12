# Handoff Report: Milestone 2 — Vis-network rendering & WebChannel Bridge

## 1. Observation

During static analysis, the following relevant architectures and code structures were directly observed in the codebase:

### A. Graph Rendering Architecture
Currently, `src/laitoxx/shared/graph/mermaid.py` generates D3.js-based force-directed SVG graphs using CDNs.
* **External D3.js Fetch**: Line 331 of `src/laitoxx/shared/graph/mermaid.py` fetches D3.js:
  ```html
  331: <script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
  ```
* **Existing QWebChannel Script**: Line 330 of `src/laitoxx/shared/graph/mermaid.py` registers QWebChannel:
  ```html
  330: <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
  ```
* **Current Bridge Setup (JS side)**: Lines 335-340 of `src/laitoxx/shared/graph/mermaid.py` initialize the bridge:
  ```javascript
  335: let BRIDGE = null;
  336: if (window.qt && window.qt.webChannelTransport) {
  337:   new QWebChannel(qt.webChannelTransport, function(channel) {
  338:     BRIDGE = channel.objects.bridge || null;
  339:   });
  340: }
  ```
* **Current D3 Context Menu Callbacks (JS side)**: Lines 595-609 of `src/laitoxx/shared/graph/mermaid.py`:
  ```javascript
  595: function onNodeContextMenu(event, d) {
  596:   event.preventDefault();
  597:   event.stopPropagation();
  598:   if (BRIDGE && BRIDGE.onNodeContext) {
  599:     BRIDGE.onNodeContext(String(d.id), Math.round(event.clientX), Math.round(event.clientY));
  600:   }
  601: }
  602: 
  603: svg.on('contextmenu', (event) => {
  604:   if (event.defaultPrevented) return;
  605:   event.preventDefault();
  606:   if (BRIDGE && BRIDGE.onBackgroundContext) {
  607:     BRIDGE.onBackgroundContext(Math.round(event.clientX), Math.round(event.clientY));
  608:   }
  609: });
  ```

### B. Python Web Bridge Architecture
The bridge object is set up inside `MermaidView` in `src/laitoxx/interfaces/gui/graph_editor.py`.
* **Bridge QObject and Slots**: Lines 962-972 of `src/laitoxx/interfaces/gui/graph_editor.py`:
  ```python
  962:     class _GraphWebBridge(QObject):
  963:         node_context = pyqtSignal(str, int, int)
  964:         background_context = pyqtSignal(int, int)
  965: 
  966:         @pyqtSlot(str, int, int)
  967:         def onNodeContext(self, node_id: str, x: int, y: int):
  968:             self.node_context.emit(node_id, x, y)
  969: 
  970:         @pyqtSlot(int, int)
  971:         def onBackgroundContext(self, x: int, y: int):
  972:             self.background_context.emit(x, y)
  ```
* **Channel Registration**: Lines 984-989 of `src/laitoxx/interfaces/gui/graph_editor.py`:
  ```python
  984:             self._bridge = MermaidView._GraphWebBridge()
  985:             self._channel = QWebChannel(self._web.page())
  986:             self._channel.registerObject("bridge", self._bridge)
  987:             self._web.page().setWebChannel(self._channel)
  988:             self._bridge.node_context.connect(self.node_context_requested.emit)
  989:             self._bridge.background_context.connect(self.background_context_requested.emit)
  ```
* **Main GUI Integration**: In `GraphEditor._build_center_panel` (lines 1410-1412):
  ```python
  1410:         self._mermaid_view = MermaidView()
  1411:         self._mermaid_view.node_context_requested.connect(self._on_graph_node_context)
  1412:         self._mermaid_view.background_context_requested.connect(self._on_graph_background_context)
  ```

### C. GUI Action and Selection Triggers
* **Selection Slots**: Lines 2133-2147 of `src/laitoxx/interfaces/gui/graph_editor.py`:
  ```python
  2133:     def _on_node_selected(self, current, previous):
  ...
  2137:         node = self._graph.get_node(current.data(Qt.ItemDataRole.UserRole))
  2138:         self._node_props.load_node(node)
  ...
  2141:     def _on_edge_selected(self, current, previous):
  ...
  2145:         edge = self._graph.get_edge(current.data(Qt.ItemDataRole.UserRole))
  2146:         self._edge_props.load_edge(edge, self._graph)
  ```

---

## 2. Logic Chain

The reasoning from these observations to our recommended implementation plan is as follows:

1. **Local Bundling of JS**: 
   - Since standard external fetches fail under network restrictions (refer to Requirement 1), fetching D3.js/Vis-network via a CDN at runtime is unreliable. 
   - A download script (e.g., `scripts/download_vis_network.py`) must be executed beforehand (or as a fallback command) to save the file to `resources/js/vis-network.min.js`.
   - If the downloader fails due to strict offline environments, it must write a mock/placeholder script setting a fallback flag (`window.VIS_NETWORK_FALLBACK = true`) so the HTML context loads without javascript runtime crash.
   
2. **Dynamic Inlining vs Relative URLs**:
   - QWebEngineView blocks access to local `file:///` assets from pages loaded with non-file schemes (like `about:blank`).
   - To make the HTML rendering context robust across different absolute workspace paths and OS platforms, Python should read the local `vis-network.min.js` file (using fallback search paths) and dynamically inline the content into the generated HTML.
   - If the file is missing or unreadable, the HTML can fall back to loading from CDN or display a beautiful, translucent warning screen notifying the user to check their offline package status.

3. **Bridge Interception Upgrade**:
   - The current `_GraphWebBridge` in `graph_editor.py` only listens for context menus on nodes/background.
   - Requirement 3 states the bridge needs to handle:
     * `onNodeSelected(node_id: str)`
     * `onEdgeSelected(edge_id: str)`
     * `onContextMenu(item_type: str, item_id: str, x: int, y: int)`
   - Therefore, the PyQt bridge must expose three slots matching these signatures.
   - On the JS side, Vis-network interaction events (`click`, `oncontext`) must be mapped to call these bridge methods.
   - On the PyQt side, selection signals must be connected to find the corresponding items in `_nodes_list` and `_edges_list` and set them as the current item. This automatically populates the properties panel.

4. **Vis-network Layout and Styling**:
   - Vis-network's physics engine (`forceAtlas2Based` or `barnesHut`) must be configured to emulate D3's force-directed layout.
   - The theme colors (e.g. `_TYPE_COLORS` map) and node sizes proportional to connection degree must be mapped to Vis-network options.
   - Highlight and dim operations (neighbor selections) should update the Vis-network `DataSet` dynamically to preserve glassmorphic opacity and glow.

---

## 3. Caveats

* **QWebEngine Profile Sandbox**: If QWebEngine is run on systems with strict CORS constraints, inlining remains the only safe way to load local scripts. If standard file paths are preferred, the base URL of `QWebEngineView.setHtml` must be modified to use `QUrl.fromLocalFile(os.path.abspath("resources/js/"))`. We suggest inlining as the primary strategy and base URL as the backup.
* **Placeholder behavior**: When offline and the downloader fails, the placeholder script prevents application crashes but will not display the graph. The user is prompted via a clear HTML message.
* **Performance of dataset updates**: Dynamic updates of neighbor opacities on hover work well for standard graph sizes (up to 1,000 nodes). For extremely large graphs (>5,000 nodes), this can cause slight rendering lag on low-end machines.

---

## 4. Conclusion

Milestone 2 can be cleanly implemented without changing the core graph models. The recommended strategy is:

### A. Add Downloader Script: `scripts/download_vis_network.py`
Create a helper script that downloads `vis-network.min.js` using `urllib` to `resources/js/vis-network.min.js` and creates a fallback/placeholder file if offline.

```python
import os
import urllib.request

URLS = [
    "https://unpkg.com/vis-network/standalone/umd/vis-network.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/standalone/umd/vis-network.min.js"
]

def get_library():
    path = os.path.abspath("resources/js/vis-network.min.js")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as res:
                with open(path, "wb") as f:
                    f.write(res.read())
            print("Successfully downloaded vis-network!")
            return
        except Exception as e:
            print(f"Failed {url}: {e}")
    # Fallback writing
    with open(path, "w", encoding="utf-8") as f:
        f.write('window.VIS_NETWORK_FALLBACK = true; console.error("vis-network is a fallback.");')
```

### B. Update HTML Generation in `src/laitoxx/shared/graph/mermaid.py`
1. Read the contents of `resources/js/vis-network.min.js` using fallback paths.
2. Inline `vis-network.min.js` inside the `<head>`.
3. Provide a fallback DOM element and a check at runtime: `if (window.VIS_NETWORK_FALLBACK) { showWarningScreen(); }`.
4. Render the graph using `vis.Network(container, data, options)` with custom options:
   * Node shapes corresponding to `n['shape']`.
   * Colors corresponding to type color.
   * Emojis prefixed inside node labels (`label: n.icon + " " + n.label`).
   * Widths and dash styles of edges configured according to `edge['stroke']` and `edge['dash']`.
5. Implement Javascript event listeners for selection and context menus:
   ```javascript
   // Selection
   network.on("click", function (params) {
     if (params.nodes.length > 0) {
       if (BRIDGE) BRIDGE.onNodeSelected(String(params.nodes[0]));
     } else if (params.edges.length > 0) {
       if (BRIDGE) BRIDGE.onEdgeSelected(String(params.edges[0]));
     }
   });
   
   // Context Menu
   network.on("oncontext", function (params) {
     params.event.preventDefault();
     params.event.stopPropagation();
     const pos = params.pointer.DOM;
     const nodeId = network.getNodeAt(pos);
     const edgeId = network.getEdgeAt(pos);
     
     let type = "background";
     let id = "";
     if (nodeId !== undefined) {
       type = "node";
       id = String(nodeId);
     } else if (edgeId !== undefined) {
       type = "edge";
       id = String(edgeId);
     }
     
     if (BRIDGE) {
       BRIDGE.onContextMenu(type, id, Math.round(params.event.clientX), Math.round(params.event.clientY));
     }
   });
   ```

### C. Update Python Bridge in `src/laitoxx/interfaces/gui/graph_editor.py`
1. Re-implement `_GraphWebBridge` inside `MermaidView`:
   ```python
   class _GraphWebBridge(QObject):
       node_selected = pyqtSignal(str)
       edge_selected = pyqtSignal(str)
       context_menu_requested = pyqtSignal(str, str, int, int) # item_type, item_id, x, y

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
2. In `GraphEditor.__init__` (or `_build_center_panel`), hook up the signals:
   ```python
   self._mermaid_view.node_selected.connect(self._on_graph_node_selected)
   self._mermaid_view.edge_selected.connect(self._on_graph_edge_selected)
   self._mermaid_view.context_menu_requested.connect(self._on_graph_context_menu)
   ```
3. Implement selection synchronization:
   ```python
   def _on_graph_node_selected(self, node_id: str):
       for i in range(self._nodes_list.count()):
           item = self._nodes_list.item(i)
           if item.data(Qt.ItemDataRole.UserRole) == node_id:
               self._nodes_list.setCurrentItem(item)
               break

   def _on_graph_edge_selected(self, edge_id: str):
       for i in range(self._edges_list.count()):
           item = self._edges_list.item(i)
           if item.data(Qt.ItemDataRole.UserRole) == edge_id:
               self._edges_list.setCurrentItem(item)
               break
   ```
4. Map the unified `_on_graph_context_menu`:
   ```python
   def _on_graph_context_menu(self, item_type: str, item_id: str, x: int, y: int):
       if item_type == "node":
           self._on_graph_node_context(item_id, x, y)
       elif item_type == "edge":
           self._on_graph_edge_context(item_id, x, y)
       elif item_type == "background":
           self._on_graph_background_context(x, y)
   ```
   Add a custom `_show_edge_context_menu(self, edge, global_pos)` and mapping slot for edge context menus to complete context menu coverage.

---

## 5. Verification Method

To verify the integration:
1. **Model/HTML Structure Test**:
   Write a small unit test in `tests/test_vis_rendering.py` that generates a mock graph, calls `generate_html(graph)`, and asserts the generated HTML structure.
   ```python
   def test_vis_html_structure():
       from laitoxx.shared.graph.model import Graph, Node
       from laitoxx.shared.graph.mermaid import generate_html
       g = Graph("Test")
       g.add_node(Node(id="n1", label="Test Node", node_type="Person"))
       html = generate_html(g)
       assert "vis.Network" in html
       assert "bridge.onNodeSelected" in html
       assert "bridge.onContextMenu" in html
   ```
   Run using:
   ```bash
   python3 -m pytest tests/test_vis_rendering.py
   ```

2. **Downloader Verification**:
   Execute `python3 scripts/download_vis_network.py`. Confirm `resources/js/vis-network.min.js` is created. Disconnect network, delete file, and re-run to confirm fallback placeholder generation.

3. **GUI Interactive Verification**:
   Start Laitoxx with `python3 start.py`. Open the Graph Editor. Right click nodes/edges/background and verify PyQt context menus pop up at correct coordinates. Left-click nodes/edges and verify details appear in the right properties sidebar.
