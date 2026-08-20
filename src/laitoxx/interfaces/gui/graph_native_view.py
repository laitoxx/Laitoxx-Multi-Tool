"""Native bounded Qt graph view."""

# ruff: noqa: E701, E702

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QLabel,
)

from laitoxx.interfaces.gui.design_system import resolved_theme
from laitoxx.shared.graph.model import Graph

from .graph_native_edge import _NativeEdgeItem
from .graph_native_interaction import NativeViewInteractionMixin
from .graph_native_layout import NativeViewLayoutMixin
from .graph_native_node import _NativeNodeItem
from .graph_native_render import NativeViewRenderMixin


class NativeGraphView(
    NativeViewRenderMixin,
    NativeViewLayoutMixin,
    NativeViewInteractionMixin,
    QGraphicsView,
):
    """Bounded, target-centred native graph canvas used by GraphEditorWindow."""

    node_context_requested = pyqtSignal(str, int, int)
    background_context_requested = pyqtSignal(int, int)
    node_selected = pyqtSignal(str)
    edge_selected = pyqtSignal(str)
    context_menu_requested = pyqtSignal(str, str, int, int)
    MAX_RENDER_NODES = 260
    MAX_RENDER_EDGES = 520

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._scene.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.BspTreeIndex)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self._theme = resolved_theme({})
        self._graph = Graph()
        self._node_items: dict[str, _NativeNodeItem] = {}
        self._edge_items: dict[str, _NativeEdgeItem] = {}
        self._layout_mode = "hierarchy"
        self._query = ""
        self._type = ""
        self._type_filter_mode = "include"
        self.show_labels = True
        self._focus_pending = False
        self._root_id = ""
        self._emphasized_node = ""
        self._backbone_edge_ids: set[str] = set()
        self._layout_communities: list[set[str]] = []
        self._secondary_edges_requested = False
        self._show_secondary_edges = True
        self._hover_text = ""
        self._hover_card = QLabel(self.viewport())
        self._hover_card.setObjectName("GraphHoverCard")
        self._hover_card.setTextFormat(Qt.TextFormat.PlainText)
        self._hover_card.setWordWrap(True)
        self._hover_card.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._hover_card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._hover_card.hide()
        self._hover_show_timer = QTimer(self)
        self._hover_show_timer.setSingleShot(True)
        self._hover_show_timer.timeout.connect(self._display_hover_card)
        self._hover_hide_timer = QTimer(self)
        self._hover_hide_timer.setSingleShot(True)
        self._hover_hide_timer.timeout.connect(self._hover_card.hide)
        self.apply_theme(self._theme)
