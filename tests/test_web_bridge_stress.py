import os
import sys
import time
import pytest
import resource
from PyQt6.QtCore import QEventLoop, QTimer, Qt
from PyQt6.QtWidgets import QApplication


# Force offscreen QPA platform for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from laitoxx.shared.graph.model import Graph, Node, Edge
from laitoxx.interfaces.gui.graph_editor import GraphEditorWindow

@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication(["-platform", "offscreen"])
    yield app

def get_memory_usage_kb():
    """Get the resident set size (RSS) in kilobytes."""
    # resource.getrusage returns bytes on macOS but kilobytes on Linux.
    # On Linux, ru_maxrss is in kilobytes.
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return usage

def test_rapid_selection_and_rendering_stress(qapp):
    # 1. Create a medium-sized graph
    graph = Graph("Stress Test Graph")
    nodes = []
    for i in range(50):
        n = Node(id=f"node_{i}", label=f"Node {i}", node_type="Person")
        graph.add_node(n)
        nodes.append(n)
        
    for i in range(49):
        e = Edge(id=f"edge_{i}", source_id=nodes[i].id, target_id=nodes[i+1].id, label="link")
        graph.add_edge(e)
        
    # 2. Instantiate GraphEditorWindow
    window = GraphEditorWindow()
    window._graph = graph
    window._refresh_all()
    window.show()
    
    # Process initial events to load QWebEngineView and register bridge
    QApplication.processEvents()
    
    # Wait for the initial page load to finish
    loop = QEventLoop()
    window._mermaid_view._web.loadFinished.connect(lambda ok: loop.quit())
    
    # 5s safety timeout
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(5000)
    loop.exec()
    timer.stop()

    # Track initial memory usage
    initial_mem = get_memory_usage_kb()
    print(f"\n[STRESS TEST] Initial memory usage: {initial_mem} KB")

    # ==========================================
    # SCENARIO 1: Rapid Python-to-JS Selection
    # Simulates rapidly clicking nodes in the list view.
    # ==========================================
    t0 = time.time()
    num_clicks = 200
    print(f"[STRESS TEST] Running Scenario 1: {num_clicks} rapid Python list selections...")
    
    for i in range(num_clicks):
        node_id = f"node_{i % 50}"
        # Trigger list selection change manually
        # Find item in the list
        item = None
        for r in range(window._nodes_list.count()):
            it = window._nodes_list.item(r)
            if it.data(Qt.ItemDataRole.UserRole) == node_id:
                item = it
                break
        assert item is not None
        window._nodes_list.setCurrentItem(item)
        QApplication.processEvents()
        
    t1 = time.time()
    scenario_1_time = t1 - t0
    mem_after_s1 = get_memory_usage_kb()
    print(f"[STRESS TEST] Scenario 1 finished in {scenario_1_time:.2f}s (avg {(scenario_1_time/num_clicks)*1000:.2f}ms/click)")
    print(f"[STRESS TEST] Memory after Scenario 1: {mem_after_s1} KB (change: {mem_after_s1 - initial_mem} KB)")

    # ==========================================
    # SCENARIO 2: Rapid JS-to-Python Selection
    # Simulates rapidly receiving node selections from the QWebChannel bridge.
    # ==========================================
    t0 = time.time()
    print(f"[STRESS TEST] Running Scenario 2: {num_clicks} rapid WebChannel bridge selection triggers...")
    
    for i in range(num_clicks):
        node_id = f"node_{i % 50}"
        # Directly emit the bridge's node_selected signal, mimicking JavaScript IPC calls
        window._mermaid_view._bridge.node_selected.emit(node_id)
        QApplication.processEvents()
        
    t1 = time.time()
    scenario_2_time = t1 - t0
    mem_after_s2 = get_memory_usage_kb()
    print(f"[STRESS TEST] Scenario 2 finished in {scenario_2_time:.2f}s (avg {(scenario_2_time/num_clicks)*1000:.2f}ms/event)")
    print(f"[STRESS TEST] Memory after Scenario 2: {mem_after_s2} KB (change: {mem_after_s2 - mem_after_s1} KB)")

    # ==========================================
    # SCENARIO 3: Alternating/Ping-Pong Selection
    # Simulates selection coming from both sources in alternation to test for loop loops.
    # ==========================================
    t0 = time.time()
    print(f"[STRESS TEST] Running Scenario 3: {num_clicks} alternating selection triggers (list and bridge)...")
    
    for i in range(num_clicks):
        node_id = f"node_{i % 50}"
        if i % 2 == 0:
            # Select via list
            item = None
            for r in range(window._nodes_list.count()):
                it = window._nodes_list.item(r)
                if it.data(Qt.ItemDataRole.UserRole) == node_id:
                    item = it
                    break
            window._nodes_list.setCurrentItem(item)
        else:
            # Select via bridge
            window._mermaid_view._bridge.node_selected.emit(node_id)
        QApplication.processEvents()
        
    t1 = time.time()
    scenario_3_time = t1 - t0
    mem_after_s3 = get_memory_usage_kb()
    print(f"[STRESS TEST] Scenario 3 finished in {scenario_3_time:.2f}s")
    print(f"[STRESS TEST] Memory after Scenario 3: {mem_after_s3} KB (change: {mem_after_s3 - mem_after_s2} KB)")

    # ==========================================
    # SCENARIO 4: Rapid Re-Rendering
    # Repeatedly renders the graph to stress-test HTML/JS reloading.
    # ==========================================
    t0 = time.time()
    num_renders = 30
    print(f"[STRESS TEST] Running Scenario 4: {num_renders} rapid graph renders...")
    
    for i in range(num_renders):
        window._refresh_all()
        # Let QWebEngineView start loading the new HTML
        QApplication.processEvents()
        time.sleep(0.02) # brief sleep to simulate rapid rendering in sequence
        
    t1 = time.time()
    scenario_4_time = t1 - t0
    mem_after_s4 = get_memory_usage_kb()
    print(f"[STRESS TEST] Scenario 4 finished in {scenario_4_time:.2f}s")
    print(f"[STRESS TEST] Memory after Scenario 4: {mem_after_s4} KB (change: {mem_after_s4 - mem_after_s3} KB)")

    # Assertions to verify correctness
    # Verify last selected node is correctly tracked in the properties panel
    last_node_id = f"node_{(num_clicks - 1) % 50}"
    assert window._node_props._current_id == last_node_id, f"Expected selected node to be {last_node_id}, got {window._node_props._current_id}"
    
    # Verify no infinite recursion occurred (the python interpreter did not raise RecursionError and we reached the end of the test)
    print(f"[STRESS TEST] Total memory growth: {mem_after_s4 - initial_mem} KB")
    window.close()
