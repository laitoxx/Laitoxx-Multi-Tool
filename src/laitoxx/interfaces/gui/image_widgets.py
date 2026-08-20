"""Reusable widgets for the image-search workspace."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QSizePolicy, QWidget

from laitoxx.core.localization.i18n import translator


class ScalableImageLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap_orig: QPixmap | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(100, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAcceptDrops(True)

    def _apply_colors(self, bg_card: str, border: str, text_dim: str) -> None:
        self.setStyleSheet(
            f"background:{bg_card};border:2px dashed {border};border-radius:12px;color:{text_dim};font-size:14px;"
        )
        if not self._pixmap_orig:
            text = translator.get("is_drag_hint")
            self.setText(text if text and text != "is_drag_hint" else "Drop an image here\nor use Open image")

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap_orig = pixmap
        self._rescale()

    def clear_image(self) -> None:
        self._pixmap_orig = None
        self.setPixmap(QPixmap())
        text = translator.get("is_drag_hint")
        self.setText(text if text and text != "is_drag_hint" else "Drop an image here\nor use Open image")

    def _rescale(self) -> None:
        if self._pixmap_orig and not self._pixmap_orig.isNull():
            self.setPixmap(
                self._pixmap_orig.scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.setText("")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._rescale()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        window = self.window()
        if urls and hasattr(window, "_load_file"):
            window._load_file(urls[0].toLocalFile())
