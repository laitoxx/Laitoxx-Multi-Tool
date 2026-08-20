"""Focused GraphEditorWindow responsibility mixin."""
# ruff: noqa: F405

from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from laitoxx.interfaces.gui.graph_actions import _vsep
from laitoxx.interfaces.gui.graph_controls import GlassPanel, GradientButton, OpacitySlider, SectionLabel
from laitoxx.shared.graph.relationship_suggestions import apply_suggestions, suggest_relationships

from .graph_ui_style import *  # noqa: F403


class GraphEditorLayoutMixin:
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 8)
        root.setSpacing(6)

        self._author_toolbar = QWidget()
        self._author_toolbar.setObjectName("graphAuthorToolbar")
        self._author_toolbar.setLayout(self._build_toolbar())
        root.addWidget(self._author_toolbar)

        # Opacity control bar
        self._opacity_toolbar = QWidget()
        self._opacity_toolbar.setObjectName("graphOpacityToolbar")
        self._opacity_toolbar.setLayout(self._build_opacity_bar())
        root.addWidget(self._opacity_toolbar)

        # Thin accent line
        self._accent_line = QFrame()
        self._accent_line.setFrameShape(QFrame.Shape.HLine)
        self._accent_line.setFixedHeight(1)
        self._accent_line.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 transparent, stop:0.3 {_ACCENT}, stop:0.7 {_ACCENT2}, stop:1 transparent);"
            f" border: none;"
        )
        root.addWidget(self._accent_line)

        # Main area
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter.setHandleWidth(2)
        self._main_splitter.setStyleSheet(f"QSplitter::handle {{ background: {_BORDER}; }}")

        self._left_panel = self._build_left_panel()
        self._center_panel = self._build_center_panel()
        self._right_panel = self._build_right_panel()

        self._main_splitter.addWidget(self._left_panel)
        self._main_splitter.addWidget(self._center_panel)
        self._main_splitter.addWidget(self._right_panel)
        self._main_splitter.setStretchFactor(0, 0)
        self._main_splitter.setStretchFactor(1, 1)
        self._main_splitter.setStretchFactor(2, 0)
        self._main_splitter.setSizes([230, 670, 310])
        self._main_splitter.setChildrenCollapsible(False)
        root.addWidget(self._main_splitter, 1)

        # Status bar
        status_bar = QHBoxLayout()
        self._status = QLabel(_t("ge_status_ready"))
        self._status.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px;")
        self._node_count = QLabel(_t("ge_node_count", n=0))
        self._node_count.setStyleSheet(f"color: {_ACCENT}; font-size: 11px; font-weight: 600;")
        self._edge_count = QLabel(_t("ge_edge_count", n=0))
        self._edge_count.setStyleSheet(f"color: {_ACCENT2}; font-size: 11px; font-weight: 600;")
        status_bar.addWidget(self._status)
        status_bar.addStretch()
        status_bar.addWidget(self._node_count)
        status_bar.addWidget(QLabel("·"))
        status_bar.addWidget(self._edge_count)
        root.addLayout(status_bar)

    def _build_toolbar(self) -> QHBoxLayout:
        tb = QHBoxLayout()
        tb.setSpacing(5)

        def gbtn(text, tip, slot, colors=_BTN_FILE):
            b = GradientButton(text, colors)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            tb.addWidget(b)
            return b

        gbtn(_t("ge_new"), _t("ge_new"), self._new_graph)
        gbtn(_t("ge_open"), _t("ge_open"), self._open_graph)
        gbtn(_t("ge_save"), _t("ge_save"), self._save_graph)
        gbtn(_t("ge_save_as"), _t("ge_save_as"), self._save_graph_as)

        tb.addWidget(_vsep())

        gbtn(_t("ge_add_node"), _t("ge_add_node"), self._add_node, _BTN_EDIT)
        gbtn(_t("ge_add_edge"), _t("ge_add_edge"), self._add_edge, _BTN_EDIT)
        gbtn(_t("ge_delete"), _t("ge_delete"), self._delete_selected, _BTN_DANGER)

        tb.addWidget(_vsep())

        lbl_dir = QLabel(_t("ge_direction_label"))
        lbl_dir.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px;")
        tb.addWidget(lbl_dir)
        self._dir_combo = QComboBox()
        self._dir_combo.addItems(["TD", "LR", "RL", "BT"])
        self._dir_combo.setFixedWidth(58)
        self._dir_combo.currentTextChanged.connect(self._on_direction_change)
        tb.addWidget(self._dir_combo)

        tb.addWidget(_vsep())

        gbtn(_t("ge_export"), _t("ge_export"), self._export_mermaid, _BTN_EXPORT)

        tb.addWidget(_vsep())
        gbtn(
            "\u26d3 Path",
            "Find shortest path between two nodes",
            self._run_shortest_path,
            _BTN_EDIT,
        )
        gbtn(
            "\u25c9 Centrality",
            "Resize nodes by centrality score",
            self._run_centrality,
            _BTN_EDIT,
        )
        gbtn(
            "✦ Relations",
            "Suggest relationships between OSINT entities",
            self._suggest_relationships,
            _BTN_EDIT,
        )

        tb.addStretch()

        lbl_name = QLabel(_t("ge_name_label"))
        lbl_name.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px;")
        tb.addWidget(lbl_name)
        self._graph_name_edit = QLineEdit(_t("ge_new_graph_name"))
        self._graph_name_edit.setPlaceholderText(_t("ge_name_placeholder"))
        self._graph_name_edit.setFixedWidth(170)
        self._graph_name_edit.textChanged.connect(self._on_name_changed)
        tb.addWidget(self._graph_name_edit)

        return tb

    def _suggest_relationships(self):
        suggestions = suggest_relationships(self._graph)
        if not suggestions:
            QMessageBox.information(self, _t("ge_relationships"), _t("ge_no_relationships"))
            return
        lines = []
        for item in suggestions[:20]:
            source = self._graph.get_node(item.source_id)
            target = self._graph.get_node(item.target_id)
            lines.append(
                f"{source.label if source else item.source_id} → "
                f"{target.label if target else item.target_id}: {item.label} ({item.confidence:.0%})"
            )
        message = _t("ge_apply_relationships", count=len(suggestions)) + "\n\n" + "\n".join(lines)
        if QMessageBox.question(self, _t("ge_relationships"), message) == QMessageBox.StandardButton.Yes:
            apply_suggestions(self._graph, suggestions)
            self._refresh_all()

    def _build_opacity_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(12)

        self._opacity_panels = OpacitySlider(_t("ge_panels_opacity"), 0.55)
        self._opacity_panels.value_changed.connect(self._on_panel_opacity)

        bar.addWidget(self._opacity_panels)
        bar.addStretch()
        return bar

    def _build_left_panel(self) -> GlassPanel:
        panel = GlassPanel(self._panel_alpha)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        vsplit = QSplitter(Qt.Orientation.Vertical)
        vsplit.setHandleWidth(2)
        vsplit.setStyleSheet(f"QSplitter::handle {{ background: {_BORDER}; }}")

        # Nodes section
        nodes_w = QWidget()
        nodes_w.setStyleSheet("background: transparent;")
        nlay = QVBoxLayout(nodes_w)
        nlay.setContentsMargins(0, 0, 0, 0)
        nlay.setSpacing(4)
        nlay.addWidget(SectionLabel(_t("ge_section_nodes")))

        self._nodes_list = QListWidget()
        self._nodes_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._nodes_list.customContextMenuRequested.connect(self._node_list_context)
        self._nodes_list.currentItemChanged.connect(self._on_node_selected)
        self._nodes_list.setStyleSheet(self._list_style())
        nlay.addWidget(self._nodes_list)
        vsplit.addWidget(nodes_w)

        # Edges section
        edges_w = QWidget()
        edges_w.setStyleSheet("background: transparent;")
        elay = QVBoxLayout(edges_w)
        elay.setContentsMargins(0, 0, 0, 0)
        elay.setSpacing(4)
        elay.addWidget(SectionLabel(_t("ge_section_edges")))

        self._edges_list = QListWidget()
        self._edges_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._edges_list.customContextMenuRequested.connect(self._edge_list_context)
        self._edges_list.currentItemChanged.connect(self._on_edge_selected)
        self._edges_list.setStyleSheet(self._list_style(accent=_ACCENT2))
        elay.addWidget(self._edges_list)
        vsplit.addWidget(edges_w)

        vsplit.setSizes([320, 200])
        layout.addWidget(vsplit)
        return panel
