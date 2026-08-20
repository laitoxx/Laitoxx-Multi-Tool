# ruff: noqa: F405
from .username_window_base import *  # noqa: F403


class _AccentButton(QPushButton):
    """Primary action button with gradient."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(124,58,237,0.7), stop:1 rgba(192,132,252,0.7));
                border: 1px solid {_ACCENT_DIM};
                border-radius: 8px;
                color: white;
                font-size: 13px;
                font-weight: 700;
                padding: 0 20px;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(192,132,252,0.8), stop:1 rgba(244,114,182,0.7));
                border-color: {_ACCENT};
            }}
            QPushButton:pressed {{
                background: rgba(124,58,237,0.9);
                padding-top: 2px;
            }}
            QPushButton:disabled {{
                background: rgba(60,50,80,0.3);
                border-color: rgba(255,255,255,0.06);
                color: {_TEXT_DIM};
            }}
        """)
