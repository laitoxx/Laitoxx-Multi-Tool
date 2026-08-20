"""Composition root for CogniPassWindow."""
# ruff: noqa: F405

from .cognipass_window_context import *  # noqa: F403
from .cognipass_window_part1 import CogniPassWindowMixin1
from .cognipass_window_part2 import CogniPassWindowMixin2


class CogniPassWindow(CogniPassWindowMixin1, CogniPassWindowMixin2, QDialog):
    def __init__(self, parent=None, theme_data: dict | None = None):
        super().__init__(parent)
        self.theme_data = theme_data or {}
        self._worker: _CogniPassWorker | None = None
        self._last_result: CogniPassResult | None = None
        self.setObjectName("CogniPassWindow")
        self.setWindowTitle(_t("cognipass_title", "Targeted password generator"))
        self.setMinimumWidth(620)
        self.resize(700, 680)
        self._build_ui()
        self.update_theme(self.theme_data)
