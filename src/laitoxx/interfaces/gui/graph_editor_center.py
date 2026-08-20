"""Focused GraphEditorWindow responsibility mixin."""
# ruff: noqa: F405

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from laitoxx.interfaces.gui.graph_analysis_dialogs import TimelineSlider
from laitoxx.interfaces.gui.graph_controls import GlassPanel, SectionLabel
from laitoxx.interfaces.gui.graph_native_view import NativeGraphView
from laitoxx.interfaces.gui.graph_properties import EdgePropertiesPanel, NodePropertiesPanel
from laitoxx.shared.graph.algorithms import find_relevant_connections

from .graph_ui_style import *  # noqa: F403


class GraphEditorCenterMixin:
    def _build_center_panel(self) -> GlassPanel:
        panel = GlassPanel(self._panel_alpha)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        layout.addWidget(SectionLabel(_t("ge_section_preview")))
        self._embedded_actions = self._build_embedded_actions()
        self._embedded_actions.setVisible(False)
        layout.addWidget(self._embedded_actions)
        # Create the canvas before the analysis toolbar: its controls bind to
        # the canvas methods during construction.
        self._mermaid_view = NativeGraphView()
        self._mermaid_view.node_context_requested.connect(self._on_graph_node_context)
        self._mermaid_view.background_context_requested.connect(self._on_graph_background_context)
        self._mermaid_view.node_selected.connect(self._select_node_by_id)
        self._mermaid_view.edge_selected.connect(self._select_edge_by_id)
        self._mermaid_view.context_menu_requested.connect(self._on_graph_context_menu_event)

        self._analysis_bar = self._build_analysis_bar()
        layout.addWidget(self._analysis_bar)
        layout.addWidget(self._mermaid_view, 1)

        # Raw code toggle
        code_hdr = QHBoxLayout()
        code_lbl = QLabel(_t("ge_mermaid_code_label"))
        code_lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 10px; font-weight: 600;")
        code_hdr.addWidget(code_lbl)
        code_hdr.addStretch()
        layout.addLayout(code_hdr)

        self._raw_code = QTextEdit()
        self._raw_code.setReadOnly(True)
        self._raw_code.setMaximumHeight(110)
        self._raw_code.setStyleSheet(
            f"font-family: 'Cascadia Code', Consolas, monospace; font-size: 11px;"
            f" background: rgba(0,0,0,0.45); color: #b8a9d9;"
            f" border: 1px solid {_BORDER}; border-radius: 8px; padding: 6px;"
        )
        layout.addWidget(self._raw_code)

        # Timeline slider (M5)
        self._timeline = TimelineSlider()
        self._timeline.range_changed.connect(self._on_timeline_changed)
        layout.addWidget(self._timeline)

        return panel

    def _build_embedded_actions(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("graphEmbeddedActions")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        def action(text: str, callback, *, primary: bool = False) -> QPushButton:
            button = QPushButton(text)
            button.setProperty("variant", "primary" if primary else "ghost")
            button.clicked.connect(callback)
            layout.addWidget(button)
            return button

        action(_t("ge_save"), self._save_graph, primary=True)
        action(_t("ge_save_as"), self._save_graph_as)
        layout.addStretch()
        action(_t("ge_add_node"), self._add_node)
        action(_t("ge_add_edge"), self._add_edge)
        return bar

    def _build_analysis_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("graphAnalysisBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)
        self._graph_search = QLineEdit()
        self._graph_search.setMinimumWidth(170)
        self._graph_search.setPlaceholderText(_t("ge_search_placeholder"))
        self._graph_search.setClearButtonEnabled(True)
        self._graph_search.returnPressed.connect(self._apply_graph_filter)
        layout.addWidget(self._graph_search, 1)
        self._graph_filter_mode = QComboBox()
        self._graph_filter_mode.setMaximumWidth(155)
        self._graph_filter_mode.addItem(_t("ge_filter_mode_only"), "include")
        self._graph_filter_mode.addItem(_t("ge_filter_mode_except"), "exclude")
        self._graph_filter_mode.currentIndexChanged.connect(self._apply_graph_filter)
        layout.addWidget(self._graph_filter_mode)
        self._graph_type_filter = QComboBox()
        self._graph_type_filter.setMaximumWidth(150)
        self._graph_type_filter.currentIndexChanged.connect(self._apply_graph_filter)
        layout.addWidget(self._graph_type_filter)
        self._graph_layout_mode = QComboBox()
        self._graph_layout_mode.setMaximumWidth(170)
        self._graph_layout_mode.addItem(_t("ge_layout_hierarchy"), "hierarchy")
        self._graph_layout_mode.addItem(_t("ge_layout_network"), "network")
        self._graph_layout_mode.currentIndexChanged.connect(self._apply_layout_mode)
        layout.addWidget(self._graph_layout_mode)
        self._quick_analysis = QComboBox()
        self._quick_analysis.setMaximumWidth(175)
        self._quick_analysis.addItem(_t("ge_quick_analysis"), "")
        self._quick_analysis.addItem(_t("ge_analysis_target_paths"), "target_paths")
        self._quick_analysis.addItem(_t("ge_analysis_hubs"), "hubs")
        self._quick_analysis.addItem(_t("ge_analysis_bridges"), "bridges")
        self._quick_analysis.addItem(_t("ge_analysis_strong"), "strong")
        self._quick_analysis.currentIndexChanged.connect(self._run_quick_analysis)
        layout.addWidget(self._quick_analysis)
        self._secondary_edges_button = QPushButton(_t("ge_all_edges"))
        self._secondary_edges_button.setToolTip(_t("ge_all_edges_tip"))
        self._secondary_edges_button.setCheckable(True)
        self._secondary_edges_button.toggled.connect(self._mermaid_view.set_secondary_edges_visible)
        layout.addWidget(self._secondary_edges_button)
        fit_button = QPushButton(_t("ge_fit_graph"))
        fit_button.clicked.connect(self._mermaid_view.fit_graph)
        layout.addWidget(fit_button)
        zoom_out = QPushButton("-")
        zoom_out.setFixedWidth(30)
        zoom_out.clicked.connect(lambda: self._mermaid_view.zoom_graph(1 / 1.22))
        layout.addWidget(zoom_out)
        zoom_in = QPushButton("+")
        zoom_in.setFixedWidth(30)
        zoom_in.clicked.connect(lambda: self._mermaid_view.zoom_graph(1.22))
        layout.addWidget(zoom_in)
        clear_button = QPushButton(_t("ge_filter_reset"))
        clear_button.clicked.connect(self._reset_graph_filter)
        layout.addWidget(clear_button)
        self._lists_button = QPushButton(_t("ge_toggle_lists"))
        self._lists_button.setCheckable(True)
        self._lists_button.toggled.connect(self._toggle_lists)
        layout.addWidget(self._lists_button)
        self._inspector_button = QPushButton(_t("ge_toggle_inspector"))
        self._inspector_button.setCheckable(True)
        self._inspector_button.toggled.connect(self._toggle_inspector)
        layout.addWidget(self._inspector_button)
        return bar

    def _run_quick_analysis(self, index: int) -> None:
        mode = self._quick_analysis.itemData(index)
        if not mode:
            return
        title = self._quick_analysis.itemText(index)
        insight = find_relevant_connections(self._graph, str(mode), limit=14)
        nodes = [str(value) for value in insight["nodes"]]
        edges = [str(value) for value in insight["edges"]]
        self._quick_analysis.blockSignals(True)
        self._quick_analysis.setCurrentIndex(0)
        self._quick_analysis.blockSignals(False)
        if not nodes:
            QMessageBox.information(self, title, _t("ge_analysis_no_results"))
            return
        self._mermaid_view.emphasize_subgraph(nodes, edges)
        self._set_status(f"{title}: " + _t("ge_analysis_result", nodes=len(nodes), edges=len(edges)))

    def _build_right_panel(self) -> GlassPanel:
        panel = GlassPanel(self._panel_alpha)
        panel.setMinimumWidth(310)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(SectionLabel(_t("ge_section_properties")))

        self._node_props = NodePropertiesPanel()
        self._node_props.node_edit_requested.connect(self._edit_node_by_id)
        layout.addWidget(self._node_props)

        self._edge_props = EdgePropertiesPanel()
        self._edge_props.edge_edit_requested.connect(self._edit_edge_by_id)
        layout.addWidget(self._edge_props)

        layout.addStretch()
        return panel

    # ------------------------------------------------------------------
    # List style helper
    # ------------------------------------------------------------------

    @staticmethod
    def _list_style(accent: str = _ACCENT, txt_pri: str = _TEXT_PRI, bdr: str = _BORDER) -> str:
        return f"""
            QListWidget {{
                background: rgba(0,0,0,0.0);
                border: none;
                color: {txt_pri};
                font-size: 12px;
                outline: none;
            }}
            QListWidget::item {{
                background: rgba(255,255,255,0.04);
                border-radius: 7px;
                padding: 5px 8px;
                margin: 1px 0;
                border: 1px solid transparent;
            }}
            QListWidget::item:hover {{
                background: rgba(255,255,255,0.07);
                border-color: {bdr};
            }}
            QListWidget::item:selected {{
                background: {bdr};
                border: 1px solid {accent};
                color: white;
            }}
        """

    # ------------------------------------------------------------------
    # Opacity handler
    # ------------------------------------------------------------------
