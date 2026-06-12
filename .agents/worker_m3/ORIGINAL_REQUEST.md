## 2026-06-11T15:27:35Z

You are Worker 3 for Milestone 3 (Drag-and-Drop Metadata Extraction).
Your working directory is /home/vdox/github_repos/Laitoxx-Multi-Tool/.agents/worker_m3/
Your mission is to implement the Drag-and-Drop Metadata Extraction functionality and write automated tests to verify it.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Key Requirements:
1. Intercept DragEnter and Drop events in `graph_editor.py` (specifically in the main window or `_center_panel` where files are dropped).
   - Install an event filter on MermaidView's child widgets (like `_web` and `_text`) so that drops bubble up or are forwarded to `GraphEditorWindow`.
   - Set `setAcceptDrops(True)` on `GraphEditorWindow`.
   - Check the file extensions of dropped files. Supported extensions are: .pdf, .png, .jpg, .jpeg, .tiff, .mp3, .wav, .mp4, .avi, .doc, .xls, .ppt, .docx, .xlsx, .pptx, .exe, .dll, .sys.
   - If any dropped file has an unsupported type, display a QMessageBox warning and abort the entire drop.
2. Integrate `MetadataEngine` (from `src/laitoxx/features/utilities/metadata_viewer/engine.py` using `engine_instance`) to extract metadata.
3. Automatically populate the Python graph model:
   - Create a `Document` node for the file. The node should store the extracted metadata in its `metadata` attribute.
   - Extract authors using keys `"Author"`, `"Creator"`, `"Producer"`, `"OwnerName"`. If present, create linked `Person` nodes with `"created/edited"` edges.
   - Extract software using keys `"EXIF:Software"`, `"Software"`, `"Tika:creator"`, `"Hachoir:Software"`. If present, create linked `Custom` nodes with `mermaid_shape="hexagon"` and `"created with"` edges.
   - Apply entity resolution/deduplication: check existing nodes/edges by label and type in the Python graph model, and reuse them if they match.
4. Push updates to the UI's `vis-network` (canvas) dynamically via QWebChannel/runJavaScript without reloading the page.
   - Expose Javascript functions `window.addNode(n)` and `window.addEdge(e)` inside the HTML generation template in `src/laitoxx/shared/graph/mermaid.py`.
   - Implement dynamic node/edge addition wrappers in `MermaidView` that call these functions on the web page.
   - Or implement a dynamic diff-based `window.updateGraph` function that refreshes the canvas and updates the stats badge dynamically.
5. Create automated pytest tests in `tests/test_drag_drop_import.py` simulating drag-and-drop file imports (both valid case adding nodes and invalid case showing QMessageBox warning). Make sure to set `QT_QPA_PLATFORM = "offscreen"` to allow tests to run headlessly.
6. Verify your implementation by running the newly created pytest tests and any other affected tests in `tests/`.

Please write a comprehensive handoff report at `/home/vdox/github_repos/Laitoxx-Multi-Tool/.agents/worker_m3/handoff.md` summarizing the changes made, the exact test execution commands, and test run output demonstrating that all tests pass.
When done, notify the orchestrator (recipient ID: e30ef7fa-e46f-4da3-905d-a59ce54dfa77).
