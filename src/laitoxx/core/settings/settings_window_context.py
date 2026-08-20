"""Settings window - unified dialog with sections:
• General (open website on startup, language)
• Themes  (dropdown from resources/themes, theme editor button)
• Background (dropdown + import file)
• Proxy  (type, host, port, username, password)
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from laitoxx.interfaces.gui.design_system import STYLE_MODES, build_workspace_qss, resolved_theme

from .app_settings import settings
from .background import SUPPORTED_EXT, import_background, list_backgrounds
from .theme import DEFAULT_THEME, list_themes, load_theme, save_theme_to_resources

_SAFE_UI_FONTS = (
    "Segoe UI",
    "Arial",
    "Tahoma",
    "Verdana",
    "Calibri",
    "Noto Sans",
    "Noto Serif",
    "Noto Serif SC",
)

_SAFE_CODE_FONTS = (
    "Cascadia Mono",
    "Cascadia Code",
    "Consolas",
    "Courier New",
    "JetBrains Mono",
    "Fira Code",
)


def _font_choices(current: str, preferred: tuple[str, ...]) -> list[str]:
    """Return stable scalable-font choices without probing legacy faces."""
    return list(dict.fromkeys((current.strip(), *preferred))) if current.strip() else list(preferred)


class _FontPreviewDelegate(QStyledItemDelegate):
    """Render each font name with that font without changing the combo itself."""

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        family = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        if family:
            option.font.setFamily(family)
            option.font.setPointSize(10)


__all__ = [
    "DEFAULT_THEME",
    "QCheckBox",
    "QComboBox",
    "QDialog",
    "QFileDialog",
    "QFormLayout",
    "QHBoxLayout",
    "QLabel",
    "QLineEdit",
    "QListWidget",
    "QListWidgetItem",
    "QMessageBox",
    "QPushButton",
    "QSpinBox",
    "QStackedWidget",
    "QStyledItemDelegate",
    "QVBoxLayout",
    "QWidget",
    "Qt",
    "STYLE_MODES",
    "SUPPORTED_EXT",
    "_FontPreviewDelegate",
    "_SAFE_CODE_FONTS",
    "_SAFE_UI_FONTS",
    "_font_choices",
    "build_workspace_qss",
    "import_background",
    "list_backgrounds",
    "list_themes",
    "load_theme",
    "pyqtSignal",
    "resolved_theme",
    "save_theme_to_resources",
    "settings",
]
