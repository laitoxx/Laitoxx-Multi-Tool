"""Composition root for SettingsWindow."""
# ruff: noqa: F405

from .settings_window_context import *  # noqa: F403
from .settings_window_part1 import SettingsWindowMixin1
from .settings_window_part2 import SettingsWindowMixin2


class SettingsWindow(SettingsWindowMixin1, SettingsWindowMixin2, QDialog):
    theme_changed = pyqtSignal(dict, str)
    background_changed = pyqtSignal(str)
    language_changed = pyqtSignal(str)
    proxy_changed = pyqtSignal()
    application_reset = pyqtSignal()

    _PAGE_MARGINS = (24, 20, 24, 20)
    _TITLE_STYLE = "font-size: 20px; font-weight: 700; margin-bottom: 8px;"
    _LABEL_STYLE = "font-size: 13px;"

    def __init__(self, parent=None, theme_data: dict | None = None, translator=None):
        super().__init__(parent)
        self._theme_data = theme_data or DEFAULT_THEME.copy()
        self._tr = translator  # may be None
        self.setWindowTitle(self._t("settings_window_title"))
        self.setMinimumSize(720, 500)
        self._build_ui()
        self._apply_theme()
