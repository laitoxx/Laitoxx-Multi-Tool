"""Theme-aware CogniPass targeted password candidate generator."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.features.utilities.cognipass import (
    ChildProfile,
    CogniPassCancelled,
    CogniPassProfile,
    CogniPassResult,
    generate_candidates,
)
from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme
from laitoxx.interfaces.gui.external_tool_messages import external_tool_message


def _t(key: str, fallback: str, **kwargs) -> str:
    value = translator.translations.get(translator.language, {}).get(key)
    if value is None:
        value = translator.translations.get("en", {}).get(key, fallback)
    try:
        return str(value).format(**kwargs)
    except (KeyError, ValueError):
        return fallback.format(**kwargs)


class _CogniPassWorker(QThread):
    completed = pyqtSignal(object)
    failed = pyqtSignal(object)
    cancelled = pyqtSignal()

    def __init__(self, profile: CogniPassProfile):
        super().__init__()
        self.profile = profile
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            result = generate_candidates(
                self.profile,
                cancel_check=lambda: self._cancelled,
            )
            self.completed.emit(result)
        except CogniPassCancelled:
            self.cancelled.emit()
        except Exception as error:  # noqa: BLE001 - worker boundary
            self.failed.emit(error)


__all__ = [
    "ChildProfile",
    "CogniPassCancelled",
    "CogniPassProfile",
    "CogniPassResult",
    "Path",
    "QCheckBox",
    "QDesktopServices",
    "QDialog",
    "QFileDialog",
    "QFormLayout",
    "QFrame",
    "QGroupBox",
    "QHBoxLayout",
    "QHeaderView",
    "QLabel",
    "QLineEdit",
    "QMessageBox",
    "QProgressBar",
    "QPushButton",
    "QScrollArea",
    "QSpinBox",
    "QTableWidget",
    "QTableWidgetItem",
    "QThread",
    "QUrl",
    "QVBoxLayout",
    "QWidget",
    "Qt",
    "_CogniPassWorker",
    "_t",
    "build_workspace_qss",
    "external_tool_message",
    "generate_candidates",
    "pyqtSignal",
    "resolved_theme",
    "translator",
]
