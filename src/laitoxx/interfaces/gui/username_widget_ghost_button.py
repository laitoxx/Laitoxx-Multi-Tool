# ruff: noqa: F405
from .username_window_base import *  # noqa: F403


class _GhostButton(QPushButton):
    """Secondary action - transparent with border."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: rgba(192,132,252,0.06);
                border: 1px solid {_BORDER};
                border-radius: 7px;
                color: {_TEXT_SEC};
                font-size: 11px;
                font-weight: 600;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: rgba(192,132,252,0.15);
                color: {_TEXT_PRI};
                border-color: {_ACCENT};
            }}
            QPushButton:pressed {{ background: rgba(192,132,252,0.25); }}
            QPushButton:disabled {{
                background: rgba(50,50,50,0.15);
                color: {_TEXT_DIM};
                border-color: rgba(255,255,255,0.05);
            }}
        """)
