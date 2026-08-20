"""Layout behavior for the native graph view."""

# ruff: noqa: E701, E702

from __future__ import annotations

from collections import deque

from PyQt6.QtCore import QPointF

from laitoxx.shared.graph.algorithms import (
    calculate_cluster_layout,
    detect_graph_communities,
)
from laitoxx.shared.graph.model import Graph


class NativeViewLayoutMixin:
    def _layout_positions(self, graph: Graph) -> dict[str, QPointF]:
        nodes = graph.nodes[: self.MAX_RENDER_NODES]
        if not nodes:
            return {}
        ids = {node.id for node in nodes}
        adjacent = {node.id: [] for node in nodes}
        for edge in graph.edges[: self.MAX_RENDER_EDGES]:
            if edge.source_id in ids and edge.target_id in ids:
                adjacent[edge.source_id].append(edge.target_id)
                adjacent[edge.target_id].append(edge.source_id)
        target = next((node for node in nodes if node.metadata.get("is_target")), None)
        root = target.id if target else max(nodes, key=lambda node: (len(adjacent[node.id]), -nodes.index(node))).id
        levels, parents, seen, queue = {root: 0}, {}, {root}, deque([root])
        while queue:
            current = queue.popleft()
            for neighbour in adjacent[current]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    levels[neighbour] = levels[current] + 1
                    parents[neighbour] = current
                    queue.append(neighbour)
        next_level = max(levels.values(), default=0) + 1
        for node in nodes:
            if node.id not in levels:
                levels[node.id] = next_level
        rings: dict[int, list[str]] = {}
        for identifier, level in levels.items():
            rings.setdefault(level, []).append(identifier)
        self._root_id = root
        type_by_id = {node.id: node.node_type for node in nodes}
        result = {root: QPointF(0, 0)}
        if self._layout_mode == "hierarchy":
            self._layout_communities = []
            for level, identifiers in rings.items():
                if level == 0:
                    continue
                identifiers.sort(
                    key=lambda identifier: (
                        result.get(parents.get(identifier, ""), QPointF()).y(),
                        type_by_id.get(identifier, ""),
                        -len(adjacent[identifier]),
                        identifier,
                    )
                )
                spacing = 84
                top = -((len(identifiers) - 1) * spacing) / 2
                for index, identifier in enumerate(identifiers):
                    result[identifier] = QPointF(level * 310, top + index * spacing)
            return result
        self._layout_communities = detect_graph_communities(
            graph,
            root_id=root,
            max_nodes=self.MAX_RENDER_NODES,
            max_edges=self.MAX_RENDER_EDGES,
        )
        clustered = calculate_cluster_layout(
            graph,
            root_id=root,
            max_nodes=self.MAX_RENDER_NODES,
            max_edges=self.MAX_RENDER_EDGES,
            communities=self._layout_communities,
        )
        return {identifier: QPointF(x, y) for identifier, (x, y) in clustered.items()}
