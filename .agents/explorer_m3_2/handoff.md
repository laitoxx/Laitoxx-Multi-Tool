# Handoff Report: Milestone 3 — Drag-and-Drop Metadata Extraction Design Strategy

## 1. Observation

During the investigation, the following files and code structures were observed:

- **`src/laitoxx/interfaces/gui/graph_editor.py`**:
  - The main editor window is `GraphEditorWindow` (inherits from `QDialog` starting at line 1232).
  - It contains a central panel `self._center_panel` built in `_build_center_panel()` (line 1423), which embeds a `MermaidView` instance `self._mermaid_view` (line 1431).
  - `MermaidView` (line 958) wraps `QWebEngineView` (if `HAS_WEB` is True) to render the vis-network graph canvas via an embedded HTML template.
  - Currently, neither `GraphEditorWindow` nor `MermaidView` implements drag-and-drop event handlers (no `dragEnterEvent`, `dragMoveEvent`, `dropEvent`, or `setAcceptDrops(True)` calls).

- **`src/laitoxx/features/utilities/metadata_viewer/gui_window.py`**:
  - The metadata viewer utilizes `self.setAcceptDrops(True)` and overrides standard event methods:
    ```python
    138:     def dragEnterEvent(self, e: QDragEnterEvent):
    139:         if e.mimeData().hasUrls():
    140:             e.acceptProposedAction()
    141: 
    142:     def dropEvent(self, e: QDropEvent):
    143:         for url in e.mimeData().urls():
    144:             path = url.toLocalFile()
    ...
    ```
  - The logic for exporting metadata to the Graph Editor is implemented in `_export_to_graph` (lines 283–369). It runs:
    ```python
    320:             data = engine_instance.extract_metadata(filepath)
    ```
    and creates a `Document` node:
    ```python
    327:             file_node = Node(
    328:                 id=str(uuid.uuid4()),
    329:                 label=data.get("FileName", os.path.basename(filepath)),
    330:                 node_type="Document"
    331:             )
    ```
    along with extracting Authors (type `"Person"`, linked with edge `"created/edited"`) and Software (type `"Custom"`, shape `"hexagon"`, linked with edge `"created with"`).

- **`src/laitoxx/features/utilities/metadata_viewer/engine.py`**:
  - The `MetadataEngine` class (line 86) exposes `extract_metadata(self, filepath: str) -> dict`. It integrates multiple forensic parsers like `Hachoir`, `pyexiv2`, `TinyTag`, `mutagen`, `olefile`, `pefile`, `binwalk`, and `kreuzberg` to extract key-value metadata.

- **`src/laitoxx/shared/graph/mermaid.py`**:
  - Contains `generate_html(graph: Graph, lang: str = None, theme: dict = None) -> str` (line 101), which generates the interactive HTML for `vis-network`.
  - It declares the global datasets `nodesDataset` and `edgesDataset` (lines 289–290) and performs a full reload when `render_graph` is called via `self._web.setHtml()`.
  - There is currently no mechanism to dynamically update `nodesDataset` or `edgesDataset` without reloading the page.

- **`tests/test_web_bridge.py`**:
  - Demonstrates how to write tests for `MermaidView` by calling page-level JavaScript functions like `window.testTriggerNodeSelected('node1')` using `runJavaScript` and verifying that signals propagate back to Python (lines 60–87).

---

## 2. Logic Chain

1. **Drop Interception**: Drag-and-drop must be supported in `graph_editor.py`. By calling `self.setAcceptDrops(True)` in `GraphEditorWindow.__init__` and implementing `dragEnterEvent` and `dropEvent` on the window level, the GUI will handle drag-and-drop events. Since child widgets like `QWebEngineView` could consume the event, we should explicitly call `self._web.setAcceptDrops(False)` in `MermaidView` to allow the events to bubble up to the parent window.
2. **File Extension Validation**: When files are dropped, we can iterate through the list of dropped URLs, retrieve their file extensions via `os.path.splitext()`, and check them against a set of supported extensions (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.mp3`, `.wav`, `.mp4`, `.avi`, `.doc`, `.xls`, `.ppt`, `.docx`, `.xlsx`, `.pptx`, `.exe`, `.dll`, `.sys`). If any file has an unsupported extension, we display a warning `QMessageBox` and call `event.ignore()` to abort the entire drop.
3. **Metadata Extraction Integration**: For valid files, we import `engine_instance` from `laitoxx.features.utilities.metadata_viewer.engine` and call `engine_instance.extract_metadata(filepath)`.
4. **Graph Node/Edge Creation**: Following the keys and schema defined in `gui_window.py`'s `_export_to_graph` method:
   - Create a `"Document"` node for the file.
   - Look up keys `"Author"`, `"Creator"`, `"Producer"`, and `"OwnerName"` in metadata. If present, create a `"Person"` node and a `"created/edited"` edge.
   - Look up keys `"EXIF:Software"`, `"Software"`, `"Tika:creator"`, and `"Hachoir:Software"` in metadata. If present, create a `"Custom"` node (with shape `"hexagon"`) and a `"created with"` edge.
   - **Resolution & Deduplication**: To avoid cluttered graphs and duplicate nodes, we query the existing nodes in `self._graph.nodes` by label and type, reusing existing nodes (and matching edges) instead of recreating them.
5. **Real-time Canvas Push**: To avoid resetting the user's pan/zoom/dragging state, the page should not be reloaded when updating the graph. Instead:
   - Implement `serialize_graph_to_dict(graph: Graph, theme: dict = None) -> dict` in `mermaid.py` to convert the backend model to the exact JSON schema expected by the frontend.
   - Expose `window.updateGraph(newGraph)` in `mermaid.py`'s generated HTML to dynamically compute the difference, call `.add()`, `.update()`, and `.remove()` on the `vis.DataSet` instances, and refresh the stats badge.
   - Modify `MermaidView.render_graph()` to check an `_is_loaded` flag. If `True`, invoke `window.updateGraph` using `self._web.page().runJavaScript()`.
6. **Automated Testing**: Simulate drop events by constructing PyQt `QDragEnterEvent` and `QDropEvent` instances containing dummy files and calling the target event handlers directly, verifying the added nodes/edges on the graph model and mocking `QMessageBox` to test warning behavior.

---

## 3. Caveats

- **Network Constraints**: The implementation is fully offline and uses local libraries. No external network requests are made.
- **ExifTool and System Dependencies**: Some extractors in `MetadataEngine` (like `pyexiv2` or `pefile`) depend on binary libraries or external helpers. The design handles extraction exceptions gracefully by wrapping them in `try-except` blocks and showing informative warnings.
- **Large Files**: Synchronous metadata extraction of very large media files or documents on the main UI thread could cause minor stutters. Since `graph_editor.py` is a GUI module, if stuttering occurs in production, extraction can easily be moved to a worker thread (similar to `WorkerThread` in `gui_window.py`).

---

## 4. Conclusion & Proposed Code Changes

The design strategy is fully structured and ready for implementation. Below are the precise code modifications required.

### A. Modifications to `src/laitoxx/shared/graph/mermaid.py`

#### 1. Add Graph Serialization Function
Place this new function at the module level (e.g., above `generate_html` around line 100):

```python
def serialize_graph_to_dict(graph: Graph, theme: dict = None) -> dict:
    import json as _json
    _td = theme or {}
    _h_accent = _td.get("accent_color", "#c084fc")
    
    nodes_data = []
    for n in graph.nodes:
        fill = _parse_style_color(n.mermaid_style, "fill",
                                  _TYPE_COLORS.get(n.node_type, "#94a3b8"))
        nodes_data.append({
            "id":    n.id,
            "label": n.label,
            "type":  n.node_type,
            "desc":  n.description,
            "fill":  fill,
            "icon":  _TYPE_SYMBOLS.get(n.node_type, "●"),
            "meta":  n.metadata,
            "shape": SHAPE_ID_TO_D3.get(n.mermaid_shape, "circle"),
        })

    edges_data = []
    for e in graph.edges:
        stroke = _parse_style_color(e.mermaid_style, "stroke", _h_accent)
        dash   = _EDGE_DASH.get(e.mermaid_line, "none")
        edges_data.append({
            "id":     e.id,
            "source": e.source_id,
            "target": e.target_id,
            "label":  e.label,
            "type":   e.edge_type,
            "stroke": stroke,
            "dash":   dash,
            "arrow":  "-->" not in (e.mermaid_line or "") or True,
        })

    return {
        "nodes": nodes_data,
        "edges": edges_data,
        "direction": graph.direction
    }
```

#### 2. Update `generate_html` to reuse `serialize_graph_to_dict`
Replace lines 137–172 in `generate_html` with:
```python
    graph_dict = serialize_graph_to_dict(graph, theme)
    graph_json = _json.dumps(graph_dict, ensure_ascii=False)
```

#### 3. Inject JS update helper in `generate_html` template
Within the `<script>` tag inside `generate_html` (e.g. before `// Listen to selections` on line 448), add the following code:

```javascript
window.updateGraph = function(newGraph) {{
  // 1. Update stats badge
  const statsEl = document.getElementById('stats');
  if (statsEl) {{
    statsEl.innerText = 
      `${{newGraph.nodes.length}} {_t('ge_d3_nodes_count')} · ${{newGraph.edges.length}} {_t('ge_d3_edges_count')}`;
  }}

  // 2. Compute Node additions, updates, and removals
  const newNodesMap = new Map();
  newGraph.nodes.forEach(n => newNodesMap.set(n.id, n));
  
  const currentNodeIds = nodesDataset.getIds();
  currentNodeIds.forEach(id => {{
    if (!newNodesMap.has(id)) {{
      nodesDataset.remove(id);
    }}
  }});

  newGraph.nodes.forEach(n => {{
    const nodeObj = {{
      id: n.id,
      label: n.label,
      shape: 'image',
      image: makeSvgDataUrl(n),
      title: makeTooltipHtml(n)
    }};
    if (nodesDataset.get(n.id)) {{
      nodesDataset.update(nodeObj);
    }} else {{
      nodesDataset.add(nodeObj);
    }}
  }});

  // 3. Compute Edge additions, updates, and removals
  const newEdgesMap = new Map();
  newGraph.edges.forEach(e => newEdgesMap.set(e.id, e));

  const currentEdgeIds = edgesDataset.getIds();
  currentEdgeIds.forEach(id => {{
    if (!newEdgesMap.has(id)) {{
      edgesDataset.remove(id);
    }}
  }});

  newGraph.edges.forEach(e => {{
    let dash = false;
    if (e.dash && e.dash !== 'none') {{
      dash = true;
    }}
    const edgeObj = {{
      id: e.id,
      from: e.source,
      to: e.target,
      label: e.label || undefined,
      color: {{ color: e.stroke || "{_h_accent}", hover: "{_h_accent}", highlight: "{_h_accent}" }},
      dashes: dash,
      arrows: e.arrow ? {{ to: {{ enabled: true, scaleFactor: 0.8 }} }} : undefined
    }};
    if (edgesDataset.get(e.id)) {{
      edgesDataset.update(edgeObj);
    }} else {{
      edgesDataset.add(edgeObj);
    }}
  }});
}};
```

---

### B. Modifications to `src/laitoxx/interfaces/gui/graph_editor.py`

#### 1. Add necessary imports
Add imports for drag events on line 18:
```python
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QLinearGradient, QPalette, QDragEnterEvent, QDropEvent
```

#### 2. Update `MermaidView` to track page loads and handle dynamic pushing
Modify `MermaidView.__init__` to disable default drops on the QWebEngineView and track load state:
```python
        if HAS_WEB:
            self._web = QWebEngineView()
            self._web.setStyleSheet("border-radius: 10px;")
            self._web.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
            self._web.setAcceptDrops(False)  # Let events bubble up to the parent window
            self._is_loaded = False
            self._web.loadFinished.connect(self._on_load_finished)
            ...
```
Add `_on_load_finished` slot:
```python
    def _on_load_finished(self, ok):
        if ok:
            self._is_loaded = True
```
Update `render_graph` method:
```python
    def render_graph(self, graph: Graph) -> None:
        if self._web:
            if self._is_loaded:
                from laitoxx.shared.graph.mermaid import serialize_graph_to_dict
                import json
                graph_dict = serialize_graph_to_dict(graph, self._theme)
                graph_json = json.dumps(graph_dict, ensure_ascii=False)
                escaped_json = json.dumps(graph_json)
                self._web.page().runJavaScript(
                    f"if (window.updateGraph) {{ window.updateGraph(JSON.parse({escaped_json})); }}"
                )
            else:
                self._web.setHtml(
                    generate_html(graph, lang=translator.lang, theme=self._theme),
                    QUrl("about:blank"),
                )
        elif self._text:
            self._text.setPlainText(generate_mermaid(graph))
```

#### 3. Update `GraphEditorWindow` to accept drops and process metadata imports
In `GraphEditorWindow.__init__` (line 1237), add:
```python
        self.setAcceptDrops(True)
```
Add the following event handlers and parsing logic to `GraphEditorWindow`:

```python
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        supported_exts = {
            ".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".mp3", ".wav", 
            ".mp4", ".avi", ".doc", ".xls", ".ppt", ".docx", ".xlsx", 
            ".pptx", ".exe", ".dll", ".sys"
        }
        
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return
            
        unsupported_files = []
        valid_files = []
        
        for url in urls:
            filepath = url.toLocalFile()
            if os.path.isfile(filepath):
                _, ext = os.path.splitext(filepath)
                if ext.lower() not in supported_exts:
                    unsupported_files.append((filepath, ext))
                else:
                    valid_files.append(filepath)
        
        if unsupported_files:
            # QMessageBox warning and abort the drop
            ext_list = ", ".join(sorted(supported_exts))
            QMessageBox.warning(
                self,
                _t("ge_unsupported_file_title", default="Unsupported File Type"),
                _t("ge_unsupported_file_msg", default=f"One or more dropped files have an unsupported type.\n\nSupported extensions:\n{ext_list}"),
            )
            event.ignore()
            return
            
        if not valid_files:
            event.ignore()
            return
            
        event.acceptProposedAction()
        for filepath in valid_files:
            self._import_metadata_file(filepath)

    def _import_metadata_file(self, filepath: str):
        from laitoxx.features.utilities.metadata_viewer.engine import engine_instance
        from laitoxx.shared.graph.model import Node, Edge
        import uuid
        
        try:
            data = engine_instance.extract_metadata(filepath)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to extract metadata from {os.path.basename(filepath)}: {e}")
            return

        if "error" in data:
            QMessageBox.warning(self, "Error", f"Failed to extract metadata from {os.path.basename(filepath)}: {data['error']}")
            return

        # Create File (Document) Node
        filename = data.get("FileName", os.path.basename(filepath))
        doc_node = next((n for n in self._graph.nodes if n.node_type == "Document" and n.label == filename), None)
        if not doc_node:
            doc_node = Node(
                id=str(uuid.uuid4()),
                label=filename,
                node_type="Document",
                description=f"Path: {filepath}\nSize: {data.get('FileSize', 0)} bytes",
                metadata={k: str(v) for k, v in data.items() if k != "ExtractedWith"}
            )
            self._graph.add_node(doc_node)

        # Extract Authors (Person nodes)
        for key in ["Author", "Creator", "Producer", "OwnerName"]:
            val = data.get(key)
            if val:
                val_str = str(val).strip()
                if not val_str:
                    continue
                # Entity resolution: reuse existing Person node
                author_node = next((n for n in self._graph.nodes if n.node_type == "Person" and n.label == val_str), None)
                if not author_node:
                    author_node = Node(
                        id=str(uuid.uuid4()),
                        label=val_str,
                        node_type="Person",
                        description=f"Author extracted from metadata"
                    )
                    self._graph.add_node(author_node)
                
                # Deduplicate edges
                edge_exists = any(
                    e.source_id == author_node.id and e.target_id == doc_node.id and e.label == "created/edited"
                    for e in self._graph.edges
                )
                if not edge_exists:
                    edge = Edge(
                        id=str(uuid.uuid4()),
                        source_id=author_node.id,
                        target_id=doc_node.id,
                        label="created/edited",
                        edge_type="Connected"
                    )
                    self._graph.add_edge(edge)

        # Extract Software (Custom nodes)
        for key in ["EXIF:Software", "Software", "Tika:creator", "Hachoir:Software"]:
            val = data.get(key)
            if val:
                val_str = str(val).strip()
                if not val_str:
                    continue
                # Entity resolution: reuse existing Software node
                software_node = next((n for n in self._graph.nodes if n.node_type == "Custom" and n.label == val_str), None)
                if not software_node:
                    software_node = Node(
                        id=str(uuid.uuid4()),
                        label=val_str,
                        node_type="Custom",
                        description=f"Software extracted from metadata",
                        mermaid_shape="hexagon"
                    )
                    self._graph.add_node(software_node)
                
                # Deduplicate edges
                edge_exists = any(
                    e.source_id == doc_node.id and e.target_id == software_node.id and e.label == "created with"
                    for e in self._graph.edges
                )
                if not edge_exists:
                    edge = Edge(
                        id=str(uuid.uuid4()),
                        source_id=doc_node.id,
                        target_id=software_node.id,
                        label="created with",
                        edge_type="Connected"
                    )
                    self._graph.add_edge(edge)

        self._refresh_all()
        self._set_status(f"Imported metadata from {filename}")
```

---

## 5. Verification Method

To independently verify the implementation, write automated tests in `tests/test_drag_drop_metadata.py` with the following structure:

```python
import os
import pytest
from unittest.mock import patch
from PyQt6.QtCore import QMimeData, QUrl, QPoint, Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QMessageBox

from laitoxx.interfaces.gui.graph_editor import GraphEditorWindow

@pytest.fixture
def graph_editor(qapp):
    # Instantiate the GraphEditorWindow
    window = GraphEditorWindow()
    return window

def test_drag_enter_event(graph_editor):
    # Construct mime data with a file URL
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile("/tmp/dummy.pdf")])
    
    # Create DragEnter event
    event = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    
    # Send event to window
    graph_editor.dragEnterEvent(event)
    assert event.isAccepted(), "Drag enter should be accepted for file URLs"

def test_drop_event_valid_file(graph_editor, tmp_path):
    # Create dummy supported file
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_text("dummy pdf contents")
    
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(pdf_file))])
    
    event = QDropEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QDropEvent.Type.Drop
    )
    
    # Mock metadata extraction
    mock_meta = {
        "FileName": "sample.pdf",
        "FileSize": 1234,
        "Author": "Alice Smith",
        "Software": "LibreOffice Writer"
    }
    
    with patch("laitoxx.features.utilities.metadata_viewer.engine.engine_instance.extract_metadata", return_value=mock_meta):
        graph_editor.dropEvent(event)
        
    # Verify nodes in the graph model
    nodes = graph_editor._graph.nodes
    edges = graph_editor._graph.edges
    
    # 1 Document node, 1 Person node, 1 Custom node
    doc_node = next((n for n in nodes if n.node_type == "Document"), None)
    author_node = next((n for n in nodes if n.node_type == "Person"), None)
    software_node = next((n for n in nodes if n.node_type == "Custom"), None)
    
    assert doc_node is not None
    assert doc_node.label == "sample.pdf"
    
    assert author_node is not None
    assert author_node.label == "Alice Smith"
    
    assert software_node is not None
    assert software_node.label == "Alice Smith" or software_node.label == "LibreOffice Writer"
    
    assert len(edges) == 2, "Should have created 2 edges linking Document to Author and Software"

def test_drop_event_invalid_file(graph_editor, tmp_path):
    # Create dummy unsupported file
    invalid_file = tmp_path / "malicious.bin"
    invalid_file.write_text("malicious shellcode")
    
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(invalid_file))])
    
    event = QDropEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QDropEvent.Type.Drop
    )
    
    with patch("PyQt6.QtWidgets.QMessageBox.warning") as mock_warning:
        graph_editor.dropEvent(event)
        # QMessageBox should be shown and event ignored
        mock_warning.assert_called_once()
        
    # Verify graph model remains empty
    assert len(graph_editor._graph.nodes) == 0
```

### Verification Command
Run the tests using the following command:
```bash
pytest tests/test_drag_drop_metadata.py
```

### Invalidation Conditions
- If PyQt6 is run in a headless environment without `QT_QPA_PLATFORM=offscreen`, the test runner will fail to instantiate the `QApplication`.
- If `engine_instance.extract_metadata` does not handle exceptions gracefully, the drop event will crash the thread instead of displaying a QMessageBox.
