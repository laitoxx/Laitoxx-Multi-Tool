"""Theme-aware TONgue public TON investigation workspace."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from PyQt6.QtCore import QPointF, Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.core.settings.app_settings import settings
from laitoxx.features.osint.tongue.graph_adapter import report_to_graph
from laitoxx.features.osint.tongue.provider.toncenter import OperationCancelled
from laitoxx.features.osint.tongue.service import TongueOptions, run_investigation
from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme
from laitoxx.interfaces.gui.graph_editor import GraphEditorWindow


def _t(key: str, fallback: str = "", **kwargs) -> str:
    """Read a translation without eagerly formatting unresolved placeholders."""
    catalogs = translator.translations
    value = catalogs.get(translator.language, {}).get(key)
    if value is None:
        value = catalogs.get("en", {}).get(key)
    if value is None:
        value = fallback or key
    text = str(value)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return str(fallback or text).format(**kwargs)
    return text


class _TongueThread(QThread):
    progress = pyqtSignal(str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, options: TongueOptions):
        super().__init__()
        self.options = options
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            report = run_investigation(
                self.options,
                progress=self.progress.emit,
                cancelled=lambda: self._cancelled,
            )
            if self._cancelled:
                self.cancelled.emit()
            else:
                self.completed.emit(report)
        except OperationCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(str(exc))


class _BrandIcon(QWidget):
    """Small, resolution-independent TON/Telegram status mark."""

    def __init__(self, mode: str = "ton", size: int = 48, parent=None):
        super().__init__(parent)
        self._mode = mode
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_mode(self, mode: str) -> None:
        if mode != self._mode:
            self._mode = mode
            self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height()) - 2
        painter.translate(self.width() / 2, self.height() / 2)
        painter.setPen(Qt.PenStyle.NoPen)
        if self._mode == "telegram":
            painter.setBrush(QColor("#2AABEE"))
            painter.drawEllipse(QPointF(0, 0), side / 2, side / 2)
            plane = QPainterPath()
            plane.moveTo(-side * 0.29, -side * 0.02)
            plane.lineTo(side * 0.31, -side * 0.26)
            plane.lineTo(side * 0.15, side * 0.30)
            plane.lineTo(side * 0.01, side * 0.12)
            plane.lineTo(-side * 0.08, side * 0.22)
            plane.lineTo(-side * 0.10, side * 0.05)
            plane.closeSubpath()
            painter.setBrush(QColor("white"))
            painter.drawPath(plane)
            return
        if self._mode == "warning":
            painter.setBrush(QColor("#F59E0B"))
            warning = QPainterPath()
            warning.moveTo(0, -side * 0.42)
            warning.lineTo(side * 0.43, side * 0.34)
            warning.lineTo(-side * 0.43, side * 0.34)
            warning.closeSubpath()
            painter.drawPath(warning)
            painter.setPen(QPen(QColor("white"), max(2.0, side * 0.06), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(0, -side * 0.16), QPointF(0, side * 0.10))
            painter.drawPoint(QPointF(0, side * 0.22))
            return

        # Official TON symbol geometry, drawn locally so it stays sharp at any DPI.
        painter.setBrush(QColor("#4DB8FF"))
        painter.drawEllipse(QPointF(0, 0), side / 2, side / 2)
        pen = QPen(QColor("white"), max(1.8, side * 0.045))
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        mark = QPainterPath()
        mark.moveTo(-side * 0.27, -side * 0.20)
        mark.lineTo(side * 0.27, -side * 0.20)
        mark.lineTo(0, side * 0.29)
        mark.closeSubpath()
        mark.moveTo(0, -side * 0.20)
        mark.lineTo(0, side * 0.29)
        painter.drawPath(mark)


def _chevron_icon(color: str, upwards: bool) -> QIcon:
    pixmap = QPixmap(18, 14)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    points = (
        (QPointF(4, 9), QPointF(9, 4), QPointF(14, 9)) if upwards else (QPointF(4, 5), QPointF(9, 10), QPointF(14, 5))
    )
    path = QPainterPath(points[0])
    path.lineTo(points[1])
    path.lineTo(points[2])
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


__all__ = [
    "GraphEditorWindow",
    "OperationCancelled",
    "Path",
    "QAbstractSpinBox",
    "QApplication",
    "QCheckBox",
    "QColor",
    "QComboBox",
    "QDesktopServices",
    "QDialog",
    "QFileDialog",
    "QFrame",
    "QGridLayout",
    "QHBoxLayout",
    "QHeaderView",
    "QIcon",
    "QLabel",
    "QLineEdit",
    "QPainter",
    "QPainterPath",
    "QPen",
    "QPixmap",
    "QPointF",
    "QProgressBar",
    "QPushButton",
    "QScrollArea",
    "QSpinBox",
    "QSplitter",
    "QTabWidget",
    "QTableWidget",
    "QTableWidgetItem",
    "QTextEdit",
    "QThread",
    "QToolButton",
    "QUrl",
    "QVBoxLayout",
    "QWidget",
    "Qt",
    "TongueOptions",
    "_BrandIcon",
    "_TongueThread",
    "_chevron_icon",
    "_t",
    "build_workspace_qss",
    "escape",
    "json",
    "pyqtSignal",
    "report_to_graph",
    "resolved_theme",
    "run_investigation",
    "settings",
    "translator",
]
