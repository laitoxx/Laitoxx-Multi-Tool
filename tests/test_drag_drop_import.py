import os
import sys
import pytest
from PyQt6.QtCore import QMimeData, QUrl, QPoint, QPointF, Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QApplication

# Force offscreen QPA platform for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from laitoxx.shared.graph.model import Graph, Node, Edge
from laitoxx.interfaces.gui.graph_editor import GraphEditorWindow

@pytest.fixture(scope="session", autouse=True)
def qapp():
    # Retrieve or create offscreen QApplication instance
    app = QApplication.instance() or QApplication(["-platform", "offscreen"])
    yield app

def test_drag_drop_valid_file(qapp, tmp_path, monkeypatch):
    # Mock metadata engine to return specific metadata
    dummy_metadata = {
        "FileName": "document.pdf",
        "Author": "John Doe",
        "Software": "Adobe Photoshop",
        "FilePath": str(tmp_path / "document.pdf")
    }
    monkeypatch.setattr(
        "laitoxx.features.utilities.metadata_viewer.engine.MetadataEngine.extract_metadata",
        lambda self, filepath: dummy_metadata
    )
    
    # Create actual file
    filepath = tmp_path / "document.pdf"
    filepath.write_text("test")
    
    window = GraphEditorWindow()
    
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(filepath))])
    
    # Simulate drag enter
    drag_event = QDragEnterEvent(
        QPoint(0, 0),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    window.dragEnterEvent(drag_event)
    assert drag_event.isAccepted()
    
    # Simulate drop
    drop_event = QDropEvent(
        QPointF(0.0, 0.0),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    window.dropEvent(drop_event)
    assert drop_event.isAccepted()
    
    # Verify graph model population
    nodes = window._graph.nodes
    edges = window._graph.edges
    
    # 1. Document node
    doc_node = next((n for n in nodes if n.node_type == "Document"), None)
    assert doc_node is not None
    assert doc_node.label == "document.pdf"
    assert doc_node.metadata["Author"] == "John Doe"
    
    # 2. Person node
    person_node = next((n for n in nodes if n.node_type == "Person"), None)
    assert person_node is not None
    assert person_node.label == "John Doe"
    
    # 3. Custom (Software) node
    soft_node = next((n for n in nodes if n.node_type == "Custom"), None)
    assert soft_node is not None
    assert soft_node.label == "Adobe Photoshop"
    assert soft_node.mermaid_shape == "hexagon"
    
    # 4. Edges
    assert len(edges) == 2
    e_created = next((e for e in edges if e.label == "created/edited"), None)
    assert e_created is not None
    assert e_created.source_id == person_node.id
    assert e_created.target_id == doc_node.id
    
    e_with = next((e for e in edges if e.label == "created with"), None)
    assert e_with is not None
    assert e_with.source_id == doc_node.id
    assert e_with.target_id == soft_node.id


def test_drag_drop_invalid_file(qapp, tmp_path, monkeypatch):
    # Create unsupported file
    filepath = tmp_path / "test.xyz"
    filepath.write_text("test")
    
    warning_shown = []
    def mock_warning(parent, title, text, buttons):
        warning_shown.append(text)
        return buttons
        
    monkeypatch.setattr("PyQt6.QtWidgets.QMessageBox.warning", mock_warning)
    
    window = GraphEditorWindow()
    
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(filepath))])
    
    # Simulate drop
    drop_event = QDropEvent(
        QPointF(0.0, 0.0),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    window.dropEvent(drop_event)
    
    # Assert aborted
    assert not drop_event.isAccepted()
    assert len(warning_shown) == 1
    assert "xyz" in warning_shown[0]
    
    # Graph must be empty
    assert len(window._graph.nodes) == 0
    assert len(window._graph.edges) == 0


def test_event_filter_forwarding(qapp, tmp_path, monkeypatch):
    # Mock extract_metadata
    monkeypatch.setattr(
        "laitoxx.features.utilities.metadata_viewer.engine.MetadataEngine.extract_metadata",
        lambda self, filepath: {"FileName": os.path.basename(filepath)}
    )
    
    filepath = tmp_path / "valid.png"
    filepath.write_text("test")
    
    window = GraphEditorWindow()
    
    target_widget = window._mermaid_view._web if window._mermaid_view._web else window._mermaid_view._text
    assert target_widget is not None
    
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(filepath))])
    
    drag_event = QDragEnterEvent(
        QPoint(0, 0),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    
    # Send event using QApplication.sendEvent
    QApplication.sendEvent(target_widget, drag_event)
    assert drag_event.isAccepted()
