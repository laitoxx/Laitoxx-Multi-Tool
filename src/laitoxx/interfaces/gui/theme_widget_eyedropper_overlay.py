# ruff: noqa: F405
from .theme_widget_context import *  # noqa: F403


class _EyedropperOverlay(QWidget):
    """Fullscreen transparent overlay that captures a single click to pick a screen color."""

    color_picked = pyqtSignal(QColor)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.showFullScreen()

    def mousePressEvent(self, event):
        pos = event.globalPosition().toPoint()
        try:
            screen = QApplication.primaryScreen()
            px = screen.grabWindow(0, pos.x(), pos.y(), 1, 1)
            color = QColor(px.toImage().pixel(0, 0))
            self.color_picked.emit(color)
        except Exception:
            pass
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
