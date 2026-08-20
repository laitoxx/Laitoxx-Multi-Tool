# ruff: noqa: F405
from .username_window_base import *  # noqa: F403


class _GlassPanel(QFrame):
    """Semi-transparent panel matching graph editor."""

    def __init__(self, alpha: float = 0.55, radius: int = 12, parent=None):
        super().__init__(parent)
        self._alpha = alpha
        self._radius = radius
        self._border_color = _BORDER
        self._bg_base = "15, 10, 30"
        self._refresh()

    def set_theme(self, border_color: str, bg_color: str = ""):
        """Update border and optional background tint from theme data."""
        self._border_color = border_color
        if bg_color:
            import re as _re

            m = _re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", bg_color)
            if m:
                self._bg_base = f"{m[1]}, {m[2]}, {m[3]}"
        self._refresh()

    def _refresh(self):
        bg = f"rgba({self._bg_base}, {self._alpha:.2f})"
        self.setStyleSheet(f"""
            _GlassPanel {{
                background: {bg};
                border: 1px solid {self._border_color};
                border-radius: {self._radius}px;
            }}
        """)
