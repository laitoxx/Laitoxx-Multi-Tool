"""Composition root for SteganographyWindow."""
# ruff: noqa: F405

from .steganography_window_context import *  # noqa: F403
from .steganography_window_part1 import SteganographyWindowMixin1
from .steganography_window_part2 import SteganographyWindowMixin2
from .steganography_window_part3 import SteganographyWindowMixin3
from .steganography_window_part4 import SteganographyWindowMixin4


class SteganographyWindow(
    SteganographyWindowMixin1,
    SteganographyWindowMixin2,
    SteganographyWindowMixin3,
    SteganographyWindowMixin4,
    QDialog,
):
    def __init__(self, parent=None, theme_data=None):
        super().__init__(parent)
        self.setWindowTitle(translator.get("Steganography Studio"))
        self.setMinimumSize(880, 590)
        self.resize(1040, 680)
        self.theme_data = theme_data or {}

        self.current_image_path = None
        self.encoded_image_path = None

        self._build_ui()
        self.update_theme()
