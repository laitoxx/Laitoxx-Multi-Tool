"""Focused GraphEditorWindow responsibility mixin."""
# ruff: noqa: F405

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import (
    Qt,
)
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from laitoxx.core.settings.paths import GRAPHS_DIR
from laitoxx.interfaces.gui.graph_analysis_dialogs import CentralityDialog, ShortestPathDialog
from laitoxx.interfaces.gui.graph_edge_dialog import EdgeDialog
from laitoxx.interfaces.gui.graph_node_dialog import NodeDialog, _dialog_ss
from laitoxx.shared.graph.mermaid import generate_mermaid
from laitoxx.shared.graph.model import (
    Graph,
)

from .graph_ui_style import *  # noqa: F403


class GraphEditorCommandsMixin:
    def _new_graph(self):
        if self._graph.nodes or self._graph.edges:
            reply = QMessageBox.question(
                self,
                _t("ge_new"),
                _t("ge_new_graph_confirm"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self._graph = Graph(name=_t("ge_new_graph_name"))
        self._current_filepath = None
        self._graph_name_edit.setText(_t("ge_new_graph_name"))
        self._refresh_all()
        self._set_status(_t("ge_new_graph_created"))

    def _open_graph(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            _t("ge_open"),
            str(GRAPHS_DIR),
            "Graph JSON (*.json);;All Files (*)",
        )
        if path:
            try:
                self._graph = Graph.load_json(path)
                self._current_filepath = path
                self._graph_name_edit.setText(self._graph.name)
                idx = self._dir_combo.findText(self._graph.direction)
                if idx >= 0:
                    self._dir_combo.setCurrentIndex(idx)
                self._refresh_all()
                self._set_status(_t("ge_opened", name=os.path.basename(path)))
            except Exception as ex:
                QMessageBox.critical(self, _t("error"), _t("ge_error_open", err=ex))

    def _save_graph(self):
        if self._current_filepath:
            self._do_save(self._current_filepath)
        else:
            self._save_graph_as()

    def _save_graph_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            _t("ge_save_as"),
            str(Path(GRAPHS_DIR) / f"{self._graph.name}.json"),
            "Graph JSON (*.json);;All Files (*)",
        )
        if path:
            self._do_save(path)

    def _do_save(self, path: str):
        try:
            self._graph.save_json(path)
            self._current_filepath = path
            self._set_status(_t("ge_saved", name=os.path.basename(path)))
        except Exception as ex:
            QMessageBox.critical(self, _t("error"), _t("ge_error_save", err=ex))

    def _add_node(self):
        dlg = NodeDialog(self, title=_t("ge_dialog_add_node"))
        if dlg.exec():
            node = dlg.get_node()
            self._graph.add_node(node)
            self._refresh_all()
            self._set_status(_t("ge_node_added", label=node.label))

    def _add_edge(self):
        if len(self._graph.nodes) < 2:
            QMessageBox.information(self, _t("ge_add_edge"), _t("ge_need_2_nodes"))
            return
        dlg = EdgeDialog(self, nodes=self._graph.nodes, title=_t("ge_dialog_add_edge"))
        if dlg.exec():
            edge = dlg.get_edge()
            if edge:
                ok = self._graph.add_edge(edge)
                if ok:
                    self._refresh_all()
                    self._set_status(_t("ge_edge_added", src=edge.source_id, tgt=edge.target_id))
                else:
                    QMessageBox.warning(self, _t("error"), _t("ge_error_invalid_edge"))

    def _delete_selected(self):
        node_item = self._nodes_list.currentItem()
        if node_item:
            node_id = node_item.data(Qt.ItemDataRole.UserRole)
            node = self._graph.get_node(node_id)
            if node:
                reply = QMessageBox.question(
                    self,
                    _t("ge_delete_node_title"),
                    _t("ge_delete_node_confirm", label=node.label),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._graph.remove_node(node_id)
                    self._refresh_all()
                    self._set_status(_t("ge_node_deleted", label=node.label))
            return
        edge_item = self._edges_list.currentItem()
        if edge_item:
            edge_id = edge_item.data(Qt.ItemDataRole.UserRole)
            edge = self._graph.get_edge(edge_id)
            if edge:
                self._graph.remove_edge(edge_id)
                self._refresh_all()
                self._set_status(_t("ge_edge_deleted", id=edge.id))

    def _export_mermaid(self):
        code = generate_mermaid(self._graph)
        dlg = QDialog(self)
        dlg.setWindowTitle(_t("ge_dialog_mermaid_title"))
        dlg.setMinimumWidth(540)
        dlg.setStyleSheet(_dialog_ss())
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(14, 14, 14, 14)
        hdr = QLabel(_t("ge_dialog_mermaid_title"))
        hdr.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {_ACCENT_DIM};")
        layout.addWidget(hdr)
        text = QTextEdit(code)
        text.setStyleSheet(
            f"font-family: 'Cascadia Code', Consolas, monospace; font-size: 12px;"
            f" background: rgba(0,0,0,0.5); color: #c4b5fd;"
            f" border: 1px solid {_BORDER}; border-radius: 8px;"
        )
        layout.addWidget(text)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        dlg.exec()

    # ------------------------------------------------------------------
    # Graph algorithms (M4)
    # ------------------------------------------------------------------

    def _run_shortest_path(self):
        """Open dialog to select two nodes, compute shortest path via NetworkX, highlight in JS."""
        if len(self._graph.nodes) < 2:
            QMessageBox.information(self, "Shortest Path", "Need at least 2 nodes.")
            return
        dlg = ShortestPathDialog(self, nodes=self._graph.nodes)
        if dlg.exec():
            src_id, tgt_id = dlg.get_selection()
            if src_id == tgt_id:
                QMessageBox.information(self, "Shortest Path", "Source and target must be different.")
                return
            from laitoxx.shared.graph.algorithms import get_shortest_path

            path = get_shortest_path(self._graph, src_id, tgt_id)
            if not path:
                QMessageBox.information(self, "Shortest Path", "No path found between selected nodes.")
                return
            self._mermaid_view.highlight_path(path)
            src = self._graph.get_node(src_id)
            tgt = self._graph.get_node(tgt_id)
            s_lbl = src.label if src else src_id
            t_lbl = tgt.label if tgt else tgt_id
            self._set_status(f"Path: {s_lbl} \u2192 {t_lbl} ({len(path)} nodes)")

    def _run_centrality(self):
        """Open dialog to select metric, compute centrality via NetworkX, resize nodes in JS."""
        if not self._graph.nodes:
            QMessageBox.information(self, "Centrality", "Graph has no nodes.")
            return
        dlg = CentralityDialog(self)
        if dlg.exec():
            metric = dlg.get_metric()
            from laitoxx.shared.graph.algorithms import calculate_centralities

            scores = calculate_centralities(self._graph, metric)
            if not scores:
                QMessageBox.information(self, "Centrality", "Could not compute centrality.")
                return
            self._mermaid_view.apply_centrality_sizes(scores)
            top = max(scores, key=scores.get)
            top_node = self._graph.get_node(top)
            top_label = top_node.label if top_node else top
            self._set_status(f"Centrality ({metric}): top = {top_label} ({scores[top]:.3f})")

    # ------------------------------------------------------------------
    # Timeline filter (M5)
    # ------------------------------------------------------------------

    def _on_timeline_changed(self, start_iso: str, end_iso: str):
        """Apply the temporal filter to the active native canvas."""
        self._mermaid_view.filter_by_time_range(start_iso, end_iso)

    def _on_direction_change(self, direction: str):
        self._graph.direction = direction
        self._refresh_view()

    def _on_name_changed(self, name: str):
        self._graph.name = name

    # ------------------------------------------------------------------
    # Context menus
    # ------------------------------------------------------------------
