"""
graph_editor.py - Modern Graph/Link editor for LAITOXX.
Glassmorphism UI, gradient buttons, real-time opacity slider.
"""

from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.shared.graph.model import (
    Graph,
)

from .graph_editor_center import GraphEditorCenterMixin
from .graph_editor_commands import GraphEditorCommandsMixin
from .graph_editor_context import GraphEditorContextMixin
from .graph_editor_import import GraphEditorImportMixin
from .graph_editor_layout import GraphEditorLayoutMixin
from .graph_editor_selection import GraphEditorSelectionMixin
from .graph_editor_stylesheet import GraphEditorStylesheetMixin
from .graph_editor_theme import GraphEditorThemeMixin


def _t(key: str, **kwargs) -> str:
    return translator.get(key, **kwargs)


# ===========================================================================
# Design tokens
# ===========================================================================

# Accent colors
_ACCENT = "#c084fc"  # purple
_ACCENT2 = "#f472b6"  # pink
_ACCENT_DIM = "#7c3aed"

# Backgrounds
_BG_DEEP = "#0d0d1a"
_BG_PANEL = "rgba(15, 12, 30, {a})"  # panel with variable alpha
_BG_ITEM = "rgba(255, 255, 255, 0.04)"
_BG_ITEM_SEL = "rgba(192, 132, 252, 0.18)"
_BG_ITEM_HOV = "rgba(255, 255, 255, 0.07)"

# Borders
_BORDER = "rgba(192, 132, 252, 0.25)"
_BORDER_FOCUS = "rgba(192, 132, 252, 0.7)"

# Text
_TEXT_PRI = "#f1f0ff"
_TEXT_SEC = "#a99fc0"
_TEXT_DIM = "#6b6580"

# Toolbar gradient button variants
_BTN_FILE = ("rgba(124,58,237,0.55)", "rgba(139,92,246,0.75)", "#7c3aed")
_BTN_EDIT = ("rgba(14,165,233,0.45)", "rgba(56,189,248,0.65)", "#0ea5e9")
_BTN_DANGER = ("rgba(220,38,38,0.45)", "rgba(239,68,68,0.65)", "#dc2626")
_BTN_EXPORT = ("rgba(5,150,105,0.45)", "rgba(16,185,129,0.65)", "#059669")


def _panel_bg(alpha: float) -> str:
    return _BG_PANEL.format(a=alpha)


# ===========================================================================
# Styled button factory
# ===========================================================================


class GraphEditorWindow(
    GraphEditorLayoutMixin,
    GraphEditorCenterMixin,
    GraphEditorThemeMixin,
    GraphEditorStylesheetMixin,
    GraphEditorCommandsMixin,
    GraphEditorContextMixin,
    GraphEditorSelectionMixin,
    GraphEditorImportMixin,
    QDialog,
):
    # Signal emitted when user wants to run an action from graph editor
    # (action_type: str, action_data: object, value: str)
    run_action_requested = pyqtSignal(str, object, str)

    def __init__(
        self,
        parent=None,
        theme_data: dict | None = None,
        lua_plugins: list | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(_t("graph_editor_title"))
        self.setMinimumSize(1140, 720)
        self._graph = Graph(name=_t("ge_new_graph_name"))
        self._current_filepath: str | None = None
        self._theme = theme_data or {}
        self._panel_alpha = 0.55
        self._lua_plugins = lua_plugins or []
        self._embedded_analysis_mode = False
        self._inspector_dialog: QDialog | None = None
        self.setAcceptDrops(True)

        self._build_ui()
        self.update_theme(self._theme)
        self._refresh_all()
        self._install_mermaid_event_filters()

    def set_graph(self, graph: Graph, status: str = "") -> None:
        """Load a prepared graph into the editor without using a modal dialog."""
        self._graph = graph
        self._current_filepath = None
        self._graph_name_edit.setText(graph.name)
        direction_index = self._dir_combo.findText(graph.direction)
        if direction_index >= 0:
            self._dir_combo.setCurrentIndex(direction_index)
        # Embedded scanner investigations open as a ForceAtlas2 cluster map;
        # the standalone editor keeps its layered authoring layout.
        preferred = "network" if self._embedded_analysis_mode else "hierarchy"
        self._graph_layout_mode.blockSignals(True)
        self._graph_layout_mode.setCurrentIndex(max(0, self._graph_layout_mode.findData(preferred)))
        self._graph_layout_mode.blockSignals(False)
        self._mermaid_view.set_layout_mode(preferred, render=False)
        self._refresh_all()
        self._set_status(status or _t("ge_status_ready"))

    def set_embedded_analysis_mode(self, enabled: bool) -> None:
        self._embedded_analysis_mode = enabled
        if enabled:
            self.setMinimumSize(0, 0)
        else:
            self.setMinimumSize(1140, 720)
        self._author_toolbar.setVisible(not enabled)
        self._opacity_toolbar.setVisible(not enabled)
        self._accent_line.setVisible(not enabled)
        self._embedded_actions.setVisible(enabled)
        self._opacity_panels.setVisible(not enabled)
        self._raw_code.setVisible(not enabled)
        self._timeline.setVisible(not enabled)
        self._left_panel.setVisible(not enabled and self._lists_button.isChecked())
        self._right_panel.setVisible(not enabled and self._inspector_button.isChecked())
        if enabled:
            self._main_splitter.setSizes([0, 1200, 0])
        else:
            self._restore_inspector_panel()
            self._left_panel.setVisible(True)
            self._right_panel.setVisible(True)
            self._main_splitter.setSizes([230, 670, 310])

    def _sync_analysis_filters(self):
        selected_type = self._graph_type_filter.currentData()
        self._graph_type_filter.blockSignals(True)
        self._graph_type_filter.clear()
        self._graph_type_filter.addItem(_t("ge_filter_all"), "")
        for node_type in sorted({node.node_type for node in self._graph.nodes}):
            self._graph_type_filter.addItem(node_type, node_type)
        index = self._graph_type_filter.findData(selected_type)
        self._graph_type_filter.setCurrentIndex(max(0, index))
        self._graph_type_filter.blockSignals(False)

    def _apply_graph_filter(self):
        self._mermaid_view.filter_graph(
            self._graph_search.text(),
            self._graph_type_filter.currentData() or "",
            self._graph_filter_mode.currentData() or "include",
        )

    def _reset_graph_filter(self):
        self._graph_search.clear()
        self._graph_filter_mode.setCurrentIndex(0)
        self._graph_type_filter.setCurrentIndex(0)
        self._mermaid_view.reset_graph_filter()

    def _apply_layout_mode(self):
        self._mermaid_view.set_layout_mode(self._graph_layout_mode.currentData() or "hierarchy")

    def _toggle_lists(self, visible: bool):
        self._left_panel.setVisible(visible or not self._embedded_analysis_mode)
        if visible:
            self._main_splitter.setSizes([260, 900, 0])

    def _toggle_inspector(self, visible: bool):
        if self._embedded_analysis_mode:
            self._toggle_floating_inspector(visible)
            return
        self._right_panel.setVisible(visible or not self._embedded_analysis_mode)
        if visible:
            self._main_splitter.setSizes([0, 900, 310])

    def _toggle_floating_inspector(self, visible: bool) -> None:
        if not visible:
            if self._inspector_dialog:
                self._inspector_dialog.hide()
            return
        if self._inspector_dialog is None:
            dialog = QDialog(self.window(), Qt.WindowType.Tool)
            dialog.setWindowTitle(_t("ge_toggle_inspector"))
            dialog.setModal(False)
            dialog.setMinimumWidth(330)
            inspector_layout = QVBoxLayout(dialog)
            inspector_layout.setContentsMargins(8, 8, 8, 8)
            self._inspector_dialog = dialog
            dialog.finished.connect(lambda _result: self._inspector_button.setChecked(False))
        layout = self._inspector_dialog.layout()
        if self._right_panel.parent() is not self._inspector_dialog:
            self._right_panel.setParent(self._inspector_dialog)
            layout.addWidget(self._right_panel)
        self._right_panel.show()
        available = self.screen().availableGeometry()
        self._inspector_dialog.resize(360, min(700, max(460, available.height() - 120)))
        host = self.window().frameGeometry()
        x = min(available.right() - self._inspector_dialog.width(), host.right() + 8)
        y = max(available.top(), host.top() + 56)
        self._inspector_dialog.move(x, y)
        self._inspector_dialog.show()
        self._inspector_dialog.raise_()
        self._inspector_dialog.activateWindow()

    def _restore_inspector_panel(self) -> None:
        if self._inspector_dialog:
            self._inspector_dialog.hide()
        if self._right_panel.parent() is not self._main_splitter:
            self._right_panel.setParent(self._main_splitter)
            self._main_splitter.addWidget(self._right_panel)

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------
