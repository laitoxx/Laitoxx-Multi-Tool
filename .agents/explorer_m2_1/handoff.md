# Handoff Report - Milestone 2 (Vis-network rendering & WebChannel Bridge)

This report details the requirements analysis, architecture, design decisions, and concrete code changes required to transition the LAITOXX multi-tool graph rendering from D3.js/Mermaid to Vis-network.

---

## 1. Observation
We observed the existing codebase structure and dependencies as follows:
- **`src/laitoxx/shared/graph/mermaid.py`** currently exports `generate_mermaid` (Mermaid string) and `generate_html` (interactive D3.js v7 visualization).
  - Lines 330-332 of `mermaid.py`:
    ```html
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
    <script>
    const DATA = {graph_json};
    ```
- **`src/laitoxx/interfaces/gui/graph_editor.py`** initializes `MermaidView` with a QWebEngineView and registers a basic communication bridge.
  - Lines 958-989 of `graph_editor.py`:
    ```python
    class MermaidView(QWidget):
        node_context_requested = pyqtSignal(str, int, int)  # node_id, x, y (client coords)
        background_context_requested = pyqtSignal(int, int)  # x, y (client coords)

        class _GraphWebBridge(QObject):
            node_context = pyqtSignal(str, int, int)
            background_context = pyqtSignal(int, int)

            @pyqtSlot(str, int, int)
            def onNodeContext(self, node_id: str, x: int, y: int):
                self.node_context.emit(node_id, x, y)

            @pyqtSlot(int, int)
            def onBackgroundContext(self, x: int, y: int):
                self.background_context.emit(x, y)
    ```
- **`requirements.txt`** contains `PyQt6` and `PyQt6-WebEngine`, but does not include any Python vis-network bindings (such as `pyvis`). It lists `networkx` for backend graph logic.
- **`resources`** directory currently contains `background/`, `icons/`, and `themes/` subdirectories. It does not contain a `js` subdirectory or `vis-network.min.js`.
- The environment is operated under network-restricted sandboxing, meaning runtime standard fetches to external CDN endpoints (e.g. jsdelivr, unpkg) inside QWebEngineView will fail, necessitating local bundling of `vis-network.min.js`.

---

## 2. Logic Chain
1. **Local Bundling & CDN Fallback Strategy**:
   - Because standard external CDNs will fail to resolve under network sandboxing (see Observation 5), we need `vis-network.min.js` to be stored locally under `resources/js/vis-network.min.js`.
   - We must design a setup script (`proposed_fetch_vis.py`) that tries CDNs first (via Python's `urllib` with custom headers), then local `npm install` inside a temporary directory, and falls back to a robust inline JS mock object if all network requests fail.
   - To make page loading resilient to file permission/location changes in different OS platforms and Qt security restrictions, `generate_html` should inline the JS file contents dynamically into the generated HTML.

2. **Vis-network Transition & Styling**:
   - The current GUI relies on node shapes (`rect`, `round`, `circle`, `diamond`, `hexagon`, `flag`, `trapez` - see `src/laitoxx/shared/graph/model.py`), node categories, connection counts (degrees), and accent-coloured edges.
   - Vis-network does not natively display unicode emojis inside non-box node shapes unless a custom canvas context renderer is used.
   - However, using Vis-network's `shape: 'image'` option with dynamically generated SVG data URIs allows us to recreate the exact glassmorphism effects, custom borders, shapes, and center-aligned emojis in high resolution, without loading external asset files.
   - Node degrees can be mapped to the `size` property of Vis-network nodes, automatically scaling the SVG representation.

3. **Bridge Enhancement & Signal Cycle Mitigation**:
   - The requirements specify three JS-to-Python bridge methods: `onNodeSelected(node_id)`, `onEdgeSelected(edge_id)`, and `onContextMenu(item_type, item_id, x, y)`.
   - We can listen to Vis-network's click events (`network.on("click", ...)`) to trigger the selection signals.
   - We can use standard DOM `contextmenu` listener on the canvas container and determine the targeted object using Vis-network's `network.getNodeAt(pointer)` and `network.getEdgeAt(pointer)` methods. This easily distinguishes between node, edge, and background clicks.
   - When a node/edge is selected inside the QWebEngineView and triggers the bridge, the Python GUI must highlight it in the lists (`self._nodes_list` and `self._edges_list`). To prevent a recursive update loop (i.e. Python selection changing trigger WebEngineView selection and vice-versa), we must temporarily call `.blockSignals(True)` on the list widgets while setting their selection programmatically.

---

## 3. Caveats
- If the user's system does not have Python's dependencies installed or PyQt6 fails to bind, the GUI falls back to raw Mermaid text mode. In this mode, the Vis-network code is not loaded.
- Stabilization iterations for Vis-network are capped at 150. For extremely large graphs (e.g. 500+ nodes), stabilization might take slightly longer, but it prevents the nodes from bouncing around randomly on the screen.
- Tooltips are mapped using Vis-network's `hoverNode` and `hoverEdge` events, which dynamically populate the same CSS-styled floating `#tooltip` div used in D3.js. This avoids relying on Vis-network's default HTML tooltips which do not fit the glassmorphism theme.

---

## 4. Conclusion
1. **Downloader**: A standalone Python downloader script `proposed_fetch_vis.py` should be executed prior to launch to write `resources/js/vis-network.min.js` (falling back to a non-crashing Javascript mock constructor if download is completely blocked).
2. **HTML Generation**: `src/laitoxx/shared/graph/mermaid.py` should be replaced with `proposed_mermaid.py`. This implementation reads the local JS file, configures SVG data URIs for all node shapes, and wires up selection and right-click callbacks.
3. **GUI Bridge**: `src/laitoxx/interfaces/gui/graph_editor.py` should have the communication bridge slot methods and programmatic list selection logic added, as defined in `graph_editor.patch`.

---

## 5. Verification Method
1. **Download Verification**:
   - Run the fetch script:
     ```bash
     python3 .agents/explorer_m2_1/proposed_fetch_vis.py
     ```
   - Verify that `resources/js/vis-network.min.js` is created and contains the library or the mock fallback script.
2. **Integration Verification**:
   - Implementers should apply the `graph_editor.patch` using:
     ```bash
     git apply .agents/explorer_m2_1/graph_editor.patch
     ```
   - Copy `proposed_mermaid.py` over to the target path:
     ```bash
     cp .agents/explorer_m2_1/proposed_mermaid.py src/laitoxx/shared/graph/mermaid.py
     ```
3. **Execution**:
   - Run the application:
     ```bash
     python3 start.py
     ```
   - Open the Graph Editor. Verify that the graph renders with force-directed physics.
   - Verify that clicking a node highlights it in the left-hand panel and displays its attributes in the right-hand panel.
   - Verify that right-clicking a node or background brings up the respective Qt context menus at the exact cursor position.
4. **Backend Test Command**:
   - Run unit tests to verify backend models:
     ```bash
     pytest tests/test_graph_api.py
     ```
