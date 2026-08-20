import json
import os
from datetime import datetime

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.core.settings.theme import load_default_theme
from laitoxx.features.utilities.metadata_viewer.document_identity import extract_document_identity
from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme

from .engine import engine_instance
from .forensics import MetadataForensics
from .sanitizer import MetadataSanitizer


class WorkerThread(QThread):
    finished_signal = pyqtSignal(dict)

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath

    def run(self):
        try:
            data = engine_instance.extract_metadata(self.filepath)
            self.finished_signal.emit(data)
        except Exception as e:
            self.finished_signal.emit({"error": str(e)})


class IdentityWorkerThread(QThread):
    finished_signal = pyqtSignal(dict)

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath

    def run(self):
        try:
            self.finished_signal.emit(extract_document_identity(self.filepath))
        except Exception as exc:
            self.finished_signal.emit({"error": str(exc)})


__all__ = [
    "IdentityWorkerThread",
    "MetadataForensics",
    "MetadataSanitizer",
    "QDialog",
    "QDragEnterEvent",
    "QDropEvent",
    "QFileDialog",
    "QFrame",
    "QGridLayout",
    "QHBoxLayout",
    "QHeaderView",
    "QLabel",
    "QLineEdit",
    "QListWidget",
    "QMessageBox",
    "QPushButton",
    "QScrollArea",
    "QSplitter",
    "QStackedWidget",
    "QTabWidget",
    "QTableWidget",
    "QTableWidgetItem",
    "QTextEdit",
    "QThread",
    "QVBoxLayout",
    "QWidget",
    "Qt",
    "WorkerThread",
    "build_workspace_qss",
    "datetime",
    "engine_instance",
    "extract_document_identity",
    "json",
    "load_default_theme",
    "os",
    "pyqtSignal",
    "resolved_theme",
    "translator",
]
