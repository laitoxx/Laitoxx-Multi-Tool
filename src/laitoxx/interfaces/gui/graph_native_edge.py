"""Native Qt graphics item for a graph edge."""

# ruff: noqa: E701, E702

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QBrush, QLinearGradient, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPathItem,
)

from laitoxx.shared.graph.model import Edge

from .graph_native_node import _NativeNodeItem

if TYPE_CHECKING:
    from .graph_native_view import NativeGraphView


class _NativeEdgeItem(QGraphicsPathItem):
    def __init__(self, edge: Edge, source: _NativeNodeItem, target: _NativeNodeItem, view: NativeGraphView):
        super().__init__()
        self.edge = edge
        self.view = view
        self.source = source
        self.target = target
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)
        self.update_path()

    def update_path(self):
        start, end = self.source.pos(), self.target.pos()
        vector = end - start
        length = max(1.0, math.hypot(vector.x(), vector.y()))
        unit = QPointF(vector.x() / length, vector.y() / length)
        card_edge = self.view._layout_mode == "hierarchy" and abs(vector.x()) >= 20
        if card_edge:
            direction = 1 if vector.x() >= 0 else -1
            begin = QPointF(start.x() + direction * 102, start.y())
            finish = QPointF(end.x() - direction * 104, end.y())
        else:
            begin = start + unit * (self.source.radius + 3)
            finish = end - unit * (self.target.radius + 4)
        path = QPainterPath(begin)
        tangent = unit
        if card_edge:
            middle = (begin.x() + finish.x()) / 2
            path.cubicTo(QPointF(middle, begin.y()), QPointF(middle, finish.y()), finish)
            tangent_vector = finish - QPointF(middle, finish.y())
            tangent_length = max(1.0, math.hypot(tangent_vector.x(), tangent_vector.y()))
            tangent = QPointF(tangent_vector.x() / tangent_length, tangent_vector.y() / tangent_length)
        elif self.view._layout_mode == "network":
            stable = sum((index + 1) * ord(char) for index, char in enumerate(self.edge.id))
            direction = -1.0 if stable % 2 else 1.0
            curve = direction * min(42.0, max(10.0, length * (0.055 + (stable % 5) * 0.008)))
            midpoint = (begin + finish) * 0.5
            normal = QPointF(-unit.y(), unit.x())
            control = midpoint + normal * curve
            path.quadTo(control, finish)
            tangent_vector = finish - control
            tangent_length = max(1.0, math.hypot(tangent_vector.x(), tangent_vector.y()))
            tangent = QPointF(tangent_vector.x() / tangent_length, tangent_vector.y() / tangent_length)
        else:
            path.lineTo(finish)
        arrow = 7.0
        left = QPointF(
            finish.x() - tangent.x() * arrow - tangent.y() * arrow * 0.65,
            finish.y() - tangent.y() * arrow + tangent.x() * arrow * 0.65,
        )
        right = QPointF(
            finish.x() - tangent.x() * arrow + tangent.y() * arrow * 0.65,
            finish.y() - tangent.y() * arrow - tangent.x() * arrow * 0.65,
        )
        path.moveTo(left)
        path.lineTo(finish)
        path.lineTo(right)
        self.setPath(path)
        current = self.edge.metadata.get("current") is not False
        active = self.view._emphasized_node in {"", "analysis"} or self.view._emphasized_node in {
            self.edge.source_id,
            self.edge.target_id,
        }
        edge_color = self.view.theme_color("border_strong_color", "#9ca3af")
        if self.view._layout_mode == "network":
            alpha = 100 if active and not self.view._emphasized_node else 220 if active else 25
            source_color = self.view.node_color(self.source.node.node_type)
            target_color = self.view.node_color(self.target.node.node_type)
            source_color.setAlpha(alpha)
            target_color.setAlpha(alpha)
            gradient = QLinearGradient(begin, finish)
            gradient.setColorAt(0.0, source_color)
            gradient.setColorAt(1.0, target_color)
            brush = QBrush(gradient)
            width = 1.25 if active else 0.7
        else:
            edge_color.setAlpha(190 if active else 32)
            brush = QBrush(edge_color)
            width = 1.5 if active else 0.8
        pen = QPen(brush, width, Qt.PenStyle.SolidLine if current else Qt.PenStyle.DashLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)

    def hoverEnterEvent(self, event):
        lines = [self.edge.label or self.edge.edge_type]
        for key, label in (
            ("total_ton", "TON"),
            ("count", "Transfers"),
            ("estimated_usd", "USD estimate"),
            ("confidence", "Confidence"),
        ):
            value = self.edge.metadata.get(key)
            if value not in (None, "", "None"):
                lines.append(f"{label}: {value}")
        details = self.edge.metadata.get("details")
        if details and details not in {"{}", "None"}:
            lines.append(str(details)[:220])
        self.view.show_hover_card(lines)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.view.hide_hover_card()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.view.context_menu_requested.emit(
                "edge", self.edge.id, int(event.screenPos().x()), int(event.screenPos().y())
            )
            event.accept()
            return
        super().mousePressEvent(event)
        self.view.edge_selected.emit(self.edge.id)
