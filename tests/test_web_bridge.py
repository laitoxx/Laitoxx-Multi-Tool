import os
import sys
import pytest
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication

# Force offscreen QPA platform for headless testing before importing PyQt6 GUI elements
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from laitoxx.shared.graph.model import Graph, Node, Edge
from laitoxx.interfaces.gui.graph_editor import MermaidView

@pytest.fixture(scope="session", autouse=True)
def qapp():
    # Retrieve or create offscreen QApplication instance
    app = QApplication.instance() or QApplication(["-platform", "offscreen"])
    yield app

def test_web_bridge_two_way_communication(qapp):
    # 1. Create a test graph
    graph = Graph("Test Graph")
    n1 = Node(id="node1", label="Node 1", node_type="Person")
    n2 = Node(id="node2", label="Node 2", node_type="Email")
    edge = Edge(id="edge1", source_id="node1", target_id="node2", label="connects")
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_edge(edge)

    # 2. Instantiate MermaidView which holds QWebEngineView and registers the bridge
    view = MermaidView()
    
    received_node_selections = []
    received_edge_selections = []
    received_context_menus = []

    # 3. Connect signals
    view.node_selected.connect(lambda node_id: received_node_selections.append(node_id))
    view.edge_selected.connect(lambda edge_id: received_edge_selections.append(edge_id))
    view.context_menu_requested.connect(
        lambda item_type, item_id, x, y: received_context_menus.append((item_type, item_id, x, y))
    )

    # 4. Render graph (this loads generated HTML with the embedded vis-network and web channel)
    view.render_graph(graph)

    # 5. Wait for the page load to finish
    loop = QEventLoop()
    view._web.loadFinished.connect(lambda ok: loop.quit())
    
    # 5s safety timeout
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(5000)
    
    loop.exec()
    assert timer.isActive(), "QWebEngineView page load timed out"
    timer.stop()

    # 6. Execute trigger scripts in QWebEngineView and let QWebChannel propagate to bridge slots
    # Trigger node selection
    loop_node = QEventLoop()
    view._web.page().runJavaScript(
        "window.testTriggerNodeSelected('node1');",
        lambda res: loop_node.quit()
    )
    loop_node.exec()
    QApplication.processEvents()

    # Trigger edge selection
    loop_edge = QEventLoop()
    view._web.page().runJavaScript(
        "window.testTriggerEdgeSelected('edge1');",
        lambda res: loop_edge.quit()
    )
    loop_edge.exec()
    QApplication.processEvents()

    # Trigger context menu
    loop_ctx = QEventLoop()
    view._web.page().runJavaScript(
        "window.testTriggerContextMenu('node', 'node1', 100, 200);",
        lambda res: loop_ctx.quit()
    )
    loop_ctx.exec()
    QApplication.processEvents()

    # 7. Assertions
    assert "node1" in received_node_selections, f"Expected node1 selection, got: {received_node_selections}"
    assert "edge1" in received_edge_selections, f"Expected edge1 selection, got: {received_edge_selections}"
    assert ("node", "node1", 100, 200) in received_context_menus, f"Expected context menu at (100, 200), got: {received_context_menus}"
