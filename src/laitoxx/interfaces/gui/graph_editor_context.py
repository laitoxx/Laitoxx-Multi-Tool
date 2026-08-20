"""Focused GraphEditorWindow responsibility mixin."""
# ruff: noqa: F405

from __future__ import annotations

from PyQt6.QtCore import (
    QPoint,
    Qt,
)

from laitoxx.interfaces.gui.graph_actions import _NODE_TYPE_ACTIONS, NodeActionDialog
from laitoxx.interfaces.gui.graph_edge_dialog import EdgeDialog
from laitoxx.interfaces.gui.graph_node_dialog import NodeDialog
from laitoxx.shared.graph.model import (
    Edge,
    Node,
)

from .graph_ui_style import *  # noqa: F403


class GraphEditorContextMixin:
    def _node_list_context(self, pos):
        item = self._nodes_list.itemAt(pos)
        if not item:
            return
        node_id = item.data(Qt.ItemDataRole.UserRole)
        node = self._graph.get_node(node_id)
        if not node:
            return
        self._show_node_context_menu(node, self._nodes_list.mapToGlobal(pos))

    def _show_node_context_menu(self, node: Node, global_pos: QPoint):
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)

        edit_act = menu.addAction(_t("ge_ctx_edit"))
        clone_act = menu.addAction(_t("ge_ctx_clone"))
        menu.addSeparator()
        run_act = menu.addAction(_t("ge_ctx_run_action"))
        copy_act = menu.addAction(_t("ge_ctx_copy_value"))
        menu.addSeparator()
        del_act = menu.addAction(_t("ge_ctx_delete"))

        action = menu.exec(global_pos)
        if action == edit_act:
            self._edit_node_by_id(node.id)
        elif action == clone_act:
            self._clone_node(node.id)
        elif action == run_act:
            self._run_action_on_node(node)
        elif action == copy_act:
            self._copy_node_value(node)
        elif action == del_act:
            self._graph.remove_node(node.id)
            self._refresh_all()

    def _show_graph_context_menu(self, global_pos: QPoint):
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        add_node = menu.addAction(_t("ge_add_node"))
        add_edge = menu.addAction(_t("ge_add_edge"))
        menu.addSeparator()
        export_act = menu.addAction(_t("ge_export"))
        action = menu.exec(global_pos)
        if action == add_node:
            self._add_node()
        elif action == add_edge:
            self._add_edge()
        elif action == export_act:
            self._export_mermaid()

    def _on_graph_node_context(self, node_id: str, x: int, y: int):
        node = self._graph.get_node(node_id)
        if not node:
            return
        global_pos = self._mermaid_view.map_web_to_global(x, y)
        self._show_node_context_menu(node, global_pos)

    def _on_graph_background_context(self, x: int, y: int):
        global_pos = self._mermaid_view.map_web_to_global(x, y)
        self._show_graph_context_menu(global_pos)

    def _on_graph_context_menu_event(self, item_type: str, item_id: str, x: int, y: int):
        global_pos = self._mermaid_view.map_web_to_global(x, y)
        if item_type == "node":
            node = self._graph.get_node(item_id)
            if node:
                self._show_node_context_menu(node, global_pos)
        elif item_type == "edge":
            edge = self._graph.get_edge(item_id)
            if edge:
                self._show_edge_context_menu(edge, global_pos)
        else:
            self._show_graph_context_menu(global_pos)

    def _show_edge_context_menu(self, edge: Edge, global_pos: QPoint):
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        edit_act = menu.addAction(_t("ge_ctx_edit"))
        menu.addSeparator()
        del_act = menu.addAction(_t("ge_ctx_delete"))
        action = menu.exec(global_pos)
        if action == edit_act:
            self._edit_edge_by_id(edge.id)
        elif action == del_act:
            self._graph.remove_edge(edge.id)
            self._refresh_all()

    def _edge_list_context(self, pos):
        item = self._edges_list.itemAt(pos)
        if not item:
            return
        edge_id = item.data(Qt.ItemDataRole.UserRole)
        edge = self._graph.get_edge(edge_id)
        if not edge:
            return
        self._show_edge_context_menu(edge, self._edges_list.mapToGlobal(pos))

    # ------------------------------------------------------------------
    # Edit existing items
    # ------------------------------------------------------------------

    def _edit_node_by_id(self, node_id: str):
        node = self._graph.get_node(node_id)
        if not node:
            return
        dlg = NodeDialog(self, node=node, title=_t("ge_dialog_edit_node", label=node.label))
        if dlg.exec():
            dlg.get_node()
            self._refresh_all()
            self._set_status(_t("ge_node_updated", label=node.label))

    def _edit_edge_by_id(self, edge_id: str):
        edge = self._graph.get_edge(edge_id)
        if not edge:
            return
        dlg = EdgeDialog(
            self,
            edge=edge,
            nodes=self._graph.nodes,
            title=_t("ge_dialog_edit_edge", id=edge.id),
        )
        if dlg.exec():
            dlg.get_edge()
            self._refresh_all()
            self._set_status(_t("ge_edge_updated", id=edge.id))

    def _clone_node(self, node_id: str):
        src = self._graph.get_node(node_id)
        if not src:
            return
        new_node = Node(
            label=src.label + _t("ge_copy_suffix"),
            node_type=src.node_type,
            description=src.description,
            metadata=dict(src.metadata),
            mermaid_shape=src.mermaid_shape,
            mermaid_style=src.mermaid_style,
        )
        self._graph.add_node(new_node)
        self._refresh_all()
        self._set_status(_t("ge_node_cloned", label=new_node.label))

    # ------------------------------------------------------------------
    # Node actions
    # ------------------------------------------------------------------

    def _run_action_on_node(self, node: Node):
        """Open the action dialog for the given node."""
        if not node:
            return
        # Get builtin actions for this node type
        builtin_actions = _NODE_TYPE_ACTIONS.get(node.node_type, [])
        # Always add Database search as universal option
        universal = [
            ("ge_act_db_search", "Database search"),
        ]
        all_builtin = list(builtin_actions)
        for u in universal:
            if u not in all_builtin:
                all_builtin.append(u)

        # Filter lua plugins - only "search" type
        search_plugins = [p for p in self._lua_plugins if p.enabled and p.plugin_type == "search"]

        dlg = NodeActionDialog(
            self,
            node=node,
            builtin_actions=all_builtin,
            lua_plugins=search_plugins,
        )
        if dlg.exec():
            result = dlg.get_result()
            if result:
                action_type, action_data, value = result
                self.run_action_requested.emit(action_type, action_data, value)

    def _copy_node_value(self, node: Node):
        """Copy node's primary value to clipboard."""
        from PyQt6.QtWidgets import QApplication

        if not node:
            return
        desc = node.description.strip()
        # Extract the most useful value
        value = node.label
        if desc:
            lines = [ln.strip() for ln in desc.split("\n") if ln.strip()]
            for line in lines:
                if ": " in line:
                    value = line.split(": ", 1)[1]
                    break
                else:
                    value = line
                    break
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(value)
        self._set_status(_t("ge_value_copied", value=value[:40]))

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _select_node_by_id(self, node_id: str):
        self._nodes_list.blockSignals(True)
        self._edges_list.blockSignals(True)
        try:
            self._edges_list.clearSelection()
            self._edges_list.setCurrentItem(None)
            self._edge_props.clear()
            for i in range(self._nodes_list.count()):
                item = self._nodes_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == node_id:
                    self._nodes_list.setCurrentItem(item)
                    node = self._graph.get_node(node_id)
                    self._node_props.load_node(node)
                    break
        finally:
            self._nodes_list.blockSignals(False)
            self._edges_list.blockSignals(False)

    def _select_edge_by_id(self, edge_id: str):
        self._nodes_list.blockSignals(True)
        self._edges_list.blockSignals(True)
        try:
            self._nodes_list.clearSelection()
            self._nodes_list.setCurrentItem(None)
            self._node_props.clear()
            for i in range(self._edges_list.count()):
                item = self._edges_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == edge_id:
                    self._edges_list.setCurrentItem(item)
                    edge = self._graph.get_edge(edge_id)
                    self._edge_props.load_edge(edge, self._graph)
                    break
        finally:
            self._nodes_list.blockSignals(False)
            self._edges_list.blockSignals(False)
