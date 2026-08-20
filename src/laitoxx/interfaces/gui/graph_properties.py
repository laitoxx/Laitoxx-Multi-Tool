"""Focused graph editor widgets and dialogs."""
# ruff: noqa: F405

from __future__ import annotations

from PyQt6.QtCore import (
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from laitoxx.shared.graph.model import (
    Edge,
    Graph,
    Node,
)

from .graph_controls import GlassPanel, GradientButton
from .graph_ui_style import *  # noqa: F403


class _PropPanel(GlassPanel):
    """Base for Node/Edge properties panels."""

    _edit_requested = None  # override in subclass as pyqtSignal

    def __init__(self, title: str, fields: list[str], parent=None):
        super().__init__(alpha=0.5, parent=parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(f"color: {_ACCENT}; font-size: 12px; font-weight: 700; letter-spacing: 0.5px;")
        hdr.addWidget(self._title_lbl)
        self._btn_edit = GradientButton(_t("ge_prop_edit"), _BTN_EDIT)
        self._btn_edit.setMinimumWidth(90)
        self._btn_edit.setFixedHeight(24)
        self._btn_edit.clicked.connect(self._on_edit)
        hdr.addWidget(self._btn_edit)
        layout.addLayout(hdr)

        self._sep = QFrame()
        self._sep.setFrameShape(QFrame.Shape.HLine)
        self._sep.setStyleSheet(f"color: {_BORDER};")
        layout.addWidget(self._sep)

        self._fields: dict[str, QLabel] = {}
        self._key_labels: list[QLabel] = []
        self._current_id: str | None = None

        for key in fields:
            row = QHBoxLayout()
            row.setSpacing(4)
            k_lbl = QLabel(f"{key}:")
            k_lbl.setFixedWidth(72)
            k_lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px;")
            self._key_labels.append(k_lbl)
            val = QLabel("-")
            val.setWordWrap(True)
            val.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px;")
            self._fields[key] = val
            row.addWidget(k_lbl)
            row.addWidget(val, 1)
            layout.addLayout(row)

        layout.addStretch()

    def apply_theme(self, accent: str, border: str, txt_sec: str, txt_dim: str):
        """Restyle panel labels from theme colours."""
        self._title_lbl.setStyleSheet(f"color: {accent}; font-size: 12px; font-weight: 700; letter-spacing: 0.5px;")
        self._sep.setStyleSheet(f"color: {border};")
        for k_lbl in self._key_labels:
            k_lbl.setStyleSheet(f"color: {txt_dim}; font-size: 11px;")
        for val_lbl in self._fields.values():
            val_lbl.setStyleSheet(f"color: {txt_sec}; font-size: 11px;")

    def _on_edit(self):
        pass

    def _set(self, key: str, value: str):
        if key in self._fields:
            self._fields[key].setText(value or "-")

    def clear(self):
        self._current_id = None
        for lbl in self._fields.values():
            lbl.setText("-")


class NodePropertiesPanel(_PropPanel):
    node_edit_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(
            _t("ge_prop_node"),
            [
                _t("ge_prop_id"),
                _t("ge_prop_label"),
                _t("ge_prop_type"),
                _t("ge_prop_shape"),
                _t("ge_prop_description"),
                _t("ge_prop_meta"),
            ],
            parent,
        )
        self._field_keys = [
            _t("ge_prop_id"),
            _t("ge_prop_label"),
            _t("ge_prop_type"),
            _t("ge_prop_shape"),
            _t("ge_prop_description"),
            _t("ge_prop_meta"),
        ]

    def load_node(self, node: Node | None):
        if not node:
            self.clear()
            return
        self._current_id = node.id
        self._set(_t("ge_prop_id"), node.id)
        self._set(_t("ge_prop_label"), node.label)
        self._set(_t("ge_prop_type"), node.node_type)
        self._set(_t("ge_prop_shape"), node.mermaid_shape)
        self._set(_t("ge_prop_description"), node.description)
        meta = ", ".join(f"{k}={v}" for k, v in node.metadata.items())
        self._set(_t("ge_prop_meta"), meta)

    def _on_edit(self):
        if self._current_id:
            self.node_edit_requested.emit(self._current_id)


class EdgePropertiesPanel(_PropPanel):
    edge_edit_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(
            _t("ge_prop_edge"),
            [
                _t("ge_prop_id"),
                _t("ge_prop_source"),
                _t("ge_prop_target"),
                _t("ge_prop_label"),
                _t("ge_prop_type"),
                _t("ge_prop_line"),
            ],
            parent,
        )

    def load_edge(self, edge: Edge | None, graph: Graph | None = None):
        if not edge:
            self.clear()
            return
        self._current_id = edge.id
        self._set(_t("ge_prop_id"), edge.id)
        src_lbl = tgt_lbl = ""
        if graph:
            sn = graph.get_node(edge.source_id)
            tn = graph.get_node(edge.target_id)
            src_lbl = sn.label if sn else edge.source_id
            tgt_lbl = tn.label if tn else edge.target_id
        self._set(_t("ge_prop_source"), src_lbl)
        self._set(_t("ge_prop_target"), tgt_lbl)
        self._set(_t("ge_prop_label"), edge.label)
        self._set(_t("ge_prop_type"), edge.edge_type)
        self._set(_t("ge_prop_line"), edge.mermaid_line)

    def _on_edit(self):
        if self._current_id:
            self.edge_edit_requested.emit(self._current_id)
