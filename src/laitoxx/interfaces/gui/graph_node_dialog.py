"""Focused graph editor widgets and dialogs."""
# ruff: noqa: F405

from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from laitoxx.shared.graph.model import (
    NODE_SHAPES,
    NODE_TYPE_DEFAULTS,
    NODE_TYPES,
    Node,
)

from .graph_style_editor import MetadataTable, StyleEditor
from .graph_ui_style import *  # noqa: F403


def _dialog_ss() -> str:
    """Build dialog stylesheet from current module-level tokens (updated at theme change)."""
    return f"""
    QDialog, QWidget {{
        background: {_BG_DEEP};
        color: {_TEXT_PRI};
        font-family: 'Segoe UI', Arial, sans-serif;
    }}
    QLabel {{ color: {_TEXT_PRI}; font-size: 12px; }}
    QLineEdit, QTextEdit, QComboBox {{
        background: rgba(255,255,255,0.04);
        border: 1px solid {_BORDER};
        border-radius: 7px;
        color: {_TEXT_PRI};
        padding: 4px 8px;
        font-size: 12px;
    }}
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
        border-color: {_BORDER_FOCUS};
    }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background: {_BG_DEEP};
        color: {_TEXT_PRI};
        selection-background-color: {_BORDER};
        border: 1px solid {_BORDER};
        border-radius: 6px;
    }}
    QTableWidget {{
        background: rgba(255,255,255,0.03);
        color: {_TEXT_PRI};
        gridline-color: rgba(255,255,255,0.07);
        border: 1px solid {_BORDER};
        border-radius: 7px;
    }}
    QHeaderView::section {{
        background: {_BORDER};
        color: {_ACCENT};
        border: none;
        padding: 4px;
        font-size: 11px;
        font-weight: 600;
    }}
    QScrollBar:vertical {{
        background: transparent; width: 8px;
    }}
    QScrollBar::handle:vertical {{
        background: {_BORDER};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {_BORDER_FOCUS};
    }}
    QDialogButtonBox QPushButton {{
        background: {_ACCENT_DIM};
        border: 1px solid {_ACCENT_DIM};
        border-radius: 7px;
        color: white;
        font-weight: 600;
        padding: 5px 18px;
        font-size: 12px;
    }}
    QDialogButtonBox QPushButton:hover {{
        background: {_ACCENT};
        border-color: {_ACCENT};
    }}
"""


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;")
    return lbl


# ===========================================================================
# Node Dialog
# ===========================================================================


class NodeDialog(QDialog):
    def __init__(self, parent=None, node: Node | None = None, title="Add Node"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self.setStyleSheet(_dialog_ss())
        self._node = node

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        layout = QVBoxLayout(inner)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header
        hdr = QLabel(title)
        hdr.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {_ACCENT};"
            f" padding-bottom: 6px; border-bottom: 1px solid {_BORDER};"
        )
        layout.addWidget(hdr)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.label_edit = QLineEdit(node.label if node else "")
        self.label_edit.setPlaceholderText(_t("ge_label_placeholder"))
        form.addRow(_field_label(_t("ge_field_label")), self.label_edit)

        self.type_combo = QComboBox()
        _node_type_keys = [
            "ge_node_type_person",
            "ge_node_type_email",
            "ge_node_type_phone",
            "ge_node_type_website",
            "ge_node_type_company",
            "ge_node_type_ip",
            "ge_node_type_address",
            "ge_node_type_document",
            "ge_node_type_custom",
        ]
        for key, internal in zip(_node_type_keys, NODE_TYPES, strict=False):
            self.type_combo.addItem(_t(key), internal)
        if node:
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == node.node_type:
                    self.type_combo.setCurrentIndex(i)
                    break
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow(_field_label(_t("ge_field_type")), self.type_combo)

        self.shape_combo = QComboBox()
        _shape_keys = {
            "rect": "ge_shape_rect",
            "round": "ge_shape_round",
            "circle": "ge_shape_circle",
            "diamond": "ge_shape_diamond",
            "hexagon": "ge_shape_hexagon",
            "flag": "ge_shape_flag",
            "trapez": "ge_shape_trapez",
        }
        for _disp, (shape_id, _o, _c) in NODE_SHAPES.items():
            self.shape_combo.addItem(_t(_shape_keys.get(shape_id, shape_id)), shape_id)
        current_shape = node.mermaid_shape if node else "rect"
        self._select_shape(current_shape)
        form.addRow(_field_label(_t("ge_field_shape")), self.shape_combo)

        self.desc_edit = QTextEdit(node.description if node else "")
        self.desc_edit.setPlaceholderText(_t("ge_desc_placeholder"))
        self.desc_edit.setMaximumHeight(60)
        form.addRow(_field_label(_t("ge_field_description")), self.desc_edit)

        layout.addLayout(form)

        # Style editor section
        se_hdr = QLabel(_t("ge_visual_style"))
        se_hdr.setStyleSheet(
            f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;"
            f" margin-top: 4px; padding-top: 8px; border-top: 1px solid {_BORDER};"
        )
        layout.addWidget(se_hdr)
        self.style_editor = StyleEditor(is_edge=False)
        if node and node.mermaid_style:
            self.style_editor.load_style(node.mermaid_style)
        layout.addWidget(self.style_editor)

        # Metadata section
        meta_hdr = QLabel(_t("ge_metadata"))
        meta_hdr.setStyleSheet(
            f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;"
            f" margin-top: 4px; padding-top: 8px; border-top: 1px solid {_BORDER};"
        )
        layout.addWidget(meta_hdr)
        self.meta_table = MetadataTable()
        if node and node.metadata:
            self.meta_table.set_metadata(node.metadata)
        layout.addWidget(self.meta_table)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _select_shape(self, shape_id: str):
        for i in range(self.shape_combo.count()):
            if self.shape_combo.itemData(i) == shape_id:
                self.shape_combo.setCurrentIndex(i)
                return
        self.shape_combo.setCurrentIndex(0)

    def _get_shape_value(self) -> str:
        return self.shape_combo.currentData() or "rect"

    def _on_type_changed(self, _index):
        internal = self.type_combo.currentData() or self.type_combo.currentText()
        defaults = NODE_TYPE_DEFAULTS.get(internal, {})
        if defaults:
            self._select_shape(defaults.get("shape", "rect"))
            self.style_editor.load_style(defaults.get("style", ""))

    def get_node(self) -> Node:
        style = self.style_editor.build_style()
        node_type = self.type_combo.currentData() or self.type_combo.currentText()
        if self._node:
            n = self._node
            n.label = self.label_edit.text().strip() or "Node"
            n.node_type = node_type
            n.description = self.desc_edit.toPlainText()
            n.mermaid_shape = self._get_shape_value()
            n.mermaid_style = style
            n.metadata = self.meta_table.get_metadata()
            return n
        return Node(
            label=self.label_edit.text().strip() or "Node",
            node_type=node_type,
            description=self.desc_edit.toPlainText(),
            mermaid_shape=self._get_shape_value(),
            mermaid_style=style,
            metadata=self.meta_table.get_metadata(),
        )
