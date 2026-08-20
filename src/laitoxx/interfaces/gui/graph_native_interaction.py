"""Filtering, focus, zoom and input behavior for the native graph view."""

# ruff: noqa: E701, E702

from __future__ import annotations

from PyQt6.QtCore import QPoint, QPointF, Qt

from .graph_native_edge import _NativeEdgeItem
from .graph_native_node import _NativeNodeItem


class NativeViewInteractionMixin:
    def filter_graph(
        self,
        query: str,
        node_type: str = "",
        type_filter_mode: str = "include",
    ) -> None:
        self._query = query.strip().casefold()
        self._type = node_type
        self._type_filter_mode = type_filter_mode if type_filter_mode in {"include", "exclude"} else "include"
        self._apply_filter(fit=True)

    def _apply_filter(self, fit: bool) -> None:
        matches = set()
        for identifier, item in self._node_items.items():
            node = item.node
            haystack = " ".join(
                [node.label, node.node_type, node.description, *map(str, node.metadata.values())]
            ).casefold()
            type_matches = not self._type or ((node.node_type == self._type) == (self._type_filter_mode == "include"))
            if (not self._query or self._query in haystack) and type_matches:
                matches.add(identifier)
        visible = set(self._node_items) if not (self._query or self._type) else set(matches)
        # Text-only searches retain their immediate graph context. A selected
        # entity type is strict: excluded types must never return as neighbours.
        if matches and self._query and not self._type:
            for edge in self._edge_items.values():
                if edge.edge.source_id in matches or edge.edge.target_id in matches:
                    visible.update((edge.edge.source_id, edge.edge.target_id))
        self.show_labels = self._layout_mode == "hierarchy" or len(visible) <= 24
        for identifier, item in self._node_items.items():
            item.setVisible(identifier in visible)
            item.update()
        for item in self._edge_items.values():
            endpoints_visible = item.edge.source_id in visible and item.edge.target_id in visible
            filter_active = bool(self._query or self._type)
            item.setVisible(
                endpoints_visible
                and (filter_active or self._show_secondary_edges or item.edge.id in self._backbone_edge_ids)
            )
            item.setOpacity(1.0)
        if fit:
            self.fit_graph()

    def reset_graph_filter(self) -> None:
        self._query = self._type = ""
        self._type_filter_mode = "include"
        self._apply_filter(fit=False)
        self.clear_emphasis()
        self.focus_root()

    def set_layout_mode(self, mode: str, *, render: bool = True) -> None:
        self._layout_mode = mode
        if render:
            self.render_graph(self._graph)

    def fit_graph(self) -> None:
        visible = [item for item in self._node_items.values() if item.isVisible()]
        if not visible:
            return
        rect = visible[0].sceneBoundingRect()
        for item in visible[1:]:
            rect = rect.united(item.sceneBoundingRect())
        self.resetTransform()
        self.fitInView(rect.adjusted(-80, -80, 80, 80), Qt.AspectRatioMode.KeepAspectRatio)

    def focus_root(self) -> None:
        if not self._node_items or self.viewport().width() <= 10:
            return
        self._focus_pending = False
        self.resetTransform()
        self.scale(0.92, 0.92)
        item = self._node_items.get(self._root_id) or next(iter(self._node_items.values()))
        self.centerOn(item.pos() + QPointF(180, 0) if self._layout_mode == "hierarchy" else item.pos())

    def focus_node(self, identifier: str) -> None:
        item = self._node_items.get(identifier)
        if not item:
            return
        self.resetTransform()
        self.scale(1.08, 1.08)
        self.centerOn(item)
        self.emphasize_neighborhood(identifier)

    def emphasize_neighborhood(self, identifier: str) -> None:
        neighbours = {identifier}
        for edge in self._edge_items.values():
            if identifier in {edge.edge.source_id, edge.edge.target_id}:
                neighbours.update((edge.edge.source_id, edge.edge.target_id))
        self._emphasized_node = identifier
        for node_id, item in self._node_items.items():
            item.setOpacity(1.0 if node_id in neighbours else 0.16)
        for edge in self._edge_items.values():
            incident = identifier in {edge.edge.source_id, edge.edge.target_id}
            edge.setVisible(incident or self._show_secondary_edges or edge.edge.id in self._backbone_edge_ids)
            edge.setOpacity(1.0 if incident else 0.10)
            edge.update_path()

    def emphasize_subgraph(self, node_ids: list[str], edge_ids: list[str]) -> None:
        """Reveal and emphasize the result of a quick analysis algorithm."""
        selected_nodes = set(node_ids)
        selected_edges = set(edge_ids)
        self._emphasized_node = "analysis"
        for identifier, item in self._node_items.items():
            item.setOpacity(1.0 if identifier in selected_nodes else 0.10)
            item.setSelected(identifier in selected_nodes)
        for identifier, item in self._edge_items.items():
            chosen = identifier in selected_edges
            item.setVisible(chosen or identifier in self._backbone_edge_ids)
            item.setOpacity(1.0 if chosen else 0.07)
            item.update_path()
        if selected_nodes:
            self.fit_items(selected_nodes)

    def clear_emphasis(self) -> None:
        self._emphasized_node = ""
        for item in self._node_items.values():
            item.setOpacity(1.0)
            item.setSelected(False)
        for item in self._edge_items.values():
            item.setOpacity(1.0)
            item.update_path()
        self._apply_filter(fit=False)

    def set_secondary_edges_visible(self, visible: bool) -> None:
        self._secondary_edges_requested = bool(visible)
        self._show_secondary_edges = self._secondary_edges_requested or len(self._edge_items) <= 140
        self.clear_emphasis()

    def fit_items(self, identifiers: set[str]) -> None:
        visible = [self._node_items[value] for value in identifiers if value in self._node_items]
        if not visible:
            return
        rect = visible[0].sceneBoundingRect()
        for item in visible[1:]:
            rect = rect.united(item.sceneBoundingRect())
        self.resetTransform()
        self.fitInView(rect.adjusted(-110, -110, 110, 110), Qt.AspectRatioMode.KeepAspectRatio)

    def show_hover_card(self, lines: list[object]) -> None:
        self._hover_text = "\n".join(str(line) for line in lines if line not in (None, ""))
        self._hover_hide_timer.stop()
        self._hover_show_timer.start(120)

    def hide_hover_card(self, *, immediate: bool = False) -> None:
        self._hover_show_timer.stop()
        if immediate:
            self._hover_hide_timer.stop()
            self._hover_card.hide()
        else:
            self._hover_hide_timer.start(180)

    def _display_hover_card(self) -> None:
        if not self._hover_text:
            return
        width = min(390, max(250, self.viewport().width() - 32))
        self._hover_card.setFixedWidth(width)
        self._hover_card.setText(self._hover_text)
        height = min(290, max(64, self._hover_card.heightForWidth(width) + 18))
        self._hover_card.resize(width, height)
        self._position_hover_card()
        self._hover_card.show()
        self._hover_card.raise_()

    def _position_hover_card(self) -> None:
        if not self._hover_card.isVisible() and not self._hover_text:
            return
        x = max(12, self.viewport().width() - self._hover_card.width() - 14)
        self._hover_card.move(x, 14)

    def zoom_graph(self, factor: float) -> None:
        self.scale(float(factor), float(factor))

    def map_web_to_global(self, x: int, y: int) -> QPoint:
        return QPoint(x, y)

    def install_drop_event_filter(self, filter_obj):
        self.installEventFilter(filter_obj)
        self.viewport().installEventFilter(filter_obj)

    def highlight_path(self, identifiers: list[str]) -> None:
        selected = set(identifiers)
        for identifier, item in self._node_items.items():
            item.setSelected(identifier in selected)

    def apply_centrality_sizes(self, scores: dict[str, float]) -> None:
        maximum = max(scores.values(), default=0.0)
        for identifier, item in self._node_items.items():
            item.radius = 25 + (18 * scores.get(identifier, 0.0) / maximum if maximum else 0)
            item.update()

    def filter_by_time_range(self, start: str, end: str) -> None:
        for _identifier, item in self._node_items.items():
            node = item.node
            item.setVisible(
                (not node.valid_from or node.valid_from <= end) and (not node.valid_to or node.valid_to >= start)
            )
        for item in self._edge_items.values():
            item.setVisible(item.source.isVisible() and item.target.isVisible())
        self.fit_graph()

    def wheelEvent(self, event):
        self.zoom_graph(1.18 if event.angleDelta().y() > 0 else 1 / 1.18)
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_hover_card()
        if self._focus_pending and self.viewport().width() > 10:
            self.focus_root()

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if not isinstance(item, (_NativeNodeItem, _NativeEdgeItem)) and event.button() == Qt.MouseButton.LeftButton:
            self.clear_emphasis()
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if not isinstance(item, (_NativeNodeItem, _NativeEdgeItem)):
            self.background_context_requested.emit(event.globalPos().x(), event.globalPos().y())
            event.accept()
            return
        super().contextMenuEvent(event)
