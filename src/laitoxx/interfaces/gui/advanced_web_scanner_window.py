"""Composition root for AdvancedWebScannerWindow."""
# ruff: noqa: F405

from .advanced_web_scanner_window_context import *  # noqa: F403
from .advanced_web_scanner_window_part1 import AdvancedWebScannerWindowMixin1
from .advanced_web_scanner_window_part2 import AdvancedWebScannerWindowMixin2
from .advanced_web_scanner_window_part3 import AdvancedWebScannerWindowMixin3


class AdvancedWebScannerWindow(
    AdvancedWebScannerWindowMixin1, AdvancedWebScannerWindowMixin2, AdvancedWebScannerWindowMixin3, QDialog
):
    def __init__(self, parent=None, theme_data=None):
        super().__init__(parent)
        self.theme_data = theme_data or {}
        self.report = None
        self._thread: _ScanThread | None = None
        self._active_scanner_warning_shown = False
        self.setWindowTitle(translator.get("Advanced Web Scanner"))
        self.setMinimumSize(1120, 760)
        self.resize(1440, 920)
        self._build_ui()
        self._apply_style()
