"""Reusable color, accessibility, and preview widgets for Theme Editor."""

from __future__ import annotations

import colorsys
import math
import re

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from laitoxx.core.localization.i18n import translator

_BG = "rgba(10, 7, 22, 0.97)"

_PANEL = "#0f0c1e"

_PANEL2 = "#130f26"

_BORDER = "rgba(192, 132, 252, 0.25)"

_ACCENT = "#c084fc"

_ACCENT2 = "#f472b6"

_TEXT = "#f1f0ff"

_TEXT_DIM = "#6b6580"


def _parse_color(s: str) -> QColor:
    """Parse hex or rgba(...) string → QColor."""
    s = s.strip()
    m = re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)", s)
    if m:
        r, g, b = int(m[1]), int(m[2]), int(m[3])
        a = min(255, int(float(m[4]) * 255))
        return QColor(r, g, b, a)
    c = QColor(s)
    return c if c.isValid() else QColor("#ffffff")


def _to_css(color: QColor, original_str: str) -> str:
    """Serialise QColor back to CSS, preserving rgba format if original was rgba."""
    if "rgba" in original_str:
        return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alphaF():.3f})"
    return color.name()


def _wcag_lum(c: QColor) -> float:
    """Relative luminance of a color per WCAG 2.1."""
    vals = [c.redF(), c.greenF(), c.blueF()]
    lin = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in vals]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _wcag_contrast(fg: QColor, bg: QColor) -> float:
    """Relative luminance contrast ratio (WCAG 2.1)."""
    l1, l2 = _wcag_lum(fg), _wcag_lum(bg)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def _generate_palette(base: QColor) -> dict[str, list[QColor]]:
    """Generate complementary/triadic/analogous color schemes from base."""
    r, g, b = base.redF(), base.greenF(), base.blueF()
    h, s, v = colorsys.rgb_to_hsv(r, g, b)

    def from_hsv(h2: float, s2: float, v2: float) -> QColor:
        r2, g2, b2 = colorsys.hsv_to_rgb(h2 % 1.0, max(0.0, min(1.0, s2)), max(0.0, min(1.0, v2)))
        return QColor.fromRgbF(r2, g2, b2)

    return {
        "complementary": [base, from_hsv(h + 0.5, s, v)],
        "triadic": [base, from_hsv(h + 0.333, s, v), from_hsv(h + 0.667, s, v)],
        "analogous": [
            from_hsv(h - 0.167, s, v),
            from_hsv(h - 0.083, s, v),
            base,
            from_hsv(h + 0.083, s, v),
            from_hsv(h + 0.167, s, v),
        ],
    }


_CB_MATRICES: dict[str, list[list[float]]] = {
    "deuteranopia": [
        [0.367, 0.861, -0.228],
        [0.280, 0.673, 0.047],
        [-0.012, 0.043, 0.969],
    ],
    "protanopia": [
        [0.152, 1.053, -0.205],
        [0.115, 0.786, 0.099],
        [-0.004, -0.048, 1.052],
    ],
    "tritanopia": [
        [1.256, -0.077, -0.179],
        [-0.078, 0.931, 0.148],
        [0.005, 0.691, 0.304],
    ],
}


def _apply_colorblind_matrix(color: QColor, mode: str) -> QColor:
    """Simulate color blindness by applying a 3×3 RGB transform."""
    if mode not in _CB_MATRICES:
        return color
    m = _CB_MATRICES[mode]
    r, g, b = color.redF(), color.greenF(), color.blueF()
    nr = max(0.0, min(1.0, m[0][0] * r + m[0][1] * g + m[0][2] * b))
    ng = max(0.0, min(1.0, m[1][0] * r + m[1][1] * g + m[1][2] * b))
    nb = max(0.0, min(1.0, m[2][0] * r + m[2][1] * g + m[2][2] * b))
    return QColor.fromRgbF(nr, ng, nb, color.alphaF())


def _wcag_autofix(fg: QColor, bg: QColor, target: float = 4.5) -> QColor:
    """Adjust fg value (HSV) until WCAG contrast ≥ target against bg."""
    r, g, b = fg.redF(), fg.greenF(), fg.blueF()
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    for direction in (-1, 1):
        test_v = v
        for _ in range(50):
            test_v = max(0.0, min(1.0, test_v + direction * 0.02))
            r2, g2, b2 = colorsys.hsv_to_rgb(h, s, test_v)
            candidate = QColor.fromRgbF(r2, g2, b2, fg.alphaF())
            if _wcag_contrast(candidate, bg) >= target:
                return candidate
    return fg


def _palette_to_theme(colors: list[QColor], base: dict) -> dict:
    """Map a list of palette colors onto the 19 theme keys sensibly."""
    if not colors:
        return {}

    c0 = colors[0]
    r, g, b = c0.redF(), c0.greenF(), c0.blueF()
    h, s, v = colorsys.rgb_to_hsv(r, g, b)

    def mk(h2, s2, v2, a=1.0) -> str:
        r2, g2, b2 = colorsys.hsv_to_rgb(h2 % 1.0, max(0.0, min(1.0, s2)), max(0.0, min(1.0, v2)))
        if a < 1.0:
            return f"rgba({int(r2 * 255)}, {int(g2 * 255)}, {int(b2 * 255)}, {a:.2f})"
        return QColor.fromRgbF(r2, g2, b2).name()

    cl = colors[-1]
    rl, gl, bl = cl.redF(), cl.greenF(), cl.blueF()
    hl, sl, vl = colorsys.rgb_to_hsv(rl, gl, bl)

    result = {
        "accent_color": mk(h, s, v),
        "accent_dim_color": mk(h, s, v * 0.7),
        "button_bg_color": mk(h, s, v, 0.15),
        "button_hover_bg_color": mk(h, s, v, 0.25),
        "button_pressed_bg_color": mk(h, s, v, 0.40),
        "button_border_color": mk(h, s, v, 0.40),
        "button_text_color": "white",
        "text_area_bg_color": mk(h, s * 0.3, v * 0.12, 0.85),
        "text_area_border_color": mk(h, s, v, 0.30),
        "text_area_text_color": "white",
        "sidebar_bg_color": mk(h, s * 0.3, v * 0.12, 0.50),
        "title_text_color": mk(h, s, v),
        "plugin_canvas_bg_color": mk(hl, sl * 0.4, vl * 0.15),
        "scrollbar_handle_color": mk(h, s, v, 0.40),
        "scrollbar_handle_hover_color": mk(h, s, v, 0.70),
        "window_bg_color": mk(hl, sl * 0.4, vl * 0.10, 0.92),
        "panel_bg_color": mk(hl, sl * 0.4, vl * 0.12, 0.80),
        "border_color": mk(h, s, v, 0.30),
        "text_secondary_color": mk(h, s * 0.5, v * 0.85),
    }
    result["border_radius"] = base.get("border_radius", 10)
    return result


def _build_dialog_ss(theme: dict) -> str:
    """Build the theme-editor dialog stylesheet from the current app theme."""
    accent = theme.get("accent_color", _ACCENT)
    bdr = theme.get("border_color", theme.get("button_border_color", _BORDER))
    txt = theme.get("text_area_text_color", _TEXT)
    bg_win = theme.get("window_bg_color", theme.get("text_area_bg_color", _PANEL))
    btn_bg = theme.get("button_bg_color", "rgba(192,132,252,0.12)")
    btn_hov = theme.get("button_hover_bg_color", "rgba(192,132,252,0.28)")
    sb_hand = theme.get("scrollbar_handle_color", bdr)

    return f"""
    QDialog {{
        background: {bg_win};
        color: {txt};
        font-family: 'Segoe UI', Arial, sans-serif;
    }}
    QLabel {{
        color: {txt};
        background: transparent;
        font-size: 12px;
    }}
    QLineEdit {{
        background: rgba(255,255,255,0.05);
        border: 1px solid {bdr};
        border-radius: 6px;
        color: {txt};
        padding: 4px 8px;
        font-size: 12px;
    }}
    QLineEdit:focus {{
        border-color: {accent};
    }}
    QPushButton {{
        background: {btn_bg};
        border: 1px solid {bdr};
        border-radius: 7px;
        color: {txt};
        padding: 5px 12px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background: {btn_hov};
        border-color: {accent};
    }}
    QPushButton:pressed {{
        background: {btn_hov};
    }}
    QListWidget {{
        background: rgba(255,255,255,0.03);
        border: 1px solid {bdr};
        border-radius: 8px;
        color: {txt};
        font-size: 12px;
        outline: none;
    }}
    QListWidget::item {{
        padding: 5px 8px;
        border-radius: 5px;
    }}
    QListWidget::item:selected {{
        background: {btn_bg};
        color: {txt};
    }}
    QListWidget::item:hover {{
        background: rgba(255,255,255,0.06);
    }}
    QScrollBar:vertical {{
        background: transparent; width: 5px; margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {sb_hand};
        border-radius: 2px; min-height: 20px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QFrame[frameShape="4"], QFrame[frameShape="5"] {{
        color: {bdr};
    }}
"""


__all__ = [
    "QApplication",
    "QBrush",
    "QColor",
    "QFrame",
    "QHBoxLayout",
    "QLabel",
    "QLinearGradient",
    "QPainter",
    "QPen",
    "QPixmap",
    "QPointF",
    "QPushButton",
    "QRectF",
    "QSize",
    "QVBoxLayout",
    "QWidget",
    "Qt",
    "_ACCENT",
    "_ACCENT2",
    "_BG",
    "_BORDER",
    "_CB_MATRICES",
    "_PANEL",
    "_PANEL2",
    "_TEXT",
    "_TEXT_DIM",
    "_apply_colorblind_matrix",
    "_build_dialog_ss",
    "_generate_palette",
    "_palette_to_theme",
    "_parse_color",
    "_to_css",
    "_wcag_autofix",
    "_wcag_contrast",
    "_wcag_lum",
    "colorsys",
    "math",
    "pyqtSignal",
    "re",
    "translator",
]
