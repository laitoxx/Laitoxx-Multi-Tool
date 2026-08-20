# ruff: noqa: F405
from .theme_widget_context import *  # noqa: F403


class _SwatchLabel(QLabel):
    """Colored swatch that emits a signal when clicked."""

    clicked = pyqtSignal(QColor)

    def __init__(self, color: QColor | None = None, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setStyleSheet("border-radius: 4px; border: 1px solid rgba(255,255,255,0.2);")
        self._color = color or QColor("transparent")
        self._refresh()

    def set_color(self, color: QColor):
        self._color = color
        self._refresh()

    def color(self) -> QColor:
        return self._color

    def _refresh(self):
        px = QPixmap(36, 36)
        px.fill(self._color)
        self.setPixmap(px)

    def mousePressEvent(self, event):
        if self._color.isValid() and self._color.alpha() > 0:
            self.clicked.emit(self._color)
