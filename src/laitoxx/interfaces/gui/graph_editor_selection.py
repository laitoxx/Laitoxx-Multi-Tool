"""Focused GraphEditorWindow responsibility mixin."""
# ruff: noqa: F405

from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
)
from PyQt6.QtWidgets import (
    QListWidgetItem,
)

from laitoxx.shared.graph.mermaid import generate_mermaid

from .graph_ui_style import *  # noqa: F403


class GraphEditorSelectionMixin:
    def _on_node_selected(self, current, previous):
        if not current:
            self._node_props.clear()
            return
        node_id = current.data(Qt.ItemDataRole.UserRole)
        node = self._graph.get_node(node_id)
        self._node_props.load_node(node)
        self._edge_props.clear()

    def _on_edge_selected(self, current, previous):
        if not current:
            self._edge_props.clear()
            return
        edge_id = current.data(Qt.ItemDataRole.UserRole)
        edge = self._graph.get_edge(edge_id)
        self._edge_props.load_edge(edge, self._graph)
        self._node_props.clear()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_all(self):
        if not self._embedded_analysis_mode:
            self._refresh_nodes_list()
            self._refresh_edges_list()
        self._sync_analysis_filters()
        self._refresh_view()

    def _refresh_nodes_list(self):
        self._nodes_list.setUpdatesEnabled(False)
        self._nodes_list.blockSignals(True)
        self._nodes_list.clear()
        for node in self._graph.nodes:
            item = QListWidgetItem(f"  {node.node_type}  ·  {node.label}")
            item.setData(Qt.ItemDataRole.UserRole, node.id)
            item.setToolTip(f"ID: {node.id}\n{node.description}")
            self._nodes_list.addItem(item)
        self._nodes_list.blockSignals(False)
        self._nodes_list.setUpdatesEnabled(True)

    def _refresh_edges_list(self):
        nodes = {node.id: node for node in self._graph.nodes}
        self._edges_list.setUpdatesEnabled(False)
        self._edges_list.blockSignals(True)
        self._edges_list.clear()
        for edge in self._graph.edges:
            src = nodes.get(edge.source_id)
            tgt = nodes.get(edge.target_id)
            s = src.label if src else edge.source_id
            t = tgt.label if tgt else edge.target_id
            prefix = f"{edge.label}  " if edge.label else ""
            item = QListWidgetItem(f"  {prefix}{s}  →  {t}")
            item.setData(Qt.ItemDataRole.UserRole, edge.id)
            self._edges_list.addItem(item)
        self._edges_list.blockSignals(False)
        self._edges_list.setUpdatesEnabled(True)

    def _refresh_view(self):
        self._mermaid_view.render_graph(self._graph)
        if not self._embedded_analysis_mode:
            self._raw_code.setPlainText(generate_mermaid(self._graph))

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _set_status(self, msg: str):
        self._status.setText(msg)
        self._node_count.setText(_t("ge_node_count", n=len(self._graph.nodes)))
        self._edge_count.setText(_t("ge_edge_count", n=len(self._graph.edges)))

    def _install_mermaid_event_filters(self):
        if hasattr(self, "_mermaid_view") and self._mermaid_view:
            self._mermaid_view.install_drop_event_filter(self)

    def eventFilter(self, watched, event):
        from PyQt6.QtCore import QEvent

        if event.type() == QEvent.Type.DragEnter:
            self.dragEnterEvent(event)
            return event.isAccepted()
        elif event.type() == QEvent.Type.DragMove:
            self.dragMoveEvent(event)
            return event.isAccepted()
        elif event.type() == QEvent.Type.Drop:
            self.dropEvent(event)
            return event.isAccepted()
        return super().eventFilter(watched, event)
