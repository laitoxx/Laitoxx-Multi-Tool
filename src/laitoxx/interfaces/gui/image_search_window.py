"""Composition root for ImageSearchWindow."""
# ruff: noqa: F405

from .image_search_window_context import *  # noqa: F403
from .image_search_window_part1 import ImageSearchWindowMixin1
from .image_search_window_part2 import ImageSearchWindowMixin2
from .image_search_window_part3 import ImageSearchWindowMixin3
from .image_search_window_part4 import ImageSearchWindowMixin4
from .image_search_window_part5 import ImageSearchWindowMixin5
from .image_search_window_part6 import ImageSearchWindowMixin6


class ImageSearchWindow(
    ImageSearchWindowMixin1,
    ImageSearchWindowMixin2,
    ImageSearchWindowMixin3,
    ImageSearchWindowMixin4,
    ImageSearchWindowMixin5,
    ImageSearchWindowMixin6,
    QDialog,
):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_t("is_title", "LAITOXX - Image Analysis"))
        self.setMinimumSize(520, 420)
        self.resize(980, 680)

        self._theme: dict[str, Any] = {}
        self._load_theme_from_parent()
        self._apply_style()

        # State
        self._file_path: str | None = None
        self._pil_original: Image.Image | None = None
        self._pil_edited: Image.Image | None = None
        self._current_tool: str = "search"
        self._hashes: dict[str, str] = {}
        self._search_urls: dict[str, str] = {}
        self._show_original = False
        self._search_btn: QPushButton | None = None

        # Background threads
        self._search_thread: QThread | None = None
        self._hash_thread: QThread | None = None
        self._forensics_thread: QThread | None = None

        # Debounce timer for editor sliders
        self._edit_timer = QTimer()
        self._edit_timer.setSingleShot(True)
        self._edit_timer.setInterval(120)
        self._edit_timer.timeout.connect(self._apply_edits)

        self._build_ui()
