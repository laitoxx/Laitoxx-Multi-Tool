import json
import logging
import re
import threading

from PyQt6.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from PyQt6.QtWebEngineCore import QWebEngineSettings
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEngineView = None
    QWebEngineSettings = None
    logging.warning("PyQt6-WebEngine not installed. Maps will not be rendered.")

from laitoxx.core.localization.i18n import translator
from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme
from laitoxx.interfaces.gui.worker import Worker, stop_and_detach_thread

__all__ = [
    "QCheckBox",
    "QComboBox",
    "QDialog",
    "QFileDialog",
    "QHBoxLayout",
    "QLabel",
    "QLineEdit",
    "QMessageBox",
    "QProgressBar",
    "QPushButton",
    "QSplitter",
    "QTabWidget",
    "QTableWidget",
    "QTableWidgetItem",
    "QTextEdit",
    "QThread",
    "QTimer",
    "QUrl",
    "QVBoxLayout",
    "QWidget",
    "Qt",
    "Worker",
    "build_workspace_qss",
    "json",
    "logging",
    "pyqtSignal",
    "re",
    "resolved_theme",
    "stop_and_detach_thread",
    "threading",
    "translator",
]
__all__ += ["QWebEngineSettings", "QWebEngineView"]
