"""Composition root for MetadataViewerWindow."""
# ruff: noqa: F405

from .gui_window_context import *  # noqa: F403
from .gui_window_part1 import MetadataViewerWindowMixin1
from .gui_window_part2 import MetadataViewerWindowMixin2
from .gui_window_part3 import MetadataViewerWindowMixin3


class MetadataViewerWindow(MetadataViewerWindowMixin1, MetadataViewerWindowMixin2, MetadataViewerWindowMixin3, QDialog):
    def __init__(self, parent=None, theme_data=None):
        super().__init__(parent)
        self.setWindowTitle(translator.get("metadata_viewer_title"))
        self.setMinimumSize(900, 600)
        self.setAcceptDrops(True)

        self.theme_data = theme_data or load_default_theme()
        self.current_metadata = {}
        self.current_filepath = None
        self.worker = None
        self.current_identity = {}

        self._build_ui()
        self._apply_style()


def open_metadata_viewer(parent=None, theme_data=None):
    dialog = MetadataViewerWindow(parent, theme_data)
    if parent is not None and hasattr(parent, "_add_open_window"):
        parent._add_open_window("Metadata Viewer", dialog)
    return dialog.exec()
