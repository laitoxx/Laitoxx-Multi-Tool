"""Focused graph editor widgets and dialogs."""
# ruff: noqa: F405

from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
)
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from laitoxx.shared.graph.model import (
    Node,
)

from .graph_node_dialog import _dialog_ss
from .graph_ui_style import *  # noqa: F403


def _vsep() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.VLine)
    sep.setFixedWidth(1)
    sep.setStyleSheet(f"background: {_BORDER}; border: none;")
    return sep


# ===========================================================================
# Main Graph Editor Window
# ===========================================================================

# ===========================================================================
# Node type → suggested built-in actions
# ===========================================================================

_NODE_TYPE_ACTIONS: dict[str, list[tuple[str, str]]] = {
    # node_type → [(action_key, tool_registry_name), ...]
    "Phone": [],
    "Email": [("ge_act_email_osint", "Email OSINT")],
    "IP": [("ge_act_check_ip", "Check IP")],
    "Website": [
        ("ge_act_domain_intelligence", "Domain Intelligence"),
    ],
    "Person": [("ge_act_search_nick", "Search Nick")],
    "Address": [],
    "Company": [("ge_act_domain_intelligence", "Domain Intelligence")],
    "Document": [],
    "Custom": [],
}


# ===========================================================================
# Node Action Dialog
# ===========================================================================


class NodeActionDialog(QDialog):
    """Dialog to choose and run an action on a node's value."""

    def __init__(
        self,
        parent=None,
        node: Node | None = None,
        builtin_actions: list[tuple[str, str]] | None = None,
        lua_plugins: list | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(_t("ge_act_dialog_title"))
        self.setMinimumWidth(440)
        self.setStyleSheet(_dialog_ss())
        self._node = node
        self._selected_action = None  # (type, key)  type='builtin'|'plugin'

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header
        hdr = QLabel(_t("ge_act_dialog_title"))
        hdr.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {_ACCENT};"
            f" padding-bottom: 6px; border-bottom: 1px solid {_BORDER};"
        )
        layout.addWidget(hdr)

        # Node info
        info_frame = QFrame()
        info_frame.setStyleSheet(
            f"background: rgba(192,132,252,0.06); border: 1px solid {_BORDER}; border-radius: 8px; padding: 8px;"
        )
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(4)

        if node:
            type_lbl = QLabel(f"{_t('ge_field_type')}: {node.node_type}")
            type_lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px; border: none;")
            info_layout.addWidget(type_lbl)

            label_lbl = QLabel(f"{_t('ge_field_label')}: {node.label}")
            label_lbl.setStyleSheet(f"color: {_TEXT_PRI}; font-size: 13px; font-weight: 600; border: none;")
            info_layout.addWidget(label_lbl)

            # Show the "value" - use description (which often contains the actual data)
            val = self._extract_value(node)
            self._value = val
            val_lbl = QLabel(f"{_t('ge_act_value')}: {val}")
            val_lbl.setStyleSheet(f"color: {_ACCENT2}; font-size: 12px; border: none;")
            val_lbl.setWordWrap(True)
            info_layout.addWidget(val_lbl)

            # Editable value field
            self._value_edit = QLineEdit(val)
            self._value_edit.setPlaceholderText(_t("ge_act_value_placeholder"))
            info_layout.addWidget(self._value_edit)

        layout.addWidget(info_frame)

        # Actions list
        actions_lbl = QLabel(_t("ge_act_choose"))
        actions_lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600; margin-top: 6px;")
        layout.addWidget(actions_lbl)

        self._actions_list = QListWidget()
        self._actions_list.setStyleSheet(f"""
            QListWidget {{
                background: rgba(255,255,255,0.03);
                border: 1px solid {_BORDER};
                border-radius: 8px;
                color: {_TEXT_PRI};
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 6px 10px;
                border-bottom: 1px solid rgba(255,255,255,0.04);
            }}
            QListWidget::item:selected {{
                background: rgba(192,132,252,0.2);
            }}
            QListWidget::item:hover {{
                background: rgba(255,255,255,0.06);
            }}
        """)
        self._actions_list.setMinimumHeight(140)
        self._actions_list.itemDoubleClicked.connect(self.accept)

        # Populate with builtin actions
        if builtin_actions:
            for trans_key, tool_name in builtin_actions:
                item = QListWidgetItem(f"⚙  {_t(trans_key)}")
                item.setData(Qt.ItemDataRole.UserRole, ("builtin", tool_name))
                item.setToolTip(tool_name)
                self._actions_list.addItem(item)

        # Separator if both
        if builtin_actions and lua_plugins:
            sep = QListWidgetItem(f"── {_t('ge_act_plugins')} ──")
            sep.setFlags(Qt.ItemFlag.NoItemFlags)
            self._actions_list.addItem(sep)

        # Populate with Lua plugins (type = "search")
        if lua_plugins:
            for plugin_meta in lua_plugins:
                item = QListWidgetItem(f"🔌  {plugin_meta.name}")
                item.setData(Qt.ItemDataRole.UserRole, ("plugin", plugin_meta))
                item.setToolTip(plugin_meta.description)
                self._actions_list.addItem(item)

        layout.addWidget(self._actions_list)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Ok).setText(_t("ge_act_run"))
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _extract_value(self, node: Node) -> str:
        """Extract the most useful value from a node for passing to a tool."""
        desc = node.description.strip()
        # If description has meaningful data (not just a source label), use first line
        if desc:
            lines = [ln.strip() for ln in desc.split("\n") if ln.strip()]
            # Skip lines that look like labels ("key: value" → take value)
            for line in lines:
                if ": " in line:
                    return line.split(": ", 1)[1]
                return line
        return node.label

    def get_result(self) -> tuple | None:
        """Returns (action_type, action_data, value) or None."""
        item = self._actions_list.currentItem()
        if not item:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return None
        value = self._value_edit.text().strip() if hasattr(self, "_value_edit") else self._value
        return (data[0], data[1], value)
