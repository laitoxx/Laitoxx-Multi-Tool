# Handoff Report — Milestone 3 (Drag-and-Drop Metadata Extraction)

This report details the design and implementation strategy for Drag-and-Drop Metadata Extraction in the Graph Editor.

---

## 1. Observation

During our codebase investigation, we observed the following structures and code patterns:

### A. Graph Editor UI (`src/laitoxx/interfaces/gui/graph_editor.py`)
`GraphEditorWindow` is a `QDialog` that manages the Python `Graph` instance, UI lists, status bar, and rendering via `MermaidView`.
Lines 1232-1249:
```python
class GraphEditorWindow(QDialog):
    # Signal emitted when user wants to run an action from graph editor
    # (action_type: str, action_data: object, value: str)
    run_action_requested = pyqtSignal(str, object, str)

    def __init__(self, parent=None, theme_data: Optional[dict] = None,
                 lua_plugins: list | None = None):
        super().__init__(parent)
        self.setWindowTitle(_t("graph_editor_title"))
        self.setMinimumSize(1140, 720)
        self._graph = Graph(name=_t("ge_new_graph_name"))
        self._current_filepath: Optional[str] = None
        self._theme = theme_data or {}
        self._panel_alpha = 0.55
        self._lua_plugins = lua_plugins or []

        self._build_ui()
```

Inside `MermaidView` (lines 992-1011):
```python
    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme: dict = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if HAS_WEB:
            self._web = QWebEngineView()
```

### B. HTML / Canvas Graph Renderer (`src/laitoxx/shared/graph/mermaid.py`)
`generate_html(graph, lang, theme)` builds a self-contained HTML page using `vis-network`.
Lines 480-487:
```javascript
// Programmatic selection helpers
window.selectNode = function(nodeId) {
  network.selectNodes([nodeId]);
};
window.selectEdge = function(edgeId) {
  network.selectEdges([edgeId]);
};
```

### C. Metadata Engine (`src/laitoxx/features/utilities/metadata_viewer/engine.py`)
`MetadataEngine` class handles file parsing and returns a metadata dictionary.
Lines 86-90:
```python
class MetadataEngine:
    def __init__(self):
        pass
```
Line 320:
```python
engine_instance = MetadataEngine()
```

### D. Export to Graph Logic (`src/laitoxx/features/utilities/metadata_viewer/gui_window.py`)
`_export_to_graph` demonstrates key names and relationships for exporting to the graph model.
Lines 335-364:
```python
            # Extract Authors
            for key in ["Author", "Creator", "Producer", "OwnerName"]:
                val = data.get(key)
                if val:
                    val_str = str(val)
                    if val_str not in author_nodes:
                        author_node = Node(id=str(uuid.uuid4()), label=val_str, node_type="Person")
                        graph_win._graph.add_node(author_node)
                        author_nodes[val_str] = author_node
                    edge = Edge(id=str(uuid.uuid4()), source_id=author_nodes[val_str].id, target_id=file_node.id, label="created/edited", edge_type="Connected")
                    graph_win._graph.add_edge(edge)
                    added_edges += 1
                    
            # Extract Software
            for key in ["EXIF:Software", "Software", "Tika:creator", "Hachoir:Software"]:
                val = data.get(key)
                if val:
                    val_str = str(val)
                    if val_str not in software_nodes:
                        software_node = Node(
                            id=str(uuid.uuid4()),
                            label=val_str,
                            node_type="Custom",
                            mermaid_shape="hexagon"
                        )
                        graph_win._graph.add_node(software_node)
                        software_nodes[val_str] = software_node
                    edge = Edge(id=str(uuid.uuid4()), source_id=file_node.id, target_id=software_nodes[val_str].id, label="created with", edge_type="Connected")
                    graph_win._graph.add_edge(edge)
                    added_edges += 1
```

### E. Existing Web Bridge Headless Testing (`tests/test_web_bridge.py`)
`test_web_bridge_two_way_communication` tests QWebEngineView and QWebChannel headlessly by forcing offscreen rendering.
Lines 7-17:
```python
# Force offscreen QPA platform for headless testing before importing PyQt6 GUI elements
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from laitoxx.shared.graph.model import Graph, Node, Edge
from laitoxx.interfaces.gui.graph_editor import MermaidView

@pytest.fixture(scope="session", autouse=True)
def qapp():
    # Retrieve or create offscreen QApplication instance
    app = QApplication.instance() or QApplication(["-platform", "offscreen"])
    yield app
```

---

## 2. Logic Chain

Based on these observations, we conclude:
1. **Drag and Drop Interception**: Enabling accept drops on `GraphEditorWindow` and disabling it on the child web view `self._mermaid_view._web` ensures dropped URLs bubble up to `GraphEditorWindow`.
2. **Unsupported Type QMessageBox**: A list of 18 extensions (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.mp3`, `.wav`, `.mp4`, `.avi`, `.doc`, `.xls`, `.ppt`, `.docx`, `.xlsx`, `.pptx`, `.exe`, `.dll`, `.sys`) will filter files during `dropEvent`. If any dropped file has an invalid extension, the import aborts, showing a `QMessageBox.warning` (per Objective 1 & 2).
3. **Metadata Extraction Integration**: The drop handler will import `engine_instance` from `engine.py` and call `extract_metadata(filepath)` to retrieve key-value pairs (per Objective 3).
4. **Graph Node/Edge Relationships**: We will create a `Document` node, along with linked `Person` nodes for authors and `Custom` nodes for software, as observed in `gui_window.py` (per Objective 4).
5. **dynamic Canvas Updates**: Rather than reloading the canvas via `setHtml()` which causes flickering, we will add Javascript methods `addNodeDynamically` and `addEdgeDynamically` to the HTML generated by `mermaid.py`. Python can execute these using `runJavaScript()` with JSON-serialized node/edge details (per Objective 5).
6. **Automated Testing**: We can write a pytest suite utilizing the offscreen QPA platform that constructs drop events and mocks the dialog interactions to verify dynamic insertion.

---

## 3. Caveats

- **Web Engine Load State**: Dynamic JS updates assume that the canvas HTML has finished loading. If a user drags and drops a file immediately before the initial blank page load completes, dynamic insertions may fail. A small check/fallback is recommended to trigger a full refresh if `window.addNodeDynamically` is not yet defined.
- **Duplicate Prevention**: Since drag-and-drop can be invoked multiple times on the same file, checking existing nodes in the graph by `FilePath` (within the node's `metadata`) is vital to avoid spamming the graph canvas.

---

## 4. Conclusion & Proposed Strategy

### File: `src/laitoxx/shared/graph/mermaid.py`
Add the following Javascript functions inside the script tag of `generate_html` (right below `window.selectEdge`):
```javascript
// Dynamic update helpers (Milestone 3)
window.addNodeDynamically = function(nodeJson) {{
  const n = JSON.parse(nodeJson);
  nodesDataset.update({{
    id: n.id,
    label: n.label,
    shape: 'image',
    image: makeSvgDataUrl(n),
    title: makeTooltipHtml(n)
  }});
  if (window.updateStatsBadge) window.updateStatsBadge();
}};

window.addEdgeDynamically = function(edgeJson) {{
  const e = JSON.parse(edgeJson);
  let dash = false;
  if (e.dash && e.dash !== 'none') {{
    dash = true;
  }}
  let edgeOpt = {{
    id: e.id,
    from: e.source,
    to: e.target,
    label: e.label || undefined,
    color: {{ color: e.stroke || "{_h_accent}", hover: "{_h_accent}", highlight: "{_h_accent}" }},
    dashes: dash,
    arrows: e.arrow ? {{ to: {{ enabled: true, scaleFactor: 0.8 }} }} : undefined
  }};
  edgesDataset.update(edgeOpt);
  if (window.updateStatsBadge) window.updateStatsBadge();
}};

window.updateStatsBadge = function() {{
  const statsElem = document.getElementById('stats');
  if (statsElem) {{
    statsElem.innerText = 
      `${{nodesDataset.length}} {_t('ge_d3_nodes_count')} · ${{edgesDataset.length}} {_t('ge_d3_edges_count')}`;
  }}
}};
```

### File: `src/laitoxx/interfaces/gui/graph_editor.py`

#### A. Enable Drag-and-Drop in `GraphEditorWindow.__init__`
```python
        self._build_ui()
        self.setAcceptDrops(True)
        if HAS_WEB:
            self._mermaid_view._web.setAcceptDrops(False)
```

#### B. Handle Events and File Extraction
Add these methods to the `GraphEditorWindow` class:
```python
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return

        supported = {
            ".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".mp3", ".wav", ".mp4", ".avi",
            ".doc", ".xls", ".ppt", ".docx", ".xlsx", ".pptx", ".exe", ".dll", ".sys"
        }

        # Validate file extensions first
        filepaths = []
        for url in urls:
            path = url.toLocalFile()
            if path and os.path.isfile(path):
                ext = os.path.splitext(path)[1].lower()
                if ext not in supported:
                    QMessageBox.warning(
                        self,
                        _t("ge_unsupported_file_title") or "Unsupported File",
                        _t("ge_unsupported_file_msg", ext=ext) or f"File type {ext} is not supported."
                    )
                    event.ignore()
                    return
                filepaths.append(path)
            elif path and os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        fpath = os.path.join(root, file)
                        ext = os.path.splitext(fpath)[1].lower()
                        if ext not in supported:
                            QMessageBox.warning(
                                self,
                                _t("ge_unsupported_file_title") or "Unsupported File",
                                f"File type {ext} in directory is not supported."
                            )
                            event.ignore()
                            return
                        filepaths.append(fpath)

        if not filepaths:
            event.ignore()
            return

        # If all valid, import metadata
        for path in filepaths:
            self._import_file_metadata(path)
        event.acceptProposedAction()

    def _import_file_metadata(self, filepath: str):
        from laitoxx.features.utilities.metadata_viewer.engine import engine_instance
        from laitoxx.shared.graph.model import Node, Edge
        import uuid

        try:
            data = engine_instance.extract_metadata(filepath)
        except Exception as e:
            QMessageBox.warning(self, _t("error"), f"Failed to extract metadata: {e}")
            return

        if "error" in data:
            QMessageBox.warning(self, _t("error"), f"Error extracting metadata: {data['error']}")
            return

        # Check duplicate Document node
        existing_node = None
        for node in self._graph.nodes:
            if node.node_type == "Document" and node.metadata.get("FilePath") == filepath:
                existing_node = node
                break

        if existing_node:
            existing_node.metadata = data
            self._refresh_all()
            self._set_status(f"Updated metadata for {os.path.basename(filepath)}")
            return

        # Create Document node
        filename = data.get("FileName", os.path.basename(filepath))
        file_node = Node(
            id=str(uuid.uuid4()),
            label=filename,
            node_type="Document",
            description=f"File path: {filepath}\nMD5: {data.get('MD5', '')}",
            metadata=data
        )
        self._graph.add_node(file_node)
        self._push_node_dynamically(file_node)

        # Extract Authors (Person)
        for key in ["Author", "Creator", "Producer", "OwnerName"]:
            val = data.get(key)
            if val:
                val_str = str(val).strip()
                if not val_str:
                    continue
                # Deduplicate Person
                person_node = None
                for node in self._graph.nodes:
                    if node.node_type == "Person" and node.label == val_str:
                        person_node = node
                        break
                if not person_node:
                    person_node = Node(
                        id=str(uuid.uuid4()),
                        label=val_str,
                        node_type="Person",
                        description=f"Author of {filename}"
                    )
                    self._graph.add_node(person_node)
                    self._push_node_dynamically(person_node)

                # Link Author -> Document
                edge_exists = False
                for edge in self._graph.edges:
                    if edge.source_id == person_node.id and edge.target_id == file_node.id:
                        edge_exists = True
                        break
                if not edge_exists:
                    edge = Edge(
                        id=str(uuid.uuid4()),
                        source_id=person_node.id,
                        target_id=file_node.id,
                        label="created/edited",
                        edge_type="Connected"
                    )
                    self._graph.add_edge(edge)
                    self._push_edge_dynamically(edge)

        # Extract Software (Custom)
        for key in ["EXIF:Software", "Software", "Tika:creator", "Hachoir:Software"]:
            val = data.get(key)
            if val:
                val_str = str(val).strip()
                if not val_str:
                    continue
                # Deduplicate Software
                soft_node = None
                for node in self._graph.nodes:
                    if node.node_type == "Custom" and node.label == val_str:
                        soft_node = node
                        break
                if not soft_node:
                    soft_node = Node(
                        id=str(uuid.uuid4()),
                        label=val_str,
                        node_type="Custom",
                        mermaid_shape="hexagon",
                        description=f"Software used by {filename}"
                    )
                    self._graph.add_node(soft_node)
                    self._push_node_dynamically(soft_node)

                # Link Document -> Software
                edge_exists = False
                for edge in self._graph.edges:
                    if edge.source_id == file_node.id and edge.target_id == soft_node.id:
                        edge_exists = True
                        break
                if not edge_exists:
                    edge = Edge(
                        id=str(uuid.uuid4()),
                        source_id=file_node.id,
                        target_id=soft_node.id,
                        label="created with",
                        edge_type="Connected"
                    )
                    self._graph.add_edge(edge)
                    self._push_edge_dynamically(edge)

        self._refresh_nodes_list()
        self._refresh_edges_list()
        self._raw_code.setPlainText(generate_mermaid(self._graph))
        self._set_status(f"Imported metadata from {filename}")

    def _push_node_dynamically(self, node: Node):
        if self._mermaid_view._web:
            import json
            from laitoxx.shared.graph.mermaid import SHAPE_ID_TO_D3, _TYPE_COLORS, _TYPE_SYMBOLS, _parse_style_color
            
            fill = _parse_style_color(node.mermaid_style, "fill",
                                      _TYPE_COLORS.get(node.node_type, "#94a3b8"))
            node_data = {
                "id":    node.id,
                "label": node.label,
                "type":  node.node_type,
                "desc":  node.description,
                "fill":  fill,
                "icon":  _TYPE_SYMBOLS.get(node.node_type, "●"),
                "meta":  node.metadata,
                "shape": SHAPE_ID_TO_D3.get(node.mermaid_shape, "circle"),
            }
            node_json = json.dumps(node_data)
            self._mermaid_view._web.page().runJavaScript(
                f"if (window.addNodeDynamically) {{ window.addNodeDynamically({json.dumps(node_json)}); }}"
            )

    def _push_edge_dynamically(self, edge: Edge):
        if self._mermaid_view._web:
            import json
            from laitoxx.shared.graph.mermaid import _EDGE_DASH, _parse_style_color
            
            accent_color = self._theme.get("accent_color", "#c084fc")
            stroke = _parse_style_color(edge.mermaid_style, "stroke", accent_color)
            dash = _EDGE_DASH.get(edge.mermaid_line, "none")
            
            edge_data = {
                "id":     edge.id,
                "source": edge.source_id,
                "target": edge.target_id,
                "label":  edge.label,
                "type":   edge.edge_type,
                "stroke": stroke,
                "dash":   dash,
                "arrow":  "-->" not in (edge.mermaid_line or "") or True,
            }
            edge_json = json.dumps(edge_data)
            self._mermaid_view._web.page().runJavaScript(
                f"if (window.addEdgeDynamically) {{ window.addEdgeDynamically({json.dumps(edge_json)}); }}"
            )
```

---

## 5. Verification Method

To verify the implementation of this strategy:

### A. Automated Test Plan (`tests/test_graph_editor_drag_drop.py`)
Add a new test module to simulate dragging and dropping valid/invalid files.
```python
import os
import pytest
from unittest.mock import patch
from PyQt6.QtCore import QMimeData, QPoint, QUrl, Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QApplication, QMessageBox
from laitoxx.interfaces.gui.graph_editor import GraphEditorWindow

@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication(["-platform", "offscreen"])
    yield app

def test_drag_and_drop_valid_file(qapp, tmp_path):
    test_file = tmp_path / "document.pdf"
    test_file.write_text("dummy")

    window = GraphEditorWindow()
    
    # Mock extract_metadata to avoid actual filesystem or dependency issues during tests
    with patch("laitoxx.features.utilities.metadata_viewer.engine.engine_instance.extract_metadata") as mock_extract:
        mock_extract.return_value = {
            "FileName": "document.pdf",
            "FilePath": str(test_file),
            "MD5": "abcd1234",
            "Author": "Test Author",
            "Software": "Test Software"
        }
        
        # Build mime data
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(str(test_file))])
        
        # Simulate drop event
        drop_event = QDropEvent(
            QPoint(100, 100),
            Qt.DropAction.CopyAction,
            mime_data,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        
        QApplication.sendEvent(window, drop_event)
        
        # Verify document node is added
        nodes = window._graph.nodes
        assert len(nodes) == 3  # Document, Person (Author), Custom (Software)
        
        doc_node = next(n for n in nodes if n.node_type == "Document")
        assert doc_node.label == "document.pdf"
        assert doc_node.metadata["MD5"] == "abcd1234"
        
        author_node = next(n for n in nodes if n.node_type == "Person")
        assert author_node.label == "Test Author"

def test_drag_and_drop_invalid_file(qapp, tmp_path):
    test_file = tmp_path / "document.txt"
    test_file.write_text("dummy text")

    window = GraphEditorWindow()
    
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(test_file))])
    
    drop_event = QDropEvent(
        QPoint(100, 100),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    
    # Mock QMessageBox warning so the test is non-blocking
    with patch.object(QMessageBox, "warning") as mock_warn:
        QApplication.sendEvent(window, drop_event)
        
        # Ensure warning is triggered and import aborted
        mock_warn.assert_called_once()
        assert len(window._graph.nodes) == 0
```

### B. Execution Command
Run the tests using pytest:
```bash
pytest tests/test_graph_editor_drag_drop.py
```
This is independent of visual X11 display because `QT_QPA_PLATFORM` is set to `offscreen`.

---
