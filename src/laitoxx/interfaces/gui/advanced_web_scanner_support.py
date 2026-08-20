from __future__ import annotations

import json
import math
from html import escape

from PyQt6.QtCore import QPointF, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.features.osint.advanced_web_scanner import AdvancedWebScanner, ScanOptions
from laitoxx.features.osint.advanced_web_scanner.catalog import PROVIDERS
from laitoxx.features.osint.advanced_web_scanner.configuration import configuration_errors, load_configuration
from laitoxx.features.osint.advanced_web_scanner.graph_projection import project_for_graph
from laitoxx.features.osint.advanced_web_scanner.models import Entity, Relation
from laitoxx.features.osint.advanced_web_scanner.quota import ledger
from laitoxx.interfaces.gui.advanced_web_scanner_settings import AdvancedWebScannerSettingsDialog
from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme
from laitoxx.interfaces.gui.graph_editor import GraphEditorWindow
from laitoxx.interfaces.gui.worker import stop_and_detach_thread
from laitoxx.shared.graph.model import Edge, Graph, Node

__all__ = [
    "AdvancedWebScanner",
    "AdvancedWebScannerSettingsDialog",
    "Edge",
    "Entity",
    "Graph",
    "GraphEditorWindow",
    "Node",
    "PROVIDERS",
    "QBrush",
    "QCheckBox",
    "QColor",
    "QComboBox",
    "QDialog",
    "QFileDialog",
    "QFrame",
    "QGraphicsPathItem",
    "QGraphicsRectItem",
    "QGraphicsScene",
    "QGraphicsSimpleTextItem",
    "QGraphicsView",
    "QHBoxLayout",
    "QHeaderView",
    "QLabel",
    "QLineEdit",
    "QMessageBox",
    "QPainterPath",
    "QPen",
    "QPointF",
    "QProgressBar",
    "QPushButton",
    "QSpinBox",
    "QSplitter",
    "QTabWidget",
    "QTableWidget",
    "QTableWidgetItem",
    "QTextEdit",
    "QThread",
    "QTreeWidget",
    "QTreeWidgetItem",
    "QVBoxLayout",
    "QWidget",
    "Qt",
    "Relation",
    "ScanOptions",
    "build_workspace_qss",
    "configuration_errors",
    "escape",
    "json",
    "ledger",
    "load_configuration",
    "math",
    "project_for_graph",
    "pyqtSignal",
    "resolved_theme",
    "stop_and_detach_thread",
    "translator",
]
