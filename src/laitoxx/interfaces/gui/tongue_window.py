"""Composition root for TongueWindow."""
# ruff: noqa: F405

from .tongue_window_context import *  # noqa: F403
from .tongue_window_part1 import TongueWindowMixin1
from .tongue_window_part2 import TongueWindowMixin2
from .tongue_window_part3 import TongueWindowMixin3
from .tongue_window_part4 import TongueWindowMixin4


class TongueWindow(TongueWindowMixin1, TongueWindowMixin2, TongueWindowMixin3, TongueWindowMixin4, QDialog):
    def __init__(self, parent=None, theme_data=None):
        super().__init__(parent)
        self.theme_data = theme_data or {}
        self.report: dict | None = None
        self._thread: _TongueThread | None = None
        self._close_pending = False
        self.setObjectName("TongueWindow")
        self.setWindowTitle(_t("TONgue"))
        self.setMinimumSize(1180, 760)
        self.resize(1520, 900)
        self._build_ui()
        self.update_theme(self.theme_data)
