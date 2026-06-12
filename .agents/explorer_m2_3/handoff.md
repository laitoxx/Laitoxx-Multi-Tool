# Handoff Report: Milestone 2 Implementation Strategy (Vis-network Rendering & WebChannel Bridge)

## 1. Observation
From direct code inspection of the `Laitoxx-Multi-Tool` codebase, we observed the following:

### Existing Architecture for Graph Rendering
* **HTML Generation**: `src/laitoxx/shared/graph/mermaid.py` generates a self-contained HTML page utilizing D3.js v7 loaded via CDN:
  ```html
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
  ```
  It constructs a force-directed graph by rendering SVG elements: nodes as custom D3 paths/symbols (line 469: `nodeEl.append('path')`), outer rings (line 462), text labels (line 492), and curved edge paths (line 504).
* **PyQt Integration**: `src/laitoxx/interfaces/gui/graph_editor.py` defines `MermaidView` which hosts a `QWebEngineView` (lines 980-990):
  ```python
  if HAS_WEB:
      self._web = QWebEngineView()
      self._web.setStyleSheet("border-radius: 10px;")
      self._web.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
      self._bridge = MermaidView._GraphWebBridge()
      self._channel = QWebChannel(self._web.page())
      self._channel.registerObject("bridge", self._bridge)
      self._web.page().setWebChannel(self._channel)
  ```
* **HTML Loader base URL**: When setting HTML content, it currently uses `about:blank` base URL (lines 1010-1014):
  ```python
  def render_graph(self, graph: Graph) -> None:
      if self._web:
          self._web.setHtml(
              generate_html(graph, lang=translator.lang, theme=self._theme),
              QUrl("about:blank"),
          )
  ```
* **QWebChannel Communication**: Currently, the two-way bridge `_GraphWebBridge` only defines context menu slots (lines 962-972):
  ```python
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
* **List Selections & Redraws**: GraphEditor registers selection events on lists (lines 1393: `self._edges_list.currentItemChanged.connect(self._on_edge_selected)` and line 1390 onwards). The lists are populated in `_refresh_nodes_list` and `_refresh_edges_list` with `Node.id`/`Edge.id` stored as `UserRole` data.

---

## 2. Logic Chain

### A. Local Bundling of `vis-network.min.js`
1. **The Issue**: Under `CODE_ONLY` network restrictions, loading `vis-network` from standard CDN endpoints (e.g. `https://unpkg.com/`) at runtime will fail.
2. **Resolution Strategy**: Create a Python script (`scripts/download_vis_network.py`) that tries downloading the library from CDN during setup/build.
3. **Robust Fallback**: If standard requests fail or no internet is available, the script must write a robust JavaScript fallback file to `resources/js/vis-network.min.js`. The fallback script will stub out `window.vis = { Network: ... }` and expose empty implementations of expected methods (e.g., `setData`, `setOptions`, `on`, `off`, `fit`, `focus`, `unselectAll`) and draw a beautiful error banner to prevent the application from throwing JS exceptions and crashing.

### B. Resolving Local Resources in QWebEngineView
1. **The Issue**: By default, QWebEngineView cannot load relative paths to local files (e.g. `resources/js/vis-network.min.js`) when `baseUrl` is set to `QUrl("about:blank")`.
2. **Resolution Strategy**: Change the base URL parameter of `setHtml` to refer to the local directory where the application is running, mapped using `QUrl.fromLocalFile(project_root)`. This allows referencing `resources/js/vis-network.min.js` locally in the HTML template.

### C. JS & Python Communication
1. **The Issue**: Two-way communication needs to cover node selection, edge selection, and context menus for nodes, edges, and background.
2. **Resolution Strategy**:
   - Upgrade `_GraphWebBridge` to expose slots: `onNodeSelected(node_id)`, `onEdgeSelected(edge_id)`, and `onContextMenu(item_type, item_id, x, y)`.
   - On the JS side, register event listeners for clicks on nodes and edges, calling these slots.
   - Listen to the `contextmenu` event, use Vis-network API `network.getNodeAt()` and `network.getEdgeAt()` to identify the right-clicked entity, and forward the request to Python.

---

## 3. Caveats
* **Offline Fallback UI**: If the download fails, the user will see a styled placeholder instead of an interactive network graph, instructing them to run the script. This ensures the app doesn't crash but does notify the user.
* **PyQt6 WebEngine Installation**: Ensure the environment has `PyQt6-WebEngine` installed. If it is missing, `HAS_WEB` will be `False` and the app falls back to raw Mermaid text rendering (which is already implemented and must be preserved).
* **Physics Stability**: Large graphs might take some time to stabilize. A stabilization limit (`stabilization.iterations: 150`) is added to prevent CPU spikes.

---

## 4. Conclusion & Recommended Plan

### A. Download Script (`scripts/download_vis_network.py`)
Propose creating `scripts/download_vis_network.py` with three fallback methods:
1. Fetch from unpkg/cdnjs CDN via `urllib.request.urlretrieve`.
2. Run `npm install vis-network` and copy from `node_modules/vis-network/standalone/umd/vis-network.min.js` if npm is installed.
3. Write a mock/stub javascript file if offline/offline sandbox.

### B. Changes to `src/laitoxx/shared/graph/mermaid.py`
Replace the HTML template within `generate_html` to load `vis-network.min.js` and use Vis-network APIs:

```python
# In src/laitoxx/shared/graph/mermaid.py
# (replace body of generate_html)

def generate_html(graph: Graph, lang: str = None, theme: dict = None) -> str:
    # 1. Translation and Theme Setup (same as current)
    # 2. Construct nodes_data and edges_data JSON (same as current)
    
    # 3. Output Vis-network HTML Template:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  width: 100vw; height: 100vh; overflow: hidden;
  {_h_body_bg}
  font-family: 'Segoe UI', system-ui, sans-serif;
}}
#canvas {{
  width: 100%; height: 100%;
}}
/* Keep styling for Tooltip and Info-panel */
#tooltip {{
  position: fixed; pointer-events: none; background: {_h_bg};
  border: 1px solid {_h_accent}; border-radius: 10px; padding: 10px 14px;
  font-size: 12px; color: {_h_txt_pri}; backdrop-filter: blur(8px);
  max-width: 260px; line-height: 1.6; opacity: 0; transition: opacity 0.18s; z-index: 100;
}}
#tooltip.visible {{ opacity: 1; }}
#tooltip strong {{ color: {_h_accent}; font-size: 13px; }}
#tooltip .tt-type {{ color: {_h_accent2}; font-size: 10px; letter-spacing: 1px; text-transform: uppercase; }}
#tooltip .tt-sep {{ border: none; border-top: 1px solid {_h_bdr}; margin: 6px 0; }}
#tooltip .tt-row {{ color: {_h_txt_sec}; font-size: 11px; }}
#tooltip .tt-row span {{ color: {_h_txt_pri}; }}

#info-panel {{
  position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%);
  background: {_h_bg}; border: 1px solid {_h_bdr}; border-radius: 12px;
  padding: 10px 20px; font-size: 11px; color: {_h_txt_sec};
  backdrop-filter: blur(12px); pointer-events: none; letter-spacing: 0.4px;
}}
#info-panel kbd {{
  background: {_h_bdr}; border: 1px solid {_h_accent}; border-radius: 4px;
  padding: 1px 5px; color: {_h_accent}; font-family: inherit; font-size: 11px;
}}
#stats {{
  position: fixed; top: 12px; right: 14px; background: {_h_bg};
  border: 1px solid {_h_bdr}; border-radius: 8px; padding: 5px 10px;
  font-size: 11px; color: {_h_accent2}; pointer-events: none;
}}
</style>
</head>
<body>

<div id="canvas"></div>
<div id="tooltip"></div>
<div id="info-panel">
  <kbd>{_t('ge_d3_zoom')}</kbd> {_t('ge_d3_zoom_hint')} &nbsp;·&nbsp; <kbd>{_t('ge_d3_drag')}</kbd> {_t('ge_d3_drag_hint')} &nbsp;·&nbsp; <kbd>{_t('ge_d3_hover')}</kbd> {_t('ge_d3_hover_hint')}
</div>
<div id="stats"></div>

<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script src="resources/js/vis-network.min.js"></script>
<script>
const DATA = {graph_json};

let BRIDGE = null;
if (window.qt && window.qt.webChannelTransport) {{
  new QWebChannel(qt.webChannelTransport, function(channel) {{
    BRIDGE = channel.objects.bridge || null;
  }});
}}

// Degree calculation
const degMap = {{}};
DATA.nodes.forEach(n => degMap[n.id] = 0);
DATA.edges.forEach(e => {{
  degMap[e.source] = (degMap[e.source] || 0) + 1;
  degMap[e.target] = (degMap[e.target] || 0) + 1;
}});

const shapeMap = {{
  'rect': 'box',
  'round': 'box',
  'circle': 'circle',
  'diamond': 'diamond',
  'hexagon': 'hexagon',
  'flag': 'triangle',
  'trapez': 'box'
}};

function hexToRgba(hex, alpha) {{
  if (!hex) return 'rgba(255,255,255,' + alpha + ')';
  if (hex.startsWith("rgba")) {{
    return hex.replace(/[\\d\\.]+\\)$/, alpha + ")");
  }}
  let c = hex.substring(1);
  if (c.length === 3) c = c[0]+c[0]+c[1]+c[1]+c[2]+c[2];
  const r = parseInt(c.substring(0, 2), 16);
  const g = parseInt(c.substring(2, 4), 16);
  const b = parseInt(c.substring(4, 6), 16);
  return 'rgba(' + r + ', ' + g + ', ' + b + ', ' + alpha + ')';
}}

const visNodes = DATA.nodes.map(n => {{
  const degree = degMap[n.id] || 0;
  const radius = 18 + Math.min(degree, 8) * 2.5;
  const visShape = shapeMap[n.shape] || 'dot';
  return {{
    id: n.id,
    label: n.icon + " " + n.label,
    title: n.label,
    shape: visShape,
    size: radius,
    color: {{
      background: n.fill,
      border: '{_h_bdr}',
      highlight: {{ background: '{_h_accent}', border: '{_h_accent}' }},
      hover: {{ background: '{_h_accent2}', border: '{_h_accent2}' }}
    }},
    font: {{
      color: '{_h_txt_pri}',
      strokeWidth: 3,
      strokeColor: '{_h_bg}'
    }}
  }};
}});

const visEdges = DATA.edges.map(e => {{
  const hasArrow = e.arrow !== false && !e.id.includes("---") && !e.id.includes("-...-");
  return {{
    id: e.id,
    from: e.source,
    to: e.target,
    label: e.label || "",
    color: {{
      color: e.stroke || '{_h_accent}',
      highlight: '{_h_accent}',
      hover: '{_h_accent2}'
    }},
    width: (e.dash === "none" && e.id.includes("==>")) ? 4 : 2,
    dashes: e.dash !== "none" ? [6, 3] : false,
    arrows: {{
      to: {{ enabled: hasArrow, scaleFactor: 0.8 }}
    }}
  }};
}});

const container = document.getElementById('canvas');
const nodesDataset = new vis.DataSet(visNodes);
const edgesDataset = new vis.DataSet(visEdges);

const options = {{
  nodes: {{
    borderWidth: 1.5,
    borderWidthSelected: 2.5,
    font: {{ size: 11, face: 'Segoe UI, system-ui, sans-serif' }}
  }},
  edges: {{
    font: {{
      color: '{_h_accent2}', size: 10, face: 'Segoe UI, system-ui, sans-serif',
      strokeWidth: 2, strokeColor: '{_h_bg}', align: 'middle'
    }},
    smooth: {{ type: 'continuous', roundness: 0.3 }}
  }},
  interaction: {{ hover: true, selectConnectedEdges: false, tooltipDelay: 200 }},
  physics: {{
    enabled: true,
    solver: 'barnesHut',
    barnesHut: {{
      gravitationalConstant: -2000, centralGravity: 0.1,
      springLength: 120, springConstant: 0.04, damping: 0.09, avoidOverlap: 0.8
    }},
    stabilization: {{ enabled: true, iterations: 150, updateInterval: 25 }}
  }}
}};

const network = new vis.Network(container, {{ nodes: nodesDataset, edges: edgesDataset }}, options);

// Selection bridge calls
network.on("click", function(params) {{
  if (params.nodes.length > 0) {{
    if (BRIDGE) BRIDGE.onNodeSelected(String(params.nodes[0]));
  }} else if (params.edges.length > 0) {{
    if (BRIDGE) BRIDGE.onEdgeSelected(String(params.edges[0]));
  }}
}});

// Context Menu Setup
container.addEventListener("contextmenu", function(e) {{
  e.preventDefault();
  const rect = container.getBoundingClientRect();
  const domPointer = {{
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  }};
  
  const nodeId = network.getNodeAt(domPointer);
  const edgeId = network.getEdgeAt(domPointer);
  
  let itemType = 'background';
  let itemId = '';
  
  if (nodeId !== undefined) {{
    itemType = 'node';
    itemId = String(nodeId);
  }} else if (edgeId !== undefined) {{
    itemType = 'edge';
    itemId = String(edgeId);
  }}
  
  if (BRIDGE) {{
    BRIDGE.onContextMenu(itemType, itemId, Math.round(e.clientX), Math.round(e.clientY));
  }}
}});

// Custom Tooltip & Neighbor Highlight
let hoveredNode = null;
const tooltip = document.getElementById('tooltip');

network.on("hoverNode", function(params) {{
  const nodeId = params.node;
  hoveredNode = DATA.nodes.find(n => n.id === nodeId);
  if (!hoveredNode) return;
  
  const connectedNodes = network.getConnectedNodes(nodeId);
  const updateArray = DATA.nodes.map(n => {{
    const isNeighbor = n.id === nodeId || connectedNodes.includes(n.id);
    return {{
      id: n.id,
      color: {{
        background: isNeighbor ? n.fill : hexToRgba(n.fill, 0.15),
        border: isNeighbor ? '{_h_bdr}' : hexToRgba('{_h_bdr}', 0.15)
      }},
      font: {{ color: isNeighbor ? '{_h_txt_pri}' : hexToRgba('{_h_txt_pri}', 0.15) }}
    }};
  }});
  nodesDataset.update(updateArray);

  const edgeUpdateArray = DATA.edges.map(e => {{
    const isConnected = e.source === nodeId || e.target === nodeId;
    return {{
      id: e.id,
      color: {{ color: isConnected ? (e.stroke || '{_h_accent}') : hexToRgba(e.stroke || '{_h_accent}', 0.1) }}
    }};
  }});
  edgesDataset.update(edgeUpdateArray);

  let html = `<strong>${{hoveredNode.label}}</strong><br><span class="tt-type">${{hoveredNode.type}}</span>`;
  if (hoveredNode.desc) html += `<hr class="tt-sep"><div class="tt-row">${{hoveredNode.desc}}</div>`;
  const metaEntries = Object.entries(hoveredNode.meta || {{}});
  if (metaEntries.length) {{
    html += `<hr class="tt-sep">`;
    metaEntries.forEach(([k,v]) => {{
      html += `<div class="tt-row">${{k}}: <span>${{v}}</span></div>`;
    }});
  }
  html += `<hr class="tt-sep"><div class="tt-row">{_t('ge_d3_connections')}: <span>${{degMap[hoveredNode.id] || 0}}</span></div>`;
  tooltip.innerHTML = html;
  tooltip.classList.add('visible');
}});

network.on("blurNode", function(params) {{
  hoveredNode = null;
  tooltip.classList.remove('visible');
  
  const restoreNodes = DATA.nodes.map(n => ({{
    id: n.id,
    color: {{ background: n.fill, border: '{_h_bdr}' }},
    font: {{ color: '{_h_txt_pri}' }}
  }}));
  nodesDataset.update(restoreNodes);

  const restoreEdges = DATA.edges.map(e => ({{
    id: e.id,
    color: {{ color: e.stroke || '{_h_accent}' }}
  }}));
  edgesDataset.update(restoreEdges);
}});

container.addEventListener("mousemove", function(event) {{
  if (!hoveredNode) return;
  const x = event.clientX, y = event.clientY;
  const tw = tooltip.offsetWidth, th = tooltip.offsetHeight;
  const px = x + 14 + tw > window.innerWidth ? x - tw - 14 : x + 14;
  const py = y + 10 + th > window.innerHeight ? y - th - 10 : y + 10;
  tooltip.style.left = px + 'px';
  tooltip.style.top  = py + 'px';
}});

document.getElementById('stats').innerText = 
  `${{DATA.nodes.length}} {_t('ge_d3_nodes_count')} · ${{DATA.edges.length}} {_t('ge_d3_edges_count')}`;
</script>
</body>
</html>
"""
```

### C. Changes to `src/laitoxx/interfaces/gui/graph_editor.py`

1. **Update `_GraphWebBridge`**:
   Expose node selection, edge selection, and context menus to JS.
   ```python
       class _GraphWebBridge(QObject):
           node_selected = pyqtSignal(str)
           edge_selected = pyqtSignal(str)
           context_menu_requested = pyqtSignal(str, str, int, int)  # item_type, item_id, x, y

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

2. **Update `MermaidView`**:
   Expose the same signals, connect bridge signals, and load from a local file directory base URL.
   ```python
   class MermaidView(QWidget):
       node_selected = pyqtSignal(str)
       edge_selected = pyqtSignal(str)
       context_menu_requested = pyqtSignal(str, str, int, int)

       # __init__:
       # Set up bridge and channel connections:
       # self._bridge.node_selected.connect(self.node_selected.emit)
       # self._bridge.edge_selected.connect(self.edge_selected.emit)
       # self._bridge.context_menu_requested.connect(self.context_menu_requested.emit)

       def render_graph(self, graph: Graph) -> None:
           if self._web:
               # Set project root as base URL to allow loading resources/js/vis-network.min.js
               project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
               base_url = QUrl.fromLocalFile(project_root + "/")
               self._web.setHtml(
                   generate_html(graph, lang=translator.lang, theme=self._theme),
                   base_url,
               )
           elif self._text:
               self._text.setPlainText(generate_mermaid(graph))
   ```

3. **Update `GraphEditor`**:
   - In `_build_center_panel`, connect the signals:
     ```python
     self._mermaid_view = MermaidView()
     self._mermaid_view.node_selected.connect(self._on_graph_node_selected)
     self._mermaid_view.edge_selected.connect(self._on_graph_edge_selected)
     self._mermaid_view.context_menu_requested.connect(self._on_graph_context_menu)
     ```
   - Add selection helpers:
     ```python
     def select_node_by_id(self, node_id: str):
         for i in range(self._nodes_list.count()):
             item = self._nodes_list.item(i)
             if item.data(Qt.ItemDataRole.UserRole) == node_id:
                 self._nodes_list.setCurrentItem(item)
                 break

     def select_edge_by_id(self, edge_id: str):
         for i in range(self._edges_list.count()):
             item = self._edges_list.item(i)
             if item.data(Qt.ItemDataRole.UserRole) == edge_id:
                 self._edges_list.setCurrentItem(item)
                 break
     ```
   - Refactor edge context menu creation:
     ```python
     def _show_edge_context_menu(self, edge_id: str, global_pos: QPoint):
         from PyQt6.QtWidgets import QMenu
         edge = self._graph.get_edge(edge_id)
         if not edge:
             return
         menu = QMenu(self)
         edit_act = menu.addAction(_t("ge_ctx_edit"))
         menu.addSeparator()
         del_act  = menu.addAction(_t("ge_ctx_delete"))
         action = menu.exec(global_pos)
         if action == edit_act:
             self._edit_edge_by_id(edge_id)
         elif action == del_act:
             self._graph.remove_edge(edge_id)
             self._refresh_all()

     def _edge_list_context(self, pos):
         item = self._edges_list.itemAt(pos)
         if not item:
             return
         edge_id = item.data(Qt.ItemDataRole.UserRole)
         self._show_edge_context_menu(edge_id, self._edges_list.mapToGlobal(pos))
     ```
   - Implement the new slot callbacks:
     ```python
     def _on_graph_node_selected(self, node_id: str):
         self.select_node_by_id(node_id)

     def _on_graph_edge_selected(self, edge_id: str):
         self.select_edge_by_id(edge_id)

     def _on_graph_context_menu(self, item_type: str, item_id: str, x: int, y: int):
         global_pos = self._mermaid_view.map_web_to_global(x, y)
         if item_type == "node":
             node = self._graph.get_node(item_id)
             if node:
                 self._show_node_context_menu(node, global_pos)
         elif item_type == "edge":
             self._show_edge_context_menu(item_id, global_pos)
         elif item_type == "background":
             self._show_graph_context_menu(global_pos)
     ```

---

## 5. Verification Method

To verify the correct execution of these changes:
1. **Download Verification**: Run the download script:
   ```bash
   python scripts/download_vis_network.py
   ```
   Verify that `resources/js/vis-network.min.js` is created. If offline/sandboxed, verify that it is populated with the robust mock placeholder script.
2. **Launch Verification**: Run the main application GUI:
   ```bash
   python gui.py
   ```
   Open the Graph Editor tool. Verify the graph renders correctly (either with the vis-network graph if downloaded, or showing the placeholder card if offline/not fetched).
3. **Selection Verification**:
   - Click a node/edge in the graph. Check that the corresponding item is selected in the left list widget, and the properties panel on the right updates correctly.
4. **Context Menu Verification**:
   - Right-click a node: Verify the node context menu displays.
   - Right-click an edge: Verify the edge context menu displays.
   - Right-click the background: Verify the graph editor options context menu (Add Node/Add Edge/Export) displays.
5. **Backend Verification**: Run the existing test suite:
   ```bash
   pytest tests/test_graph_api.py
   ```
   Ensure no regressions in the underlying backend graph data model or algorithms.
