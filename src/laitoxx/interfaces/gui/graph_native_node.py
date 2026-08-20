"""Native Qt graphics item for a graph node."""

# ruff: noqa: E701, E702

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QRadialGradient
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
)

from laitoxx.shared.graph.model import Node

from .graph_native_style import _TYPE_GLYPHS, paint_glyph

if TYPE_CHECKING:
    from .graph_native_view import NativeGraphView


class _NativeNodeItem(QGraphicsObject):
    """A compact vector node with a literal tooltip, never HTML."""

    def __init__(self, node: Node, view: NativeGraphView, position: QPointF):
        super().__init__()
        self.node = node
        self.view = view
        self.radius = 25.0
        self.setPos(position)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(2)
        self._hovered = False

    def boundingRect(self) -> QRectF:
        if self.view._layout_mode == "hierarchy":
            return QRectF(-102, -34, 204, 68)
        return QRectF(-82, -52, 164, 116)

    def _shape_name(self) -> str:
        value = str(self.node.mermaid_shape or "rect")
        return {
            "[]": "rect",
            "[": "rect",
            "()": "round",
            "(": "round",
            "(())": "circle",
            "{}": "diamond",
            "{{}}": "hexagon",
            ">]": "flag",
            "[/ /]": "trapez",
        }.get(value, value if value in {"rect", "round", "circle", "diamond", "hexagon", "flag", "trapez"} else "round")

    def _shape_path(self, radius: float) -> QPainterPath:
        shape = self._shape_name()
        path = QPainterPath()
        if shape == "circle":
            path.addEllipse(QPointF(0, 0), radius, radius)
        elif shape == "rect":
            path.addRect(QRectF(-radius, -radius * 0.78, radius * 2, radius * 1.56))
        elif shape == "round":
            path.addRoundedRect(
                QRectF(-radius, -radius * 0.80, radius * 2, radius * 1.60), radius * 0.36, radius * 0.36
            )
        elif shape == "diamond":
            path.moveTo(0, -radius)
            path.lineTo(radius, 0)
            path.lineTo(0, radius)
            path.lineTo(-radius, 0)
            path.closeSubpath()
        elif shape == "hexagon":
            path.moveTo(-radius * 0.52, -radius * 0.88)
            path.lineTo(radius * 0.52, -radius * 0.88)
            path.lineTo(radius, 0)
            path.lineTo(radius * 0.52, radius * 0.88)
            path.lineTo(-radius * 0.52, radius * 0.88)
            path.lineTo(-radius, 0)
            path.closeSubpath()
        elif shape == "flag":
            path.moveTo(-radius, -radius * 0.82)
            path.lineTo(radius * 0.72, -radius * 0.82)
            path.lineTo(radius, 0)
            path.lineTo(radius * 0.72, radius * 0.82)
            path.lineTo(-radius, radius * 0.82)
            path.closeSubpath()
        else:  # trapezoid
            path.moveTo(-radius * 0.72, -radius * 0.82)
            path.lineTo(radius * 0.72, -radius * 0.82)
            path.lineTo(radius, radius * 0.82)
            path.lineTo(-radius, radius * 0.82)
            path.closeSubpath()
        return path

    def paint(self, painter: QPainter, option, widget=None):
        color = self.view.node_color(self.node.node_type)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = self.isSelected()
        is_target = bool(self.node.metadata.get("is_target"))
        accent = self.view.theme_color("accent_color", "#ffffff") if selected or is_target else color.lighter(120)
        if self.view._layout_mode == "hierarchy":
            surface = self.view.theme_color("surface_raised_color", "#171923")
            painter.setPen(QPen(accent, 2.7 if selected or is_target else 1.4))
            painter.setBrush(surface)
            painter.drawRoundedRect(QRectF(-99, -29, 198, 58), 10, 10)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(-99, -29, 6, 58), 3, 3)
            painter.save()
            painter.translate(-69, 0)
            painter.setPen(QPen(color.lighter(145), 1.2))
            icon_fill = QColor(color)
            icon_fill.setAlpha(55)
            painter.setBrush(icon_fill)
            painter.drawPath(self._shape_path(18))
            painter.setPen(QPen(color.lighter(155), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            paint_glyph(painter, _TYPE_GLYPHS.get(self.node.node_type, "dot"))
            painter.restore()

            label = self.node.label.replace("\n", " ")
            if len(label) > 25:
                label = label[:24] + "…"
            painter.setPen(self.view.theme_color("text_primary_color", "#e5e7eb"))
            font = QFont(self.view._theme.get("font_family", "Segoe UI"), 9)
            font.setBold(selected)
            painter.setFont(font)
            painter.drawText(
                QRectF(-43, -21, 134, 24), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label
            )
            painter.setPen(self.view.theme_color("text_secondary_color", "#9ca3af"))
            painter.setFont(QFont(self.view._theme.get("font_family", "Segoe UI"), 7))
            painter.drawText(
                QRectF(-43, 3, 134, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.node.node_type
            )
        else:
            radius = self.radius
            glow = QColor(accent)
            glow.setAlpha(52 if selected or is_target or self._hovered else 22)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawPath(self._shape_path(radius + (9 if is_target else 6)))
            gradient = QRadialGradient(QPointF(-radius * 0.28, -radius * 0.32), radius * 1.45)
            gradient.setColorAt(0.0, color.lighter(155))
            gradient.setColorAt(0.58, color)
            gradient.setColorAt(1.0, color.darker(145))
            border = QPen(accent, 3.0 if selected or is_target else 1.6)
            border.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(border)
            painter.setBrush(QBrush(gradient))
            painter.drawPath(self._shape_path(radius))
            inner = QColor("#ffffff")
            inner.setAlpha(42)
            painter.setPen(QPen(inner, 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(self._shape_path(max(5, radius - 5)))
            painter.setPen(
                QPen(QColor("#f8fafc"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            )
            paint_glyph(painter, _TYPE_GLYPHS.get(self.node.node_type, "dot"))
            if self.view.show_labels or selected or self.view.transform().m11() >= 0.72:
                label = self.node.label.replace("\n", " ")
                if len(label) > 22:
                    label = label[:21] + "…"
                font = QFont(self.view._theme.get("font_family", "Segoe UI"), 8)
                font.setBold(selected)
                painter.setFont(font)
                width = min(152.0, max(48.0, painter.fontMetrics().horizontalAdvance(label) + 18.0))
                label_rect = QRectF(-width / 2, radius + 8, width, 23)
                surface = self.view.theme_color("surface_raised_color", "#171923")
                surface.setAlpha(232)
                outline = QColor(color)
                outline.setAlpha(105)
                painter.setPen(QPen(outline, 1.0))
                painter.setBrush(surface)
                painter.drawRoundedRect(label_rect, 7, 7)
                painter.setPen(self.view.theme_color("text_primary_color", "#e5e7eb"))
                painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.setZValue(6)
        self.update()
        lines = [self.node.label, self.node.node_type]
        if self.node.description:
            lines.append(self.node.description[:240])
        lines.extend(f"{key}: {value}" for key, value in list(self.node.metadata.items())[:6])
        self.view.show_hover_card(lines)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.setZValue(2)
        self.update()
        self.view.hide_hover_card()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.view.node_context_requested.emit(self.node.id, int(event.screenPos().x()), int(event.screenPos().y()))
            event.accept()
            return
        super().mousePressEvent(event)
        self.view.emphasize_neighborhood(self.node.id)
        self.view.node_selected.emit(self.node.id)

    def mouseDoubleClickEvent(self, event):
        self.view.focus_node(self.node.id)
        event.accept()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.view._edge_items.values():
                if edge.source is self or edge.target is self:
                    edge.update_path()
            # Translucent antialiased paths can leave their old raster footprint
            # on Windows unless the complete native viewport is invalidated.
            self.view.viewport().update()
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.view._scene.setSceneRect(self.view._scene.itemsBoundingRect().adjusted(-90, -90, 90, 90))
        self.view.viewport().update()
