"""Rendering and theme behavior for the native graph view."""

# ruff: noqa: E701, E702

from __future__ import annotations

import math
import re
from collections import deque

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QGraphicsPathItem,
)

from laitoxx.interfaces.gui.design_system import resolved_theme
from laitoxx.shared.graph.algorithms import (
    detect_graph_communities,
    find_relevant_connections,
)
from laitoxx.shared.graph.model import Edge, Graph

from .graph_native_edge import _NativeEdgeItem
from .graph_native_node import _NativeNodeItem
from .graph_native_style import _TYPE_PALETTE, _TYPE_THEME_KEYS


class NativeViewRenderMixin:
    @staticmethod
    def _parse_color(value: str, fallback: str) -> QColor:
        color = QColor(str(value))
        if color.isValid():
            return color
        parts = re.findall(r"[\d.]+", str(value))
        if len(parts) >= 3:
            alpha = float(parts[3]) if len(parts) > 3 else 1.0
            alpha = alpha if alpha <= 1 else alpha / 255
            return QColor(int(float(parts[0])), int(float(parts[1])), int(float(parts[2])), round(alpha * 255))
        return QColor(fallback)

    def theme_color(self, key: str, fallback: str) -> QColor:
        return self._parse_color(self._theme.get(key, fallback), fallback)

    def node_color(self, node_type: str) -> QColor:
        fallback = _TYPE_PALETTE.get(node_type, "#a78bfa")
        theme_key = _TYPE_THEME_KEYS.get(node_type)
        return self.theme_color(theme_key, fallback) if theme_key else QColor(fallback)

    def apply_theme(self, theme: dict) -> None:
        self._theme = resolved_theme(theme)
        canvas = self._theme["surface_work_color"]
        border = self._theme["border_subtle_color"]
        self.setBackgroundBrush(self.theme_color("surface_work_color", "#101116"))
        self.setStyleSheet(f"QGraphicsView {{ background: {canvas}; border: 1px solid {border}; border-radius: 9px; }}")
        surface = self._theme["surface_raised_color"]
        text = self._theme["text_primary_color"]
        self._hover_card.setStyleSheet(
            "QLabel#GraphHoverCard {"
            f"background: {surface}; color: {text}; border: 1px solid {border};"
            "border-radius: 9px; padding: 10px; font-size: 11px;"
            "}"
        )
        for edge in self._edge_items.values():
            edge.update_path()
        for node in self._node_items.values():
            node.update()
        self.viewport().update()

    def render_graph(self, graph: Graph) -> None:
        self._graph = graph
        self._emphasized_node = ""
        self.hide_hover_card(immediate=True)
        self._scene.clear()
        self._node_items.clear()
        self._edge_items.clear()
        positions = self._layout_positions(graph)
        if self._layout_mode == "network":
            self._draw_community_hulls(graph, positions)
        degree = {node.id: 0 for node in graph.nodes[: self.MAX_RENDER_NODES]}
        self._backbone_edge_ids = self._build_backbone_edge_ids(graph)
        renderable_edges = graph.edges[: self.MAX_RENDER_EDGES]
        self._show_secondary_edges = self._secondary_edges_requested or len(renderable_edges) <= 140
        for edge in renderable_edges:
            if edge.source_id in degree and edge.target_id in degree:
                degree[edge.source_id] += 1
                degree[edge.target_id] += 1
        maximum_degree = max(degree.values(), default=1) or 1
        for node in graph.nodes[: self.MAX_RENDER_NODES]:
            item = _NativeNodeItem(node, self, positions.get(node.id, QPointF()))
            if self._layout_mode == "network":
                item.radius = (
                    36.0 if node.id == self._root_id else 20.0 + 10.0 * math.sqrt(degree[node.id] / maximum_degree)
                )
            self._node_items[node.id] = item
            self._scene.addItem(self._node_items[node.id])
        for edge in graph.edges[: self.MAX_RENDER_EDGES]:
            source, target = self._node_items.get(edge.source_id), self._node_items.get(edge.target_id)
            if source and target:
                item = _NativeEdgeItem(edge, source, target, self)
                self._edge_items[edge.id] = item
                self._scene.addItem(item)
        self._apply_filter(fit=False)
        bounds = self._scene.itemsBoundingRect()
        self._scene.setSceneRect(bounds.adjusted(-180, -180, 180, 180))
        self._focus_pending = True
        QTimer.singleShot(0, self.focus_root)

    def _draw_community_hulls(self, graph: Graph, positions: dict[str, QPointF]) -> None:
        node_by_id = {node.id: node for node in graph.nodes[: self.MAX_RENDER_NODES]}
        communities = self._layout_communities or detect_graph_communities(
            graph,
            root_id=self._root_id,
            max_nodes=self.MAX_RENDER_NODES,
            max_edges=self.MAX_RENDER_EDGES,
        )
        for index, community in enumerate(communities):
            points = [positions[identifier] for identifier in community if identifier in positions]
            if len(points) < 2:
                continue
            left = min(point.x() for point in points) - 58
            top = min(point.y() for point in points) - 58
            right = max(point.x() for point in points) + 58
            bottom = max(point.y() for point in points) + 58
            path = QPainterPath()
            path.addRoundedRect(QRectF(left, top, right - left, bottom - top), 42, 42)
            item = QGraphicsPathItem(path)
            representative = next((node_by_id[value] for value in sorted(community) if value in node_by_id), None)
            color = self.node_color(representative.node_type if representative else "Custom")
            fill = QColor(color)
            fill.setAlpha(12 if index else 18)
            outline = QColor(color)
            outline.setAlpha(48)
            item.setBrush(fill)
            item.setPen(QPen(outline, 1.2, Qt.PenStyle.DashLine))
            item.setZValue(-3)
            self._scene.addItem(item)

    def _build_backbone_edge_ids(self, graph: Graph) -> set[str]:
        edges = [edge for edge in graph.edges[: self.MAX_RENDER_EDGES] if edge.source_id != edge.target_id]
        if len(edges) <= 140:
            return {edge.id for edge in edges}
        adjacency: dict[str, list[Edge]] = {}
        for edge in edges:
            adjacency.setdefault(edge.source_id, []).append(edge)
            adjacency.setdefault(edge.target_id, []).append(edge)
        retained: set[str] = set()
        seen: set[str] = set()
        seeds = [self._root_id, *sorted(adjacency)]
        for seed in seeds:
            if not seed or seed in seen or seed not in adjacency:
                continue
            seen.add(seed)
            queue = deque([seed])
            while queue:
                current = queue.popleft()
                for edge in sorted(adjacency[current], key=lambda item: item.id):
                    neighbour = edge.target_id if edge.source_id == current else edge.source_id
                    if neighbour in seen:
                        continue
                    seen.add(neighbour)
                    queue.append(neighbour)
                    retained.add(edge.id)
        for mode, limit in (("bridges", 36), ("strong", 28), ("target_paths", 20)):
            insight = find_relevant_connections(graph, mode, limit=limit)
            retained.update(str(identifier) for identifier in insight["edges"])
        return retained
