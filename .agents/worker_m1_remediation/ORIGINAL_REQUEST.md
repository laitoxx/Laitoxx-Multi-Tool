## 2026-06-11T14:05:10Z
You are the Worker for Milestone 1 Correctness Remediation.
Your task is to implement the following logic fixes and updates:
1. In `/home/vdox/github_repos/Laitoxx-Multi-Tool/src/laitoxx/shared/graph/model.py`, modify `merge_nodes` so that only edges connected to the merged nodes (`primary_id` or `valid_dup_ids`) are re-routed, self-loop filtered, and deduplicated. All other unrelated edges in the graph (including unrelated self-loops and unrelated multi-edges) must be left completely unchanged.
2. In `/home/vdox/github_repos/Laitoxx-Multi-Tool/src/laitoxx/shared/graph/algorithms.py`, update the graph algorithms to filter out dangling edges (edges where either the source or target node ID does not exist in the graph's nodes) before populating the NetworkX graph.
3. In `/home/vdox/github_repos/Laitoxx-Multi-Tool/tests/test_graph_api.py`, add new test cases to verify:
   - Unrelated self-loops are NOT deleted when merging nodes.
   - Unrelated duplicate/multi-edges are NOT deduplicated or merged when merging other unrelated nodes.
   - Centrality calculations ignore dangling edges and do not skew metrics.
4. Run `python3 -m pytest tests/test_graph_api.py` to verify that all tests pass.
5. Write your detailed handoff report to `/home/vdox/github_repos/Laitoxx-Multi-Tool/.agents/worker_m1_remediation/handoff.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
