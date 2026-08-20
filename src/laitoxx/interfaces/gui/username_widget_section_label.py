# ruff: noqa: F405
from .username_window_base import *  # noqa: F403


class _SectionLabel(QLabel):
    """Small uppercase section header."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(22)
        self.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.setStyleSheet(f"""
            QLabel {{
                color: {_ACCENT};
                background: rgba(192,132,252,0.06);
                border-bottom: 1px solid {_BORDER};
                padding: 2px 8px;
                letter-spacing: 1.2px;
            }}
        """)
