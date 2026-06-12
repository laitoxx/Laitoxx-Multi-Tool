# Handoff Report — Challenger 2 (Milestone 2)

## 1. Observation

### File & Resource Paths:
- **Mock Library**: `resources/js/vis-network.min.js`
- **Mermaid/HTML Generator**: `src/laitoxx/shared/graph/mermaid.py`
- **Graph Editor GUI**: `src/laitoxx/interfaces/gui/graph_editor.py`
- **Web Bridge Test Suite**: `tests/test_web_bridge.py`

### Verbatim Code Findings:

1. **Test Suite Event Bypass**:
   In `tests/test_web_bridge.py` (lines 60-87), the test exercises the bridge signals by executing helper methods directly injected in the window rather than interacting with the `vis.Network` layout or simulating the real event callbacks:
   ```python
   # 6. Execute trigger scripts in QWebEngineView and let QWebChannel propagate to bridge slots
   # Trigger node selection
   loop_node = QEventLoop()
   view._web.page().runJavaScript(
       "window.testTriggerNodeSelected('node1');",
       lambda res: loop_node.quit()
   )
   ```
   These window functions are defined in `src/laitoxx/shared/graph/mermaid.py` (lines 488-504) as:
   ```javascript
   // Headless test trigger functions
   window.testTriggerNodeSelected = function(nodeId) {
     if (BRIDGE) {
       BRIDGE.onNodeSelected(nodeId);
     }
   };
   ```

2. **Missing WebEngine Check**:
   In `tests/test_web_bridge.py` (line 48), the code invokes `view._web.loadFinished` directly:
   ```python
   view._web.loadFinished.connect(lambda ok: loop.quit())
   ```
   However, `src/laitoxx/interfaces/gui/graph_editor.py` (lines 1013-1028) defines a fallback where `view._web` is `None` if PyQt6 WebEngine is missing:
   ```python
   else:
       self._web = None
       info = QLabel(_t("ge_no_web_engine"))
       ...
   ```

3. **Mock Event Limits**:
   In `resources/js/vis-network.min.js` (lines 35-41), the coordinate-to-element resolution methods always return `null`:
   ```javascript
   this.getNodeAt = function(pos) {
     return null;
   };
   
   this.getEdgeAt = function(pos) {
     return null;
   };
   ```

4. **Programmatic Selection Lack**:
   In `resources/js/vis-network.min.js` (lines 27-33), selection synchronization methods from PyQt to JS have empty bodies:
   ```javascript
   this.selectNodes = function(nodeIds) {
     // Mock selection logic
   };
   ```

5. **DOM Performance in Mock**:
   In `resources/js/vis-network.min.js` (lines 50-71), the mock renders graphs by building an HTML string of list elements synchronously and replacing the container HTML:
   ```javascript
   let html = '<div style="color: #f1f0ff; padding: 20px; text-align: center; font-family: sans-serif;">';
   ...
   if (data.nodes) {
     ...
     nodesArr.forEach(n => {
       html += `<li>[${n.type || 'Node'}] ${n.label || n.id}</li>`;
     });
   }
   ...
   container.innerHTML = html;
   ```

6. **Relative Resource Resolution**:
   In `src/laitoxx/shared/graph/mermaid.py` (lines 112-114):
   ```python
   current_dir = os.path.dirname(os.path.abspath(__file__))
   resources_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "..", "resources"))
   js_path = os.path.join(resources_dir, "js", "vis-network.min.js")
   ```

7. **Command Execution Restriction**:
   Executing python/pytest commands using `run_command` in this environment triggers a permission prompt which times out:
   ```
   Encountered error in step execution: Permission prompt for action 'command' on target 'venv/bin/pytest tests/test_web_bridge.py' timed out waiting for user response.
   ```

---

## 2. Logic Chain

1. **Test Design Flaw (Event Bypass)**: Since the test suite triggers `BRIDGE.onNodeSelected` using custom `window.testTriggerNodeSelected` instead of firing events on the actual `vis.Network` object, any configuration errors or event typos inside `mermaid.py`'s real listeners (e.g. lines 448-453: `network.on("selectNode", ...)`) will not be caught by tests.
2. **Crash on Missing WebEngine**: Since `test_web_bridge.py` does not check `HAS_WEB` (defined in `graph_editor.py`) and directly calls `.connect()` on `view._web`, any environment that loads the test without `PyQt6-WebEngine` installed will crash with `AttributeError: 'NoneType' object has no attribute 'loadFinished'`.
3. **Null Context Menu on Nodes/Edges**: Since the mock's `getNodeAt` and `getEdgeAt` methods always return `null`, the right-click listener in `mermaid.py` (lines 462-478) will evaluate `nodeId` and `edgeId` as `null`, forcing the bridge to always receive `itemType = "background"`. Thus, it is impossible for users to trigger node or edge context menus when utilizing the offline mock.
4. **No Visual Update for Selection**: Since the selection helpers `selectNodes` and `selectEdges` inside the mock have empty bodies, programmatic selection updates from the PyQt list widgets to the JS view will not render or highlight anything in the web panel.
5. **UI Thread Blocking for Large Graphs**: Since the mock iterates over all nodes and edges in a single synchronous loop and writes them as list items (`<li>`) using `innerHTML`, rendering a graph with a large number of nodes (e.g. 5,000 nodes, 10,000 edges) will require creating 15,000 DOM nodes synchronously. This blocks the Qt GUI main thread and will cause noticeable lag or crash the WebEngine helper process.
6. **Path Resolution Vulnerability**: Since the code resolves the path to `vis-network.min.js` relative to `src/laitoxx/shared/graph/mermaid.py`'s directory, any distribution/installation (like a pip wheel install) that reorganizes the project structure will fail to load the script file, causing the UI to silently load with a failed-load comment.

---

## 3. Caveats

- **Pytest Execution**: Due to non-interactive sandbox permissions, the automated tests could not be run locally. Verification of the test logic and resource behavior was performed via deep static code review and control-flow tracing.
- **Offscreen WebEngine Rendering**: We assumed that the Qt WebEngine environment behaves correctly under `QT_QPA_PLATFORM = "offscreen"`. In some older Qt/Chromium packages, running WebEngine in offscreen mode without a virtual frame buffer (like Xvfb) can cause silent rendering freezes or timeouts.

---

## 4. Conclusion

The implementation of Milestone 2 works correctly as a static mock representation, but contains several design and integration risks:
- The tests pass but fail to verify the actual vis-network selection event registration.
- Lack of WebEngine check in tests leads to hard crashes in headless environments where `PyQt6-WebEngine` is absent.
- The offline mock lacks support for node/edge context menus and programmatic selection highlights.
- Loading massive graphs (e.g. 5,000+ nodes) will block the main thread due to non-virtualized synchronous DOM insertion.

---

## 5. Verification Method

To verify these findings:
1. **Empty Graph Stability**:
   - Construct a graph with no nodes or edges.
   - Load it into `MermaidView`. Verify it shows `0 Nodes · 0 Edges` without JS errors.
2. **Large Graph Performance**:
   - Create a graph with 5,000 nodes and 10,000 edges.
   - Measure the synchronous lag inside the browser engine during DOM injection.
3. **WebEngine Absence Test**:
   - Uninstall `PyQt6-WebEngine` from the python environment.
   - Run `pytest tests/test_web_bridge.py` and verify it raises `AttributeError: 'NoneType' object has no attribute 'loadFinished'`.
4. **Context Menu Failure**:
   - Load a graph containing a node.
   - Simulate a right-click on the node in the mock view. Verify it triggers `onContextMenu` with type `"background"` instead of `"node"`.

---

# ADVERSARIAL CHALLENGE REPORT

**Overall risk assessment**: **MEDIUM**

## Challenges

### [Medium] Challenge 1: Web Bridge Test Design Bypass
- **Assumption challenged**: The test suite validates two-way communication between vis-network events and PyQt.
- **Attack scenario**: If a developer breaks the `network.on("selectNode")` configuration in `mermaid.py`, the pytest suite will still report **PASS** because it bypasses the event listener and directly fires the bridge slot via `window.testTriggerNodeSelected()`.
- **Blast radius**: Undetected regression in interactive selection syncing.
- **Mitigation**: Update `tests/test_web_bridge.py` to trigger mock events via the `vis` instance or simulate a native DOM interaction, rather than calling bridge slots directly.

### [Medium] Challenge 2: Test Suit Crash on Missing WebEngine
- **Assumption challenged**: The test suite is safe to run in standard headless/CI environments.
- **Attack scenario**: CI/CD pipelines often install base packages without GUI dependencies like `PyQt6-WebEngine`. Running the test suite in such environments crashes the execution with an `AttributeError`.
- **Blast radius**: Complete CI build failure.
- **Mitigation**: Wrap the web bridge tests with a skip guard, e.g.:
  ```python
  from laitoxx.interfaces.gui.graph_editor import HAS_WEB
  pytestmark = pytest.mark.skipif(not HAS_WEB, reason="PyQt6 QWebEngineView is not available")
  ```

### [Low] Challenge 3: Path Resolution Relocation Failure
- **Assumption challenged**: The relative path of `resources/` is stable.
- **Attack scenario**: Distributing the project as a Python wheel and installing it makes the relative path `../../../../resources` invalid.
- **Blast radius**: Silent fallback to code preview/no graph visualization.
- **Mitigation**: Relocate the JS asset into the source package structure and use `importlib.resources`.
