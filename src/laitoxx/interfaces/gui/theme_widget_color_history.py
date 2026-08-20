# ruff: noqa: F405
from .theme_widget_context import *  # noqa: F403


class _ColorHistory(QWidget):
    """Clickable strip of recent colors."""

    color_picked = pyqtSignal(str)  # emits CSS string

    MAX = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self._colors: list[str] = []

    def push(self, css: str):
        if css in self._colors:
            return
        self._colors.insert(0, css)
        if len(self._colors) > self.MAX:
            self._colors.pop()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        size = 24
        gap = 4
        for i, css in enumerate(self._colors):
            x = i * (size + gap)
            c = _parse_color(css)
            # Checkerboard under alpha
            for dx in range(0, size, 6):
                for dy in range(0, size, 6):
                    light = (dx // 6 + dy // 6) % 2 == 0
                    p.fillRect(x + dx, 2 + dy, 6, 6, QColor("#aaa" if light else "#777"))
            p.fillRect(x, 2, size, size, QBrush(c))
            p.setPen(QPen(QColor(100, 100, 100), 1))
            p.drawRoundedRect(x, 2, size, size, 3, 3)

    def mousePressEvent(self, event):
        size, gap = 24, 4
        idx = int(event.position().x()) // (size + gap)
        if 0 <= idx < len(self._colors):
            self.color_picked.emit(self._colors[idx])

    def sizeHint(self) -> QSize:
        return QSize(self.MAX * 28, 28)
