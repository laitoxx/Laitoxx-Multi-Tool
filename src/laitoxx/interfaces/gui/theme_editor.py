"""
theme_editor.py — Modern Theme Editor for LAITOXX.

Layout (3-panel monolithic window):
  Left: searchable element list grouped by category
  Center: custom color picker (hue wheel + SV square + hex input + alpha slider)
  Right: preset themes, contrast indicator, color history, glow/glass settings
"""

from __future__ import annotations

import colorsys
import math
import re

from PyQt6.QtCore import (
    QPointF,
    QRectF,
    QSize,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from laitoxx.core.settings.theme import DEFAULT_THEME, save_theme_to_resources
from laitoxx.interfaces.gui.translator import translator

# ─── Design tokens ────────────────────────────────────────────────────────────
_BG = "rgba(10, 7, 22, 0.97)"
_PANEL = "#0f0c1e"
_PANEL2 = "#130f26"
_BORDER = "rgba(192, 132, 252, 0.25)"
_ACCENT = "#c084fc"
_ACCENT2 = "#f472b6"
_TEXT = "#f1f0ff"
_TEXT_DIM = "#6b6580"

# ─── Category groups (key → list of theme_data keys) ─────────────────────────
_GROUPS: dict[str, list[str]] = {
    "te_group_buttons": [
        "button_bg_color",
        "button_hover_bg_color",
        "button_pressed_bg_color",
        "button_border_color",
        "button_text_color",
    ],
    "te_group_text_area": [
        "text_area_bg_color",
        "text_area_border_color",
        "text_area_text_color",
    ],
    "te_group_panels": [
        "sidebar_bg_color",
        "title_text_color",
        "plugin_canvas_bg_color",
    ],
    "te_group_scrollbar": [
        "scrollbar_handle_color",
        "scrollbar_handle_hover_color",
    ],
    "te_group_windows": [
        "accent_color",
        "accent_dim_color",
        "window_bg_color",
        "panel_bg_color",
        "border_color",
        "text_secondary_color",
    ],
}

# ─── Built-in preset themes ───────────────────────────────────────────────────
PRESETS: dict[str, dict] = {
    "Cyberpunk": {
        "button_bg_color": "rgba(0, 255, 170, 0.1)",
        "button_hover_bg_color": "rgba(0, 255, 170, 0.25)",
        "button_pressed_bg_color": "rgba(0, 255, 170, 0.4)",
        "button_border_color": "rgba(0, 255, 170, 0.5)",
        "button_text_color": "#00ffaa",
        "text_area_bg_color": "rgba(0, 0, 0, 0.6)",
        "text_area_border_color": "rgba(0, 255, 170, 0.3)",
        "text_area_text_color": "#00ffaa",
        "sidebar_bg_color": "rgba(0, 20, 15, 0.5)",
        "title_text_color": "#00ffff",
        "scrollbar_handle_color": "rgba(0, 255, 170, 0.4)",
        "scrollbar_handle_hover_color": "rgba(0, 255, 170, 0.7)",
        "plugin_canvas_bg_color": "#001a10",
        "accent_color": "#00ffaa",
        "accent_dim_color": "#00b87a",
        "window_bg_color": "rgba(0, 8, 5, 0.92)",
        "panel_bg_color": "rgba(0, 15, 10, 0.80)",
        "border_color": "rgba(0, 255, 170, 0.30)",
        "text_secondary_color": "#00cc88",
    },
    "Dracula": {
        "button_bg_color": "rgba(98, 114, 164, 0.2)",
        "button_hover_bg_color": "rgba(98, 114, 164, 0.4)",
        "button_pressed_bg_color": "rgba(98, 114, 164, 0.6)",
        "button_border_color": "rgba(189, 147, 249, 0.4)",
        "button_text_color": "#f8f8f2",
        "text_area_bg_color": "rgba(40, 42, 54, 0.85)",
        "text_area_border_color": "rgba(98, 114, 164, 0.4)",
        "text_area_text_color": "#f8f8f2",
        "sidebar_bg_color": "rgba(30, 32, 43, 0.7)",
        "title_text_color": "#bd93f9",
        "scrollbar_handle_color": "rgba(98, 114, 164, 0.5)",
        "scrollbar_handle_hover_color": "rgba(189, 147, 249, 0.7)",
        "plugin_canvas_bg_color": "#1e2030",
        "accent_color": "#bd93f9",
        "accent_dim_color": "#7c5cbf",
        "window_bg_color": "rgba(20, 21, 30, 0.94)",
        "panel_bg_color": "rgba(30, 31, 43, 0.82)",
        "border_color": "rgba(189, 147, 249, 0.28)",
        "text_secondary_color": "#9a86c8",
    },
    "Nord": {
        "button_bg_color": "rgba(136, 192, 208, 0.15)",
        "button_hover_bg_color": "rgba(136, 192, 208, 0.3)",
        "button_pressed_bg_color": "rgba(136, 192, 208, 0.5)",
        "button_border_color": "rgba(136, 192, 208, 0.4)",
        "button_text_color": "#eceff4",
        "text_area_bg_color": "rgba(46, 52, 64, 0.85)",
        "text_area_border_color": "rgba(67, 76, 94, 0.6)",
        "text_area_text_color": "#eceff4",
        "sidebar_bg_color": "rgba(36, 41, 51, 0.7)",
        "title_text_color": "#88c0d0",
        "scrollbar_handle_color": "rgba(136, 192, 208, 0.4)",
        "scrollbar_handle_hover_color": "rgba(136, 192, 208, 0.7)",
        "plugin_canvas_bg_color": "#2e3440",
        "accent_color": "#88c0d0",
        "accent_dim_color": "#5e90a0",
        "window_bg_color": "rgba(18, 20, 28, 0.93)",
        "panel_bg_color": "rgba(28, 32, 42, 0.82)",
        "border_color": "rgba(136, 192, 208, 0.28)",
        "text_secondary_color": "#7aa5b0",
    },
    "Matrix": {
        "button_bg_color": "rgba(0, 180, 0, 0.1)",
        "button_hover_bg_color": "rgba(0, 255, 0, 0.2)",
        "button_pressed_bg_color": "rgba(0, 255, 0, 0.35)",
        "button_border_color": "rgba(0, 200, 0, 0.4)",
        "button_text_color": "#00ff41",
        "text_area_bg_color": "rgba(0, 10, 0, 0.8)",
        "text_area_border_color": "rgba(0, 180, 0, 0.3)",
        "text_area_text_color": "#00ff41",
        "sidebar_bg_color": "rgba(0, 15, 0, 0.6)",
        "title_text_color": "#00ff41",
        "scrollbar_handle_color": "rgba(0, 200, 0, 0.4)",
        "scrollbar_handle_hover_color": "rgba(0, 255, 0, 0.7)",
        "plugin_canvas_bg_color": "#000a00",
        "accent_color": "#00ff41",
        "accent_dim_color": "#00b82e",
        "window_bg_color": "rgba(0, 5, 0, 0.93)",
        "panel_bg_color": "rgba(0, 10, 0, 0.82)",
        "border_color": "rgba(0, 200, 0, 0.28)",
        "text_secondary_color": "#00b830",
    },
    "Classic Light": {
        "button_bg_color": "rgba(60, 100, 200, 0.15)",
        "button_hover_bg_color": "rgba(60, 100, 200, 0.28)",
        "button_pressed_bg_color": "rgba(60, 100, 200, 0.45)",
        "button_border_color": "rgba(60, 100, 200, 0.5)",
        "button_text_color": "#1a1a2e",
        "text_area_bg_color": "rgba(245, 245, 250, 0.9)",
        "text_area_border_color": "rgba(100, 120, 200, 0.4)",
        "text_area_text_color": "#1a1a2e",
        "sidebar_bg_color": "rgba(220, 225, 240, 0.7)",
        "title_text_color": "#2a2a5e",
        "scrollbar_handle_color": "rgba(100, 120, 200, 0.4)",
        "scrollbar_handle_hover_color": "rgba(60, 100, 200, 0.7)",
        "plugin_canvas_bg_color": "#dce0f0",
        "accent_color": "#3c64c8",
        "accent_dim_color": "#2a4a9e",
        "window_bg_color": "rgba(240, 243, 255, 0.95)",
        "panel_bg_color": "rgba(225, 230, 248, 0.88)",
        "border_color": "rgba(60, 100, 200, 0.30)",
        "text_secondary_color": "#5570aa",
    },
    "Red Laitoxx": DEFAULT_THEME.copy(),
}


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# Hue-Saturation-Value picker wheel
# ══════════════════════════════════════════════════════════════════════════════


class _HueSatWheel(QWidget):
    """Circular hue wheel + inner SV square."""

    color_changed = pyqtSignal(QColor)

    _RING_W = 18

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self._hue = 0
        self._sat = 1.0
        self._val = 1.0
        self._alpha = 1.0
        self._dragging_ring = False
        self._dragging_sq = False
        self._cache: QPixmap | None = None

    # ── public API ──────────────────────────────────────────────────────────

    def set_color(self, color: QColor):
        h, s, v, a = (
            color.hsvHueF(),
            color.saturationF(),
            color.valueF(),
            color.alphaF(),
        )
        if h < 0:
            h = 0.0
        self._hue, self._sat, self._val, self._alpha = h, s, v, a
        self._cache = None
        self.update()

    def color(self) -> QColor:
        c = QColor.fromHsvF(self._hue, self._sat, self._val)
        c.setAlphaF(self._alpha)
        return c

    def set_alpha(self, alpha: float):
        self._alpha = max(0.0, min(1.0, alpha))
        self.update()
        self.color_changed.emit(self.color())

    # ── paint ────────────────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = self.width() / 2, self.height() / 2
        r_outer = min(cx, cy) - 2
        r_inner = r_outer - self._RING_W

        # ── hue ring ─────────────────────────────────────────────────────
        steps = 360
        for i in range(steps):
            angle_start = i - 1
            angle_span = 2
            hue_color = QColor.fromHsvF(i / steps, 1.0, 1.0)
            pen = QPen(hue_color, self._RING_W)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawArc(
                QRectF(
                    cx - r_outer + self._RING_W / 2,
                    cy - r_outer + self._RING_W / 2,
                    (r_outer - self._RING_W / 2) * 2,
                    (r_outer - self._RING_W / 2) * 2,
                ),
                int(angle_start * 16),
                int(angle_span * 16),
            )

        # ── SV square inside ring ─────────────────────────────────────────
        sq = r_inner * math.sqrt(2) - 4
        sq_x, sq_y = cx - sq / 2, cy - sq / 2

        img_size = int(sq)
        if img_size > 0:
            px = QPixmap(img_size, img_size)
            pp = QPainter(px)
            pp.setRenderHint(QPainter.RenderHint.Antialiasing)
            for xi in range(img_size):
                sat = xi / (img_size - 1) if img_size > 1 else 1.0
                grad = QLinearGradient(0, 0, 0, img_size)
                grad.setColorAt(0, QColor.fromHsvF(self._hue, sat, 1.0))
                grad.setColorAt(1, QColor.fromHsvF(self._hue, sat, 0.0))
                pen = QPen(QBrush(grad), 1)
                pp.setPen(pen)
                pp.drawLine(xi, 0, xi, img_size)
            pp.end()
            p.drawPixmap(int(sq_x), int(sq_y), px)

            # SV crosshair
            cx_sq = sq_x + self._sat * sq
            cy_sq = sq_y + (1 - self._val) * sq
            p.setPen(QPen(QColor("white"), 2))
            p.drawEllipse(QPointF(cx_sq, cy_sq), 5, 5)
            p.setPen(QPen(QColor("black"), 1))
            p.drawEllipse(QPointF(cx_sq, cy_sq), 5, 5)

        # ── hue indicator on ring ─────────────────────────────────────────
        angle_rad = self._hue * 2 * math.pi
        mid_r = r_outer - self._RING_W / 2
        ix = cx + mid_r * math.cos(angle_rad - math.pi / 2)
        iy = cy + mid_r * math.sin(angle_rad - math.pi / 2)
        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(QBrush(QColor.fromHsvF(self._hue, 1.0, 1.0)))
        p.drawEllipse(QPointF(ix, iy), 7, 7)

    # ── mouse ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        self._handle_mouse(event.position(), press=True)

    def mouseMoveEvent(self, event):
        self._handle_mouse(event.position())

    def mouseReleaseEvent(self, _):
        self._dragging_ring = self._dragging_sq = False

    def _handle_mouse(self, pos: QPointF, press=False):
        cx, cy = self.width() / 2, self.height() / 2
        dx, dy = pos.x() - cx, pos.y() - cy
        dist = math.hypot(dx, dy)
        r_outer = min(cx, cy) - 2
        r_inner = r_outer - self._RING_W
        sq = r_inner * math.sqrt(2) - 4

        in_ring = r_inner <= dist <= r_outer
        in_sq = abs(dx) <= sq / 2 and abs(dy) <= sq / 2

        if press:
            self._dragging_ring = in_ring
            self._dragging_sq = in_sq and not in_ring

        if self._dragging_ring:
            self._hue = (math.atan2(dy, dx) / (2 * math.pi) + 0.25) % 1.0
            self.color_changed.emit(self.color())
            self.update()

        elif self._dragging_sq:
            self._sat = max(0.0, min(1.0, (dx + sq / 2) / sq))
            self._val = max(0.0, min(1.0, 1 - (dy + sq / 2) / sq))
            self.color_changed.emit(self.color())
            self.update()


# ══════════════════════════════════════════════════════════════════════════════
# Alpha bar
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# Color history strip
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# Contrast indicator
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# Main dialog
# ══════════════════════════════════════════════════════════════════════════════


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


class _PreviewPane(QWidget):
    """Live preview of how the current theme looks on real UI elements."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QLineEdit as _LE
        from PyQt6.QtWidgets import QPlainTextEdit

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        self._title_lbl = QLabel("Title Text")
        self._title_lbl.setObjectName("preview_title")
        lay.addWidget(self._title_lbl)

        self._secondary_lbl = QLabel("Secondary / dim text")
        self._secondary_lbl.setObjectName("preview_secondary")
        lay.addWidget(self._secondary_lbl)

        row = QHBoxLayout()
        self._btn_normal = QPushButton("Sample Button")
        self._btn_normal.setObjectName("preview_btn")
        self._btn_hover = QPushButton("Hover State")
        self._btn_hover.setObjectName("preview_btn_hover")
        row.addWidget(self._btn_normal)
        row.addWidget(self._btn_hover)
        lay.addLayout(row)

        self._input = _LE()
        self._input.setPlaceholderText("Input field placeholder...")
        self._input.setObjectName("preview_input")
        lay.addWidget(self._input)

        self._text_area = QPlainTextEdit()
        self._text_area.setPlainText("Text area content\nLine two\nLine three")
        self._text_area.setObjectName("preview_textarea")
        self._text_area.setFixedHeight(80)
        lay.addWidget(self._text_area)

        self._panel = QFrame()
        self._panel.setObjectName("preview_panel")
        self._panel.setFixedHeight(32)
        panel_lbl = QLabel("  Panel / Sidebar")
        panel_lbl.setObjectName("preview_panel_lbl")
        panel_lay = QHBoxLayout(self._panel)
        panel_lay.setContentsMargins(0, 0, 0, 0)
        panel_lay.addWidget(panel_lbl)
        lay.addWidget(self._panel)

        lay.addStretch()

    def apply_theme(self, td: dict, colorblind_mode: str = "none", dark_bg: bool = True):
        """Restyle all preview widgets from theme data."""

        def col(key: str, fallback: str = "#888") -> str:
            css = td.get(key, fallback)
            c = _parse_color(css)
            if colorblind_mode != "none":
                c = _apply_colorblind_matrix(c, colorblind_mode)
            c.setAlpha(255)
            return c.name()

        def col_a(key: str, fallback: str = "#888", alpha: int = 255) -> str:
            css = td.get(key, fallback)
            c = _parse_color(css)
            if colorblind_mode != "none":
                c = _apply_colorblind_matrix(c, colorblind_mode)
            c.setAlpha(alpha)
            return c.name(QColor.NameFormat.HexArgb)

        br = td.get("border_radius", 10)
        bg = "#ffffff" if not dark_bg else "#0a0a0a"
        accent = col("accent_color", _ACCENT)
        txt = col("text_area_text_color", _TEXT)
        txt2 = col("text_secondary_color", _TEXT_DIM)
        btn_bg = col_a("button_bg_color", "rgba(200,0,0,0.1)", 180)
        btn_hov = col_a("button_hover_bg_color", "rgba(200,0,0,0.2)", 200)
        btn_bdr = col_a("button_border_color", "rgba(255,255,255,0.2)", 100)
        btn_txt = col("button_text_color", "white")
        ta_bg = col_a("text_area_bg_color", "rgba(0,0,0,0.5)", 200)
        ta_bdr = col("text_area_border_color", "#888")
        panel = col_a("panel_bg_color", "rgba(20,8,8,0.8)", 220)

        self.setStyleSheet(f"background: {bg};")
        self._title_lbl.setStyleSheet(f"color: {accent}; font-size: 14px; font-weight: bold; background: transparent;")
        self._secondary_lbl.setStyleSheet(f"color: {txt2}; font-size: 12px; background: transparent;")
        self._btn_normal.setStyleSheet(
            f"QPushButton {{ background: {btn_bg}; border: 1px solid {btn_bdr}; border-radius: {br}px; color: {btn_txt}; padding: 6px 14px; }}"
        )
        self._btn_hover.setStyleSheet(
            f"QPushButton {{ background: {btn_hov}; border: 1px solid {accent}; border-radius: {br}px; color: {btn_txt}; padding: 6px 14px; }}"
        )
        self._input.setStyleSheet(
            f"QLineEdit {{ background: {ta_bg}; border: 1px solid {ta_bdr}; border-radius: {br}px; color: {txt}; padding: 4px 8px; }}"
        )
        self._text_area.setStyleSheet(
            f"QPlainTextEdit {{ background: {ta_bg}; border: 1px solid {ta_bdr}; border-radius: {br}px; color: {txt}; }}"
        )
        self._panel.setStyleSheet(f"QFrame {{ background: {panel}; border-radius: {br}px; }}")
        lbl = self._panel.findChild(QLabel, "preview_panel_lbl")
        if lbl:
            lbl.setStyleSheet(f"color: {txt}; background: transparent;")


class ThemeEditorDialog(QDialog):
    """Monolithic theme editor — live preview, custom picker, presets, history."""

    def __init__(self, parent, current_theme: dict):
        super().__init__(parent)
        self.setWindowTitle(translator.get("theme_editor_title"))
        self.setMinimumSize(960, 600)
        self.resize(1100, 680)

        self.theme_data = current_theme.copy()
        self.original_theme = current_theme.copy()
        self._current_key: str | None = None
        self._updating_hex = False
        self._last_palette: list[QColor] = []
        self._colorblind_mode: str = "none"
        self._preview_dark: bool = True
        self._eyedropper: _EyedropperOverlay | None = None

        # build flat ordered list  key → display label
        theme_map_raw = translator.get("theme_map")
        self._theme_map: dict[str, str] = theme_map_raw if isinstance(theme_map_raw, dict) else {}

        # Update module tokens so _populate_list uses correct accent colour
        import laitoxx.interfaces.gui.theme_editor as _self_mod

        _self_mod._ACCENT = current_theme.get("accent_color", _ACCENT)
        _self_mod._TEXT = current_theme.get("text_area_text_color", _TEXT)
        _self_mod._TEXT_DIM = current_theme.get("text_secondary_color", _TEXT_DIM)
        _self_mod._BORDER = current_theme.get("border_color", current_theme.get("button_border_color", _BORDER))

        self._build_ui()
        self.setStyleSheet(_build_dialog_ss(current_theme))
        self._restyle_panels(current_theme)
        self._populate_list()
        self._populate_library()
        # select first item
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    # ══════════════════════════════════════════════════════════════════════
    # Build UI
    # ══════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left panel ──────────────────────────────────────────────────────
        self._left_pane = QWidget()
        left = self._left_pane
        left.setFixedWidth(210)
        left.setStyleSheet(f"background: {_PANEL2}; border-right: 1px solid {_BORDER};")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 12, 10, 10)
        left_layout.setSpacing(8)

        self._search_lbl = QLabel(translator.get("te_search_elements"))
        self._search_lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px; background: transparent;")
        left_layout.addWidget(self._search_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText(translator.get("search"))
        self._search.textChanged.connect(self._filter_list)
        left_layout.addWidget(self._search)

        self._list = QListWidget()
        self._list.setSpacing(1)
        self._list.currentItemChanged.connect(self._on_item_selected)
        left_layout.addWidget(self._list, 1)

        root.addWidget(left)

        # ── Center panel with tabs ───────────────────────────────────────────
        self._center_pane = QWidget()
        center = self._center_pane
        center.setStyleSheet(f"background: {_PANEL};")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(12, 12, 12, 12)
        center_layout.setSpacing(8)

        # Title of selected element (outside tabs)
        self._element_lbl = QLabel("")
        self._element_lbl.setStyleSheet(
            f"color: {_ACCENT}; font-size: 14px; font-weight: 700; background: transparent;"
        )
        center_layout.addWidget(self._element_lbl)

        # Tabs
        self._center_tabs = QTabWidget()
        self._center_tabs.addTab(
            self._build_picker_tab(), translator.get("te_presets").split()[0] if False else "Color Picker"
        )
        self._center_tabs.addTab(self._build_palettes_tab(), translator.get("te_tab_palettes"))
        self._center_tabs.addTab(self._build_preview_tab(), translator.get("te_tab_preview"))
        center_layout.addWidget(self._center_tabs, 1)

        # Bottom buttons (outside tabs)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._btn_apply = QPushButton(translator.get("save_theme"))
        self._btn_apply.setStyleSheet(
            f"QPushButton {{ background: rgba(192,132,252,0.25); border: 1px solid {_ACCENT};"
            f" border-radius: 7px; color: white; padding: 6px 20px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: rgba(192,132,252,0.5); }}"
        )
        self._btn_apply.clicked.connect(self._save_and_close)

        self._btn_reset = QPushButton(translator.get("reset_theme"))
        self._btn_reset.clicked.connect(self._reset)

        self._btn_close = QPushButton(translator.get("close"))
        self._btn_close.clicked.connect(self._cancel)

        btn_row.addWidget(self._btn_reset)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_close)
        btn_row.addWidget(self._btn_apply)
        center_layout.addLayout(btn_row)

        root.addWidget(center, 1)

        # ── Right panel — tabbed (Tools + Library) ───────────────────────────
        self._right_pane = QWidget()
        right = self._right_pane
        right.setFixedWidth(230)
        right.setStyleSheet(f"background: {_PANEL2}; border-left: 1px solid {_BORDER};")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._right_tabs = QTabWidget()
        self._right_tabs.addTab(self._build_tools_tab(), translator.get("te_presets"))
        self._right_tabs.addTab(self._build_library_tab(), translator.get("te_tab_library"))
        right_layout.addWidget(self._right_tabs)

        root.addWidget(right)

    def _build_picker_tab(self) -> QWidget:
        """Color Picker tab — existing wheel/alpha/hex/contrast/history."""
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(8, 12, 8, 8)
        lay.setSpacing(10)

        # Hue/SV wheel
        wheel_row = QHBoxLayout()
        self._wheel = _HueSatWheel()
        self._wheel.color_changed.connect(self._on_wheel_changed)
        wheel_row.addStretch()
        wheel_row.addWidget(self._wheel)
        wheel_row.addStretch()
        lay.addLayout(wheel_row)

        # Alpha bar
        alpha_row = QHBoxLayout()
        alpha_lbl = QLabel("Alpha")
        alpha_lbl.setFixedWidth(42)
        self._alpha_bar = _AlphaBar()
        self._alpha_bar.alpha_changed.connect(self._on_alpha_changed)
        self._alpha_val_lbl = QLabel("100%")
        self._alpha_val_lbl.setFixedWidth(38)
        self._alpha_val_lbl.setStyleSheet(
            f"color: {_ACCENT}; font-size: 11px; font-weight: 600; background: transparent;"
        )
        alpha_row.addWidget(alpha_lbl)
        alpha_row.addWidget(self._alpha_bar, 1)
        alpha_row.addWidget(self._alpha_val_lbl)
        lay.addLayout(alpha_row)

        # Hex input + swatch
        hex_row = QHBoxLayout()
        hex_lbl = QLabel("HEX / CSS")
        hex_lbl.setFixedWidth(68)
        self._hex_input = QLineEdit()
        self._hex_input.setPlaceholderText("#rrggbb or rgba(…)")
        self._hex_input.textEdited.connect(self._on_hex_edited)
        self._swatch = QLabel()
        self._swatch.setFixedSize(36, 24)
        self._swatch.setStyleSheet("border-radius: 6px; border: 1px solid rgba(255,255,255,0.2);")
        hex_row.addWidget(hex_lbl)
        hex_row.addWidget(self._hex_input, 1)
        hex_row.addWidget(self._swatch)
        lay.addLayout(hex_row)

        # Contrast indicator
        self._contrast = _ContrastBadge("")
        lay.addWidget(self._contrast)

        # Color history
        hist_lbl = QLabel(translator.get("te_history"))
        hist_lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px; background: transparent;")
        lay.addWidget(hist_lbl)
        self._history = _ColorHistory()
        self._history.color_picked.connect(self._apply_css_string)
        lay.addWidget(self._history)

        lay.addStretch()
        return tab

    def _build_palettes_tab(self) -> QWidget:
        """Smart Palettes tab — harmony generation + image extraction."""
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(10, 12, 10, 10)
        lay.setSpacing(8)

        self._palette_base_lbl = QLabel("")
        self._palette_base_lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px; background: transparent;")
        lay.addWidget(self._palette_base_lbl)

        # Harmony type buttons
        mode_row = QHBoxLayout()
        mode_row.setSpacing(4)
        for mode_key, mode_id in [
            ("te_palette_complementary", "complementary"),
            ("te_palette_triadic", "triadic"),
            ("te_palette_analogous", "analogous"),
        ]:
            btn = QPushButton(translator.get(mode_key))
            btn.clicked.connect(lambda _, m=mode_id: self._show_palette(m))
            mode_row.addWidget(btn)
        lay.addLayout(mode_row)

        # Palette swatches
        swatch_row = QHBoxLayout()
        swatch_row.setSpacing(4)
        self._palette_swatches: list[_SwatchLabel] = []
        for _ in range(5):
            sw = _SwatchLabel()
            sw.clicked.connect(self._on_palette_swatch_clicked)
            swatch_row.addWidget(sw)
            self._palette_swatches.append(sw)
        swatch_row.addStretch()
        lay.addLayout(swatch_row)

        btn_apply_all = QPushButton(translator.get("te_apply_to_all"))
        btn_apply_all.clicked.connect(self._apply_palette_to_all)
        lay.addWidget(btn_apply_all)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {_BORDER};")
        lay.addWidget(sep)

        btn_from_image = QPushButton(translator.get("te_extract_image"))
        btn_from_image.clicked.connect(self._extract_from_image)
        lay.addWidget(btn_from_image)

        # Image palette swatches (hidden initially)
        img_row = QHBoxLayout()
        img_row.setSpacing(4)
        self._image_swatches: list[_SwatchLabel] = []
        for _ in range(6):
            sw = _SwatchLabel()
            sw.clicked.connect(self._on_palette_swatch_clicked)
            img_row.addWidget(sw)
            self._image_swatches.append(sw)
        img_row.addStretch()
        self._img_swatch_container = QWidget()
        self._img_swatch_container.setLayout(img_row)
        self._img_swatch_container.hide()
        lay.addWidget(self._img_swatch_container)

        lay.addStretch()
        return tab

    def _build_preview_tab(self) -> QWidget:
        """Preview tab — live demo of the current theme."""
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # BG toggle button
        self._btn_bg_toggle = QPushButton(translator.get("te_preview_light_bg"))
        self._btn_bg_toggle.clicked.connect(self._toggle_preview_bg)
        lay.addWidget(self._btn_bg_toggle)

        # Preview pane in scroll area
        self._preview_pane = _PreviewPane()
        scroll = QScrollArea()
        scroll.setWidget(self._preview_pane)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        lay.addWidget(scroll, 1)

        return tab

    def _build_tools_tab(self) -> QWidget:
        """Tools tab — copy/paste/eyedropper, WCAG fix, colorblind sim, border radius, invert, presets, export."""
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        def section(key: str):
            lbl = QLabel(translator.get(key))
            lbl.setStyleSheet(f"color: {_ACCENT}; font-size: 11px; font-weight: 700; background: transparent;")
            lay.addWidget(lbl)

        section("te_copy_color")

        row1 = QHBoxLayout()
        btn_copy = QPushButton(translator.get("te_copy_color"))
        btn_copy.clicked.connect(self._copy_color)
        btn_paste = QPushButton(translator.get("te_paste_color"))
        btn_paste.clicked.connect(self._paste_color)
        row1.addWidget(btn_copy)
        row1.addWidget(btn_paste)
        lay.addLayout(row1)

        btn_eye = QPushButton(translator.get("te_eyedropper"))
        btn_eye.clicked.connect(self._start_eyedropper)
        lay.addWidget(btn_eye)

        btn_wcag = QPushButton(translator.get("te_wcag_fix"))
        btn_wcag.clicked.connect(self._wcag_autofix_selected)
        lay.addWidget(btn_wcag)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet(f"color: {_BORDER};")
        lay.addWidget(sep1)

        cb_row = QHBoxLayout()
        cb_lbl = QLabel(translator.get("te_colorblind") + ":")
        cb_lbl.setFixedWidth(70)
        self._combo_colorblind = QComboBox()
        self._combo_colorblind.addItem(translator.get("te_colorblind_none"), "none")
        self._combo_colorblind.addItem(translator.get("te_colorblind_deuteranopia"), "deuteranopia")
        self._combo_colorblind.addItem(translator.get("te_colorblind_protanopia"), "protanopia")
        self._combo_colorblind.addItem(translator.get("te_colorblind_tritanopia"), "tritanopia")
        self._combo_colorblind.currentIndexChanged.connect(self._on_colorblind_changed)
        cb_row.addWidget(cb_lbl)
        cb_row.addWidget(self._combo_colorblind)
        lay.addLayout(cb_row)

        br_row = QHBoxLayout()
        br_lbl = QLabel(translator.get("te_border_radius") + ":")
        br_lbl.setFixedWidth(90)
        self._br_slider = QSlider(Qt.Orientation.Horizontal)
        self._br_slider.setRange(0, 20)
        self._br_slider.setValue(int(self.theme_data.get("border_radius", 10)))
        self._br_slider.valueChanged.connect(self._on_border_radius_changed)
        self._br_label = QLabel(f"{int(self.theme_data.get('border_radius', 10))}px")
        self._br_label.setFixedWidth(32)
        br_row.addWidget(br_lbl)
        br_row.addWidget(self._br_slider, 1)
        br_row.addWidget(self._br_label)
        lay.addLayout(br_row)

        btn_invert = QPushButton(translator.get("te_invert_theme"))
        btn_invert.clicked.connect(self._invert_theme)
        lay.addWidget(btn_invert)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {_BORDER};")
        lay.addWidget(sep2)

        self._presets_lbl = QLabel(translator.get("te_presets"))
        self._presets_lbl.setStyleSheet(
            f"color: {_ACCENT}; font-size: 11px; font-weight: 700; background: transparent;"
        )
        lay.addWidget(self._presets_lbl)

        for name in PRESETS:
            btn = QPushButton(name)
            btn.setStyleSheet(
                f"QPushButton {{ background: rgba(255,255,255,0.04); border: 1px solid {_BORDER};"
                f" border-radius: 6px; color: {_TEXT}; padding: 4px 8px; text-align: left; }}"
                f"QPushButton:hover {{ background: rgba(192,132,252,0.18); border-color: {_ACCENT}; }}"
            )
            btn.clicked.connect(lambda _, n=name: self._apply_preset(n))
            lay.addWidget(btn)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setStyleSheet(f"color: {_BORDER};")
        lay.addWidget(sep3)

        self._export_lbl = QLabel(translator.get("te_export"))
        self._export_lbl.setStyleSheet(f"color: {_ACCENT}; font-size: 11px; font-weight: 700; background: transparent;")
        lay.addWidget(self._export_lbl)

        btn_export = QPushButton(translator.get("te_export_json"))
        btn_export.clicked.connect(self._export_json)
        lay.addWidget(btn_export)

        btn_import = QPushButton(translator.get("te_import_json"))
        btn_import.clicked.connect(self._import_json)
        lay.addWidget(btn_import)

        lay.addStretch()
        return tab

    def _build_library_tab(self) -> QWidget:
        """Library tab — browse all themes with favorites."""
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(8, 10, 8, 8)
        lay.setSpacing(6)

        self._lib_search = QLineEdit()
        self._lib_search.setPlaceholderText(translator.get("te_search_themes"))
        self._lib_search.textChanged.connect(self._populate_library)
        lay.addWidget(self._lib_search)

        self._lib_list = QListWidget()
        self._lib_list.setSpacing(1)
        self._lib_list.itemDoubleClicked.connect(self._apply_library_theme)
        lay.addWidget(self._lib_list, 1)

        row = QHBoxLayout()
        btn_apply = QPushButton(translator.get("te_apply_preset"))
        btn_apply.clicked.connect(self._apply_library_theme)
        row.addWidget(btn_apply)
        lay.addLayout(row)

        return tab

    # ══════════════════════════════════════════════════════════════════════
    # Restyle panels from theme
    # ══════════════════════════════════════════════════════════════════════

    def _restyle_panels(self, theme: dict):
        accent = theme.get("accent_color", _ACCENT)
        bdr = theme.get("border_color", theme.get("button_border_color", _BORDER))
        txt = theme.get("text_area_text_color", _TEXT)
        txt_dim = theme.get("text_secondary_color", _TEXT_DIM)
        bg_win = theme.get("window_bg_color", theme.get("text_area_bg_color", _PANEL))
        panel_bg = theme.get("panel_bg_color", _PANEL2)
        btn_bg = theme.get("button_bg_color", "rgba(192,132,252,0.12)")
        btn_hov = theme.get("button_hover_bg_color", "rgba(192,132,252,0.28)")

        if hasattr(self, "_left_pane"):
            self._left_pane.setStyleSheet(f"background: {panel_bg}; border-right: 1px solid {bdr};")
        if hasattr(self, "_center_pane"):
            self._center_pane.setStyleSheet(f"background: {bg_win};")
        if hasattr(self, "_right_pane"):
            self._right_pane.setStyleSheet(f"background: {panel_bg}; border-left: 1px solid {bdr};")
        if hasattr(self, "_search_lbl"):
            self._search_lbl.setStyleSheet(f"color: {txt_dim}; font-size: 11px; background: transparent;")
        if hasattr(self, "_element_lbl"):
            self._element_lbl.setStyleSheet(
                f"color: {accent}; font-size: 14px; font-weight: 700; background: transparent;"
            )
        if hasattr(self, "_alpha_val_lbl"):
            self._alpha_val_lbl.setStyleSheet(
                f"color: {accent}; font-size: 11px; font-weight: 600; background: transparent;"
            )
        if hasattr(self, "_presets_lbl"):
            self._presets_lbl.setStyleSheet(
                f"color: {accent}; font-size: 12px; font-weight: 700; background: transparent;"
            )
        if hasattr(self, "_export_lbl"):
            self._export_lbl.setStyleSheet(
                f"color: {accent}; font-size: 12px; font-weight: 700; background: transparent;"
            )
        # Save button
        if hasattr(self, "_btn_apply"):
            self._btn_apply.setStyleSheet(
                f"QPushButton {{ background: {btn_bg}; border: 1px solid {accent};"
                f" border-radius: 7px; color: {txt}; padding: 6px 20px; font-weight: 600; }}"
                f"QPushButton:hover {{ background: {btn_hov}; }}"
            )

        # Style tab widgets
        tab_ss = (
            f"QTabWidget::pane {{ border: 1px solid {bdr}; background: {panel_bg}; }}"
            f"QTabBar::tab {{ background: {panel_bg}; color: {txt}; padding: 4px 8px; font-size: 11px; }}"
            f"QTabBar::tab:selected {{ background: {btn_bg}; color: {accent}; border-bottom: 2px solid {accent}; }}"
            f"QTabBar::tab:hover {{ background: {btn_hov}; }}"
        )
        if hasattr(self, "_center_tabs"):
            self._center_tabs.setStyleSheet(tab_ss)
        if hasattr(self, "_right_tabs"):
            self._right_tabs.setStyleSheet(tab_ss)

        # Section labels in tools tab
        for attr in ("_presets_lbl", "_export_lbl"):
            if hasattr(self, attr):
                getattr(self, attr).setStyleSheet(
                    f"color: {accent}; font-size: 11px; font-weight: 700; background: transparent;"
                )

        # Preset buttons — walk all QPushButton in right pane
        preset_ss = (
            f"QPushButton {{ background: rgba(255,255,255,0.04); border: 1px solid {bdr};"
            f" border-radius: 6px; color: {txt}; padding: 4px 8px; text-align: left; }}"
            f"QPushButton:hover {{ background: {btn_hov}; border-color: {accent}; }}"
        )
        if hasattr(self, "_right_pane"):
            from PyQt6.QtWidgets import QPushButton as _QPB

            for btn in self._right_pane.findChildren(_QPB):
                btn.setStyleSheet(preset_ss)

    # ══════════════════════════════════════════════════════════════════════
    # List population & filtering
    # ══════════════════════════════════════════════════════════════════════

    def _populate_list(self, search: str = ""):
        self._list.clear()
        search = search.lower()
        for group_key, keys in _GROUPS.items():
            group_label = translator.get(group_key)
            group_added = False
            for key in keys:
                display = self._theme_map.get(key, key)
                if search and search not in display.lower():
                    continue
                if not group_added:
                    header = QListWidgetItem(f"── {group_label} ──")
                    header.setFlags(Qt.ItemFlag.NoItemFlags)
                    header.setForeground(QColor(_ACCENT))
                    font = header.font()
                    font.setPointSize(9)
                    font.setBold(True)
                    header.setFont(font)
                    self._list.addItem(header)
                    group_added = True
                item = QListWidgetItem(f"  {display}")
                item.setData(Qt.ItemDataRole.UserRole, key)
                # Color swatch in item
                color = _parse_color(self.theme_data.get(key, "#ffffff"))
                px = QPixmap(12, 12)
                px.fill(color)
                item.setIcon(px if False else item.icon())  # skip icon to keep it clean
                self._list.addItem(item)

        # also add keys not in any group (future-proofing)
        ungrouped_added = False
        all_grouped = [k for keys in _GROUPS.values() for k in keys]
        for key in self.theme_data:
            if key not in all_grouped:
                display = self._theme_map.get(key, key)
                if search and search not in display.lower():
                    continue
                if not ungrouped_added:
                    header = QListWidgetItem("── Other ──")
                    header.setFlags(Qt.ItemFlag.NoItemFlags)
                    header.setForeground(QColor(_ACCENT))
                    self._list.addItem(header)
                    ungrouped_added = True
                item = QListWidgetItem(f"  {display}")
                item.setData(Qt.ItemDataRole.UserRole, key)
                self._list.addItem(item)

    def _filter_list(self, text: str):
        current_key = self._current_key
        self._populate_list(text)
        # try to restore selection
        if current_key:
            for i in range(self._list.count()):
                it = self._list.item(i)
                if it and it.data(Qt.ItemDataRole.UserRole) == current_key:
                    self._list.setCurrentItem(it)
                    break

    # ══════════════════════════════════════════════════════════════════════
    # Item selection → update pickers
    # ══════════════════════════════════════════════════════════════════════

    def _on_item_selected(self, current, _previous):
        if not current:
            return
        key = current.data(Qt.ItemDataRole.UserRole)
        if not key:
            return
        self._current_key = key
        display = self._theme_map.get(key, key)
        self._element_lbl.setText(display)
        if key == "border_radius":
            return  # handled by slider in Tools tab
        css = self.theme_data.get(key, "#ffffff")
        color = _parse_color(css)
        self._load_color(color, css)
        if hasattr(self, "_palette_base_lbl"):
            self._palette_base_lbl.setText(f"Base: {display}")

    def _load_color(self, color: QColor, css: str):
        self._wheel.set_color(color)
        self._alpha_bar.set_color(color)
        self._update_alpha_label(color.alphaF())
        self._updating_hex = True
        self._hex_input.setText(css)
        self._updating_hex = False
        self._update_swatch(color)
        self._update_contrast(color)

    # ══════════════════════════════════════════════════════════════════════
    # Picker event handlers
    # ══════════════════════════════════════════════════════════════════════

    def _on_wheel_changed(self, color: QColor):
        color.setAlphaF(self._alpha_bar.alpha())
        if not self._current_key:
            return
        original = self.theme_data.get(self._current_key, "#ffffff")
        css = _to_css(color, original)
        self._commit(css, color)

    def _on_alpha_changed(self, alpha: float):
        self._update_alpha_label(alpha)
        color = self._wheel.color()
        color.setAlphaF(alpha)
        self._alpha_bar.set_color(color)
        if not self._current_key:
            return
        original = self.theme_data.get(self._current_key, "#ffffff")
        # If original didn't have rgba, switch it now that alpha changed
        if alpha < 0.999:
            css = f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha:.3f})"
        else:
            css = _to_css(color, original)
        self._commit(css, color)

    def _on_hex_edited(self, text: str):
        if self._updating_hex or not self._current_key:
            return
        color = _parse_color(text)
        if color.isValid():
            self._load_color(color, text)
            self._commit(text, color)

    def _apply_css_string(self, css: str):
        """Apply a CSS string (from history or preset)."""
        if not self._current_key:
            return
        color = _parse_color(css)
        self._load_color(color, css)
        self._commit(css, color)

    def _commit(self, css: str, color: QColor):
        """Write to theme_data, update hex box, live-preview."""
        if not self._current_key:
            return
        self.theme_data[self._current_key] = css
        self._updating_hex = True
        self._hex_input.setText(css)
        self._updating_hex = False
        self._update_swatch(color)
        self._update_contrast(color)
        self._wheel.set_color(color)
        self._alpha_bar.set_color(color)
        self._update_alpha_label(color.alphaF())
        # Live preview
        if self.parent() and hasattr(self.parent(), "theme_data"):
            self.parent().theme_data = self.theme_data
            self.parent().apply_theme()
        # Update preview pane if visible
        if hasattr(self, "_center_tabs") and self._center_tabs.currentIndex() == 2:
            self._update_preview()

    # ══════════════════════════════════════════════════════════════════════
    # Visual helpers
    # ══════════════════════════════════════════════════════════════════════

    def _update_swatch(self, color: QColor):
        px = QPixmap(36, 24)
        px.fill(color)
        self._swatch.setPixmap(px)
        self._history.push(self._hex_input.text())

    def _update_contrast(self, color: QColor):
        # Use the color as foreground against current bg
        bg_css = self.theme_data.get("text_area_bg_color", "rgba(0,0,0,0.5)")
        bg = _parse_color(bg_css)
        bg.setAlpha(255)  # ignore alpha for contrast calculation
        fg = QColor(color)
        fg.setAlpha(255)
        self._contrast.update_colors(fg, bg)

    def _update_alpha_label(self, alpha: float):
        self._alpha_val_lbl.setText(f"{int(alpha * 100)}%")

    # ══════════════════════════════════════════════════════════════════════
    # Presets
    # ══════════════════════════════════════════════════════════════════════

    def _apply_preset(self, name: str):
        preset = PRESETS.get(name, {})
        self.theme_data.update(preset)
        # Reload current key picker
        if self._current_key:
            css = self.theme_data.get(self._current_key, "#ffffff")
            self._load_color(_parse_color(css), css)
        # Live preview
        if self.parent() and hasattr(self.parent(), "theme_data"):
            self.parent().theme_data = self.theme_data
            self.parent().apply_theme()

    # ══════════════════════════════════════════════════════════════════════
    # Export / Import
    # ══════════════════════════════════════════════════════════════════════

    def _export_json(self):
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            translator.get("theme_name_title"),
            translator.get("theme_name_prompt"),
        )
        if ok and name:
            path = save_theme_to_resources(name, self.theme_data)
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                translator.get("te_export_ok"),
                f"{path}",
            )

    def _import_json(self):
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self, translator.get("te_import_json"), "", "JSON (*.json)")
        if path:
            from laitoxx.core.settings.theme import load_theme

            data = load_theme(path)
            if data:
                self.theme_data.update(data)
                if self._current_key:
                    css = self.theme_data.get(self._current_key, "#ffffff")
                    self._load_color(_parse_color(css), css)
                if self.parent() and hasattr(self.parent(), "theme_data"):
                    self.parent().theme_data = self.theme_data
                    self.parent().apply_theme()

    # ══════════════════════════════════════════════════════════════════════
    # Smart Palettes
    # ══════════════════════════════════════════════════════════════════════

    def _show_palette(self, mode: str):
        if not self._current_key or self._current_key == "border_radius":
            return
        css = self.theme_data.get(self._current_key, "#ffffff")
        base = _parse_color(css)
        palette = _generate_palette(base)
        colors = palette.get(mode, [])
        self._last_palette = colors
        # Pad to 5 swatches
        for i, sw in enumerate(self._palette_swatches):
            if i < len(colors):
                sw.set_color(colors[i])
            else:
                sw.set_color(QColor("transparent"))

    def _on_palette_swatch_clicked(self, color: QColor):
        if self._current_key and self._current_key != "border_radius":
            self._apply_css_string(color.name())

    def _apply_palette_to_all(self):
        if not self._last_palette:
            return
        result = _palette_to_theme(self._last_palette, self.theme_data)
        self.theme_data.update(result)
        if self._current_key and self._current_key != "border_radius":
            css = self.theme_data.get(self._current_key, "#ffffff")
            self._load_color(_parse_color(css), css)
        if self.parent() and hasattr(self.parent(), "theme_data"):
            self.parent().theme_data = self.theme_data
            self.parent().apply_theme()
        self._update_preview()

    def _extract_from_image(self):
        try:
            from PIL import Image
        except ImportError:
            QMessageBox.warning(self, "Error", "Pillow not installed.")
            return
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self, translator.get("te_extract_image"), "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        try:
            img = Image.open(path).convert("RGB").resize((150, 150))
            quantized = img.quantize(colors=6)
            palette_rgb = quantized.getpalette()[:18]
            colors = [QColor(palette_rgb[i * 3], palette_rgb[i * 3 + 1], palette_rgb[i * 3 + 2]) for i in range(6)]
            self._last_palette = colors
            for i, sw in enumerate(self._image_swatches):
                sw.set_color(colors[i])
            self._img_swatch_container.show()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    # ══════════════════════════════════════════════════════════════════════
    # Preview
    # ══════════════════════════════════════════════════════════════════════

    def _update_preview(self):
        if hasattr(self, "_preview_pane"):
            self._preview_pane.apply_theme(self.theme_data, self._colorblind_mode, self._preview_dark)

    def _toggle_preview_bg(self):
        self._preview_dark = not self._preview_dark
        if self._preview_dark:
            self._btn_bg_toggle.setText(translator.get("te_preview_light_bg"))
        else:
            self._btn_bg_toggle.setText(translator.get("te_preview_dark_bg"))
        self._update_preview()

    # ══════════════════════════════════════════════════════════════════════
    # Tools
    # ══════════════════════════════════════════════════════════════════════

    def _copy_color(self):
        if not self._current_key or self._current_key == "border_radius":
            return
        css = self.theme_data.get(self._current_key, "#ffffff")
        color = _parse_color(css)
        QApplication.clipboard().setText(color.name())

    def _paste_color(self):
        if not self._current_key or self._current_key == "border_radius":
            return
        text = QApplication.clipboard().text().strip()
        color = _parse_color(text)
        if color.isValid():
            self._apply_css_string(text)

    def _start_eyedropper(self):
        self._eyedropper = _EyedropperOverlay()
        self._eyedropper.color_picked.connect(self._on_eyedropper_color)

    def _on_eyedropper_color(self, color: QColor):
        if self._current_key and self._current_key != "border_radius":
            self._apply_css_string(color.name())

    def _wcag_autofix_selected(self):
        if not self._current_key or self._current_key == "border_radius":
            return
        fg_css = self.theme_data.get(self._current_key, "#ffffff")
        fg = _parse_color(fg_css)
        bg_css = self.theme_data.get("text_area_bg_color", "#000000")
        bg = _parse_color(bg_css)
        bg.setAlpha(255)
        fg.setAlpha(255)
        fixed = _wcag_autofix(fg, bg)
        self._apply_css_string(fixed.name())

    def _on_border_radius_changed(self, value: int):
        self.theme_data["border_radius"] = value
        if hasattr(self, "_br_label"):
            self._br_label.setText(f"{value}px")
        if self.parent() and hasattr(self.parent(), "theme_data"):
            self.parent().theme_data = self.theme_data
            self.parent().apply_theme()
        self._update_preview()

    def _invert_theme(self):
        for key in list(self.theme_data.keys()):
            if key == "border_radius":
                continue
            css = self.theme_data.get(key, "")
            if not css:
                continue
            color = _parse_color(css)
            if not color.isValid():
                continue
            r, g, b = color.redF(), color.greenF(), color.blueF()
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            r2, g2, b2 = colorsys.hsv_to_rgb(h, s, 1.0 - v)
            inverted = QColor.fromRgbF(r2, g2, b2, color.alphaF())
            self.theme_data[key] = _to_css(inverted, css)
        if self._current_key and self._current_key != "border_radius":
            css = self.theme_data.get(self._current_key, "#ffffff")
            self._load_color(_parse_color(css), css)
        self._update_preview()
        if self.parent() and hasattr(self.parent(), "theme_data"):
            self.parent().theme_data = self.theme_data
            self.parent().apply_theme()

    def _on_colorblind_changed(self, idx: int):
        mode = self._combo_colorblind.itemData(idx) or "none"
        self._colorblind_mode = mode
        self._update_preview()

    # ══════════════════════════════════════════════════════════════════════
    # Library
    # ══════════════════════════════════════════════════════════════════════

    def _populate_library(self, search: str = ""):
        from laitoxx.core.settings.app_settings import settings
        from laitoxx.core.settings.theme import list_themes

        self._lib_list.clear()
        search = search.lower()
        themes = list_themes()
        favs = settings.favorite_themes

        for name, path in themes:
            if search and search not in name.lower():
                continue
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, path)

            # Build row widget with name + star button
            row_w = QWidget()
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(4, 2, 4, 2)
            row_lay.setSpacing(4)

            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(f"color: {_TEXT}; font-size: 12px; background: transparent;")
            row_lay.addWidget(name_lbl, 1)

            is_fav = path in favs
            star_btn = QPushButton("★" if is_fav else "☆")
            star_btn.setFixedSize(24, 24)
            star_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; color: {'#f9c74f' if is_fav else _TEXT_DIM}; font-size: 14px; }}"
                f"QPushButton:hover {{ color: #f9c74f; }}"
            )
            star_btn.clicked.connect(lambda _, p=path: self._toggle_favorite(p))
            row_lay.addWidget(star_btn)

            self._lib_list.addItem(item)
            item.setSizeHint(row_w.sizeHint())
            self._lib_list.setItemWidget(item, row_w)

    def _apply_library_theme(self):
        item = self._lib_list.currentItem()
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        from laitoxx.core.settings.theme import load_theme

        data = load_theme(path)
        if data:
            self.theme_data.update(data)
            if self._current_key and self._current_key != "border_radius":
                css = self.theme_data.get(self._current_key, "#ffffff")
                self._load_color(_parse_color(css), css)
            if self.parent() and hasattr(self.parent(), "theme_data"):
                self.parent().theme_data = self.theme_data
                self.parent().apply_theme()
            self._update_preview()
            # Update border radius slider
            if hasattr(self, "_br_slider"):
                self._br_slider.setValue(int(self.theme_data.get("border_radius", 10)))

    def _toggle_favorite(self, path: str):
        from laitoxx.core.settings.app_settings import settings

        favs = list(settings.favorite_themes)
        if path in favs:
            favs.remove(path)
        else:
            favs.append(path)
        settings.favorite_themes = favs
        self._populate_library(self._lib_search.text())

    # ══════════════════════════════════════════════════════════════════════
    # Dialog close actions
    # ══════════════════════════════════════════════════════════════════════

    def _reset(self):
        if self.parent() and hasattr(self.parent(), "load_initial_theme"):
            self.parent().load_initial_theme(use_last_saved=False)
            self.theme_data = self.parent().theme_data.copy()
        else:
            self.theme_data = self.original_theme.copy()
        if self._current_key:
            css = self.theme_data.get(self._current_key, "#ffffff")
            self._load_color(_parse_color(css), css)
        if self.parent() and hasattr(self.parent(), "apply_theme"):
            self.parent().apply_theme()

    def _save_and_close(self):
        self.accept()

    def _cancel(self):
        # Restore original theme
        if self.parent() and hasattr(self.parent(), "theme_data"):
            self.parent().theme_data = self.original_theme
            self.parent().apply_theme()
        self.reject()

    def get_theme_data(self) -> dict:
        return self.theme_data
