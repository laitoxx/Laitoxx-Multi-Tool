## Challenge Summary

**Overall risk assessment**: MEDIUM

## Challenges

### [High] Challenge 1: Package Resource Loading Failures

- **Assumption challenged**: The resources folder is always located at `../../../../resources` relative to the python source code.
- **Attack scenario**: Deploying the Laitoxx multi-tool as a standard wheel/packaged Python library and running it. The resources folder is not included or packaged at the relative path.
- **Blast radius**: The graph editor fails to load `vis-network.min.js`, leaving the `QWebEngineView` blank or showing JavaScript reference errors.
- **Mitigation**: Package JS assets inside the python package structure and load using `importlib.resources`.

### [Medium] Challenge 2: Headless or CI Environments without WebEngine

- **Assumption challenged**: PyQt6 QWebEngineWidgets is always available on target platforms.
- **Attack scenario**: Running automated tests or running Laitoxx inside Docker containers or server environments lacking GUI display buffers or QtWebEngine packages.
- **Blast radius**: `HAS_WEB` becomes False. The GUI falls back gracefully to a read-only `QTextEdit` showing Mermaid strings, which is functional but lacks any interactivity.
- **Mitigation**: The code already includes a graceful fallback (`HAS_WEB = False` catch block), but tests running on server/CI must ensure proper virtual framebuffers (like `xvfb`) and PySide6/PyQt6 webengine dependencies are pre-installed.

### [Low] Challenge 3: Scale and Performance with Custom SVGs

- **Assumption challenged**: Rendering nodes via dynamic inline SVG Data URLs scales efficiently.
- **Attack scenario**: Loading a large OSINT graph containing >1000 nodes and edges.
- **Blast radius**: vis-network has to render 1000+ custom SVGs from Data URLs, leading to severe rendering lag, slow physics layout resolution, and high memory utilization.
- **Mitigation**: Switch to vis-network native shapes (e.g., `'dot'`, `'square'`) when the node count exceeds a certain threshold (e.g., 200 nodes), bypassing custom SVG generation.

## Stress Test Results

- **Headless QWebEngineView and QWebChannel Integration** → Verified that `tests/test_web_bridge.py` sets `QT_QPA_PLATFORM="offscreen"` and runs QEventLoop to wait for QWebEngineView loading, which runs correctly in a headless test runner → **PASS**

## Unchallenged Areas

- **Metadata extraction and temporal timeline filtering logic** — Out of scope for Milestone 2 reviews.
