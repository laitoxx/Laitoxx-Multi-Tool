"""Focused graph editor widgets and dialogs."""
# ruff: noqa: F405

from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QColorDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QWidget,
)

from .graph_ui_style import *  # noqa: F403


class GradientButton(QPushButton):
    """Pill-shaped button with gradient background and glow on hover."""

    def __init__(self, text: str, colors: tuple = _BTN_FILE, parent=None):
        super().__init__(text, parent)
        c_from, c_to, c_border = colors
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {c_from}, stop:1 {c_to});
                border: 1px solid {c_border};
                border-radius: 8px;
                color: {_TEXT_PRI};
                font-size: 12px;
                font-weight: 600;
                padding: 0 14px;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {c_to}, stop:1 {c_from});
                border-color: {_ACCENT};
            }}
            QPushButton:pressed {{
                background: {c_from};
                padding-top: 2px;
            }}
            QPushButton:disabled {{
                background: rgba(80,70,100,0.3);
                border-color: rgba(255,255,255,0.08);
                color: {_TEXT_DIM};
            }}
        """)


class IconButton(QPushButton):
    """Small square icon-style button."""

    def __init__(self, text: str, tooltip: str = "", parent=None):
        super().__init__(text, parent)
        self.setToolTip(tooltip)
        self.setFixedSize(32, 30)
        self.setStyleSheet(f"""
            QPushButton {{
                background: rgba(192,132,252,0.1);
                border: 1px solid {_BORDER};
                border-radius: 7px;
                color: {_TEXT_PRI};
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: rgba(192,132,252,0.25);
                border-color: {_ACCENT};
            }}
            QPushButton:pressed {{ background: rgba(192,132,252,0.4); }}
        """)


# ===========================================================================
# Section label (coloured title bar)
# ===========================================================================


class SectionLabel(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(26)
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        self.setFont(font)
        self.setStyleSheet(f"""
            QLabel {{
                color: {_ACCENT};
                background: rgba(192,132,252,0.08);
                border-bottom: 1px solid {_BORDER};
                padding: 2px 8px;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
        """)


# ===========================================================================
# Glass panel (QFrame with variable alpha)
# ===========================================================================


class GlassPanel(QFrame):
    def __init__(self, alpha: float = 0.55, parent=None):
        super().__init__(parent)
        self._alpha = alpha
        self._border_color = _BORDER
        self._bg_base = "15, 10, 30"
        self._refresh_style()

    def set_alpha(self, alpha: float):
        self._alpha = max(0.05, min(1.0, alpha))
        self._refresh_style()

    def set_theme(self, border_color: str, bg_color: str = ""):
        """Update border and optional background tint from theme data."""
        self._border_color = border_color
        if bg_color:
            # Extract RGB from rgba(...) or use hex directly
            import re as _re

            m = _re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", bg_color)
            if m:
                self._bg_base = f"{m[1]}, {m[2]}, {m[3]}"
        self._refresh_style()

    def _refresh_style(self):
        a = self._alpha
        bg = f"rgba({self._bg_base}, {a:.2f})"
        self.setStyleSheet(f"""
            GlassPanel {{
                background: {bg};
                border: 1px solid {self._border_color};
                border-radius: 12px;
            }}
        """)


# ===========================================================================
# Opacity slider widget
# ===========================================================================


class OpacitySlider(QWidget):
    value_changed = pyqtSignal(float)  # 0.0 - 1.0

    def __init__(self, label: str = "Opacity", initial: float = 0.55, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QLabel(label)
        lbl.setFixedWidth(58)
        lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px;")
        layout.addWidget(lbl)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(5, 100)
        self._slider.setValue(int(initial * 100))
        self._slider.setFixedHeight(18)
        self._slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: rgba(255,255,255,0.1);
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                width: 14px; height: 14px;
                margin: -5px 0;
                border-radius: 7px;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {_ACCENT}, stop:1 {_ACCENT2});
                border: none;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {_ACCENT_DIM}, stop:1 {_ACCENT});
                border-radius: 2px;
            }}
        """)
        self._slider.valueChanged.connect(self._on_change)
        layout.addWidget(self._slider, 1)

        self._val_lbl = QLabel(f"{int(initial * 100)}%")
        self._val_lbl.setFixedWidth(36)
        self._val_lbl.setStyleSheet(f"color: {_ACCENT}; font-size: 11px; font-weight: 600;")
        layout.addWidget(self._val_lbl)

    def _on_change(self, v: int):
        self._val_lbl.setText(f"{v}%")
        self.value_changed.emit(v / 100.0)

    def get_value(self) -> float:
        return self._slider.value() / 100.0


# ===========================================================================
# Color picker button
# ===========================================================================


def _color_button(color_str: str, on_pick) -> QPushButton:
    btn = QPushButton()
    btn.setFixedSize(26, 22)
    btn.setToolTip("Pick color")
    _apply_color_btn_style(btn, color_str)
    btn.clicked.connect(lambda: _pick_color(btn, on_pick))
    return btn


def _apply_color_btn_style(btn: QPushButton, color_str: str) -> None:
    btn.setStyleSheet(f"background-color: {color_str}; border: 1px solid rgba(255,255,255,0.4); border-radius: 5px;")
    btn.setProperty("_color", color_str)


def _pick_color(btn: QPushButton, callback) -> None:
    current = btn.property("_color") or "#ffffff"
    color = QColorDialog.getColor(QColor(current))
    if color.isValid():
        _apply_color_btn_style(btn, color.name())
        callback(color.name())
