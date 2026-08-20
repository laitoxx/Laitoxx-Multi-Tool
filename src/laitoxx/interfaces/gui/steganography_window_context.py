import os
import traceback

from PyQt6.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.features.utilities.steganography.api import create_config
from laitoxx.features.utilities.steganography.method_catalog import AUTO_METHOD_ID, METHOD_BY_ID, method_choices
from laitoxx.features.utilities.steganography.models import CHANNEL_PRESETS
from laitoxx.features.utilities.steganography.service import StegOptions
from laitoxx.features.utilities.steganography.service import service as steganography_service
from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme
from laitoxx.interfaces.gui.worker_io import stop_and_detach_thread


class ExtractionScanWorker(QThread):
    completed = pyqtSignal(dict)
    failed = pyqtSignal(str)
    progress = pyqtSignal(int, int, str)

    def __init__(self, image_path: str, password: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.password = password

    def run(self):
        try:
            self.completed.emit(
                steganography_service.extract_all(
                    self.image_path,
                    self.password,
                    lambda current, total, label: self.progress.emit(current, total, label),
                )
            )
        except Exception as exc:
            self.failed.emit(str(exc))


def apply_shadow(widget):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(22)
    shadow.setXOffset(0)
    shadow.setYOffset(4)
    shadow.setColor(QColor(0, 0, 0, 55))
    widget.setGraphicsEffect(shadow)


class ImageDropLabel(QLabel):
    """Preview surface that also accepts local image files."""

    imageDropped = pyqtSignal(str)
    SUPPORTED_EXTENSIONS = {".png", ".bmp", ".jpg", ".jpeg"}

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if any(os.path.splitext(url.toLocalFile())[1].lower() in self.SUPPORTED_EXTENSIONS for url in urls):
            event.acceptProposedAction()
            self.setProperty("dragActive", True)
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event):
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.splitext(path)[1].lower() in self.SUPPORTED_EXTENSIONS:
                self.imageDropped.emit(path)
                event.acceptProposedAction()
                return


class ModernCard(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("ModernCard")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 12, 14, 14)
        self.layout.setSpacing(9)

        # Title
        self.title_lbl = QLabel(title)
        font = self.title_lbl.font()
        font.setBold(True)
        font.setPointSize(11)
        self.title_lbl.setFont(font)
        self.title_lbl.setObjectName("PanelTitle")

        # Title separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setObjectName("CardDivider")

        self.layout.addWidget(self.title_lbl)
        self.layout.addWidget(line)
        apply_shadow(self)


__all__ = [
    "AUTO_METHOD_ID",
    "CHANNEL_PRESETS",
    "ExtractionScanWorker",
    "ImageDropLabel",
    "METHOD_BY_ID",
    "ModernCard",
    "QCheckBox",
    "QColor",
    "QComboBox",
    "QDialog",
    "QFileDialog",
    "QFrame",
    "QGraphicsDropShadowEffect",
    "QGridLayout",
    "QHBoxLayout",
    "QLabel",
    "QLineEdit",
    "QMessageBox",
    "QPixmap",
    "QProgressBar",
    "QPushButton",
    "QScrollArea",
    "QSize",
    "QSpinBox",
    "QSplitter",
    "QTabWidget",
    "QTextEdit",
    "QThread",
    "QVBoxLayout",
    "QWidget",
    "Qt",
    "StegOptions",
    "apply_shadow",
    "build_workspace_qss",
    "create_config",
    "method_choices",
    "os",
    "pyqtSignal",
    "resolved_theme",
    "steganography_service",
    "stop_and_detach_thread",
    "traceback",
    "translator",
]
