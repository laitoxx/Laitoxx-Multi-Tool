# ruff: noqa: F405
from .theme_widget_context import *  # noqa: F403


class _AlphaBar(QWidget):
    """Horizontal alpha slider rendered on a checkerboard + color gradient."""

    alpha_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(22)
        self._alpha = 1.0
        self._color = QColor("white")

    def set_color(self, color: QColor):
        self._color = color
        self._alpha = color.alphaF()
        self.update()

    def alpha(self) -> float:
        return self._alpha

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Checkerboard
        sq = 8
        for xi in range(0, w, sq):
            for yi in range(0, h, sq):
                light = ((xi // sq) + (yi // sq)) % 2 == 0
                p.fillRect(xi, yi, sq, sq, QColor("#aaaaaa" if light else "#777777"))

        # Gradient overlay
        grad = QLinearGradient(0, 0, w, 0)
        transparent = QColor(self._color)
        transparent.setAlpha(0)
        opaque = QColor(self._color)
        opaque.setAlpha(255)
        grad.setColorAt(0, transparent)
        grad.setColorAt(1, opaque)
        p.fillRect(0, 0, w, h, QBrush(grad))

        # Handle
        x = int(self._alpha * (w - 6))
        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(QBrush(QColor("white")))
        p.drawRoundedRect(x, 2, 6, h - 4, 3, 3)

    def mousePressEvent(self, event):
        self._set_from_x(event.position().x())

    def mouseMoveEvent(self, event):
        self._set_from_x(event.position().x())

    def _set_from_x(self, x):
        self._alpha = max(0.0, min(1.0, x / self.width()))
        self.update()
        self.alpha_changed.emit(self._alpha)
