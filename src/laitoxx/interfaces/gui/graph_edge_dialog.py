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
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from laitoxx.shared.graph.model import (
    EDGE_LINE_TYPES,
    EDGE_TYPES,
    Edge,
    Node,
)

from .graph_node_dialog import _dialog_ss, _field_label
from .graph_style_editor import MetadataTable, StyleEditor
from .graph_ui_style import *  # noqa: F403


class EdgeDialog(QDialog):
    def __init__(
        self,
        parent=None,
        edge: Edge | None = None,
        nodes: list[Node] | None = None,
        title="Add Edge",
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self.setStyleSheet(_dialog_ss())
        self._edge = edge
        nodes = nodes or []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        hdr = QLabel(title)
        hdr.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {_ACCENT2};"
            f" padding-bottom: 6px; border-bottom: 1px solid {_BORDER};"
        )
        layout.addWidget(hdr)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.source_combo = QComboBox()
        self.target_combo = QComboBox()
        for n in nodes:
            display = f"{n.label}  [{n.id}]"
            self.source_combo.addItem(display, n.id)
            self.target_combo.addItem(display, n.id)
        if edge:
            self._sel(self.source_combo, edge.source_id)
            self._sel(self.target_combo, edge.target_id)
        form.addRow(_field_label(_t("ge_field_source")), self.source_combo)
        form.addRow(_field_label(_t("ge_field_target")), self.target_combo)

        self.label_edit = QLineEdit(edge.label if edge else "")
        self.label_edit.setPlaceholderText(_t("ge_edge_label_placeholder"))
        form.addRow(_field_label(_t("ge_field_label")), self.label_edit)

        _edge_type_keys = [
            "ge_edge_type_connected",
            "ge_edge_type_worksfor",
            "ge_edge_type_owns",
            "ge_edge_type_relatedto",
            "ge_edge_type_communicates",
            "ge_edge_type_locatedat",
            "ge_edge_type_memberof",
            "ge_edge_type_custom",
        ]
        self.type_combo = QComboBox()
        for key, internal in zip(_edge_type_keys, EDGE_TYPES, strict=False):
            self.type_combo.addItem(_t(key), internal)
        if edge:
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == edge.edge_type:
                    self.type_combo.setCurrentIndex(i)
                    break
        form.addRow(_field_label(_t("ge_field_type")), self.type_combo)

        _line_keys = [
            "ge_line_arrow",
            "ge_line_thick",
            "ge_line_dotted",
            "ge_line_open",
            "ge_line_open_dotted",
            "ge_line_double",
        ]
        self.line_combo = QComboBox()
        for key, val in zip(_line_keys, EDGE_LINE_TYPES.values(), strict=False):
            self.line_combo.addItem(_t(key), val)
        if edge:
            for i in range(self.line_combo.count()):
                if self.line_combo.itemData(i) == edge.mermaid_line:
                    self.line_combo.setCurrentIndex(i)
                    break
        form.addRow(_field_label(_t("ge_field_line")), self.line_combo)

        layout.addLayout(form)

        se_hdr = QLabel(_t("ge_visual_style"))
        se_hdr.setStyleSheet(
            f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;"
            f" margin-top: 4px; padding-top: 8px; border-top: 1px solid {_BORDER};"
        )
        layout.addWidget(se_hdr)
        self.style_editor = StyleEditor(is_edge=True)
        if edge and edge.mermaid_style:
            self.style_editor.load_style(edge.mermaid_style)
        layout.addWidget(self.style_editor)

        meta_hdr = QLabel(_t("ge_metadata"))
        meta_hdr.setStyleSheet(
            f"color: {_TEXT_SEC}; font-size: 11px; font-weight: 600;"
            f" margin-top: 4px; padding-top: 8px; border-top: 1px solid {_BORDER};"
        )
        layout.addWidget(meta_hdr)
        self.meta_table = MetadataTable()
        if edge and edge.metadata:
            self.meta_table.set_metadata(edge.metadata)
        layout.addWidget(self.meta_table)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _sel(self, combo: QComboBox, node_id: str):
        for i in range(combo.count()):
            if combo.itemData(i) == node_id:
                combo.setCurrentIndex(i)
                return

    def get_edge(self) -> Edge | None:
        src = self.source_combo.currentData()
        tgt = self.target_combo.currentData()
        if not src or not tgt:
            return None
        style = self.style_editor.build_style()
        edge_type = self.type_combo.currentData() or self.type_combo.currentText()
        if self._edge:
            e = self._edge
            e.source_id = src
            e.target_id = tgt
            e.label = self.label_edit.text().strip()
            e.edge_type = edge_type
            e.mermaid_line = self.line_combo.currentData()
            e.mermaid_style = style
            e.metadata = self.meta_table.get_metadata()
            return e
        return Edge(
            source_id=src,
            target_id=tgt,
            label=self.label_edit.text().strip(),
            edge_type=edge_type,
            mermaid_line=self.line_combo.currentData(),
            mermaid_style=style,
            metadata=self.meta_table.get_metadata(),
        )
