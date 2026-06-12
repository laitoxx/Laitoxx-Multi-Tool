## 2026-06-11T13:35:39Z
Perform a comprehensive exploration of the codebase to understand how to implement the OSINT upgrade requirements.
1. Find where QWebEngineView, _center_panel, Graph, Node, Edge, and Mermaid.js are defined.
2. Locate MetadataEngine, Document node, Person node, and files related to metadata extraction.
3. Check the existing testing setup, in particular where tests/test_graph_api.py should go.
4. Recommend how to bundle vis-network.min.js and structure the two-way Python-JS communication (using QWebChannel).
5. Suggest the structure for: Entity Resolution API, Temporal Graph filter/slider, NetworkX integration for Shortest Path and Centrality.
6. Propose a milestone decomposition (3-7 milestones) and any interface contracts.

Write your report to `/home/vdox/github_repos/Laitoxx-Multi-Tool/.agents/explorer_investigation/handoff.md`. Once complete, send me a message coordinating your findings.
