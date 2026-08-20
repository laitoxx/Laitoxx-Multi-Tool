# ruff: noqa: F405
from .theme_widget_context import *  # noqa: F403


class _ContrastBadge(QLabel):
    def update_colors(self, fg: QColor, bg: QColor):
        ratio = _wcag_contrast(fg, bg)
        if ratio >= 7.0:
            level, color = "AAA", "#00d084"
        elif ratio >= 4.5:
            level, color = "AA", "#7ec8e3"
        elif ratio >= 3.0:
            level, color = "AA Lrg", "#f9c74f"
        else:
            level, color = translator.get("te_low_contrast"), "#e63946"
        self.setText(f"Contrast {ratio:.1f}:1  [{level}]")
        self.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 600; background: transparent;")
