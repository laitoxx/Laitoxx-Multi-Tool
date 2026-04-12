"""
_style_provider.py — Style/theme helpers for ImageSearchWindow.

Centralises all QSS generation so the main window class stays free of
inline style strings.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QPushButton

# ---------------------------------------------------------------------------
# Design tokens (fallback values used when no theme is loaded)
# ---------------------------------------------------------------------------
ACCENT      = "#c084fc"
ACCENT2     = "#f472b6"
ACCENT_DIM  = "#7c3aed"
BG_DEEP     = "#0d0d1a"
BG_CARD     = "#13131f"
BG_PANEL    = "#111120"
TEXT_PRI    = "#f1f0ff"
TEXT_SEC    = "#a99fc0"
TEXT_DIM    = "#6b6580"
BORDER      = "rgba(192, 132, 252, 0.20)"
GREEN       = "#00b894"
RED         = "#e74c3c"
ORANGE      = "#f39c12"


# ---------------------------------------------------------------------------
# Base stylesheet
# ---------------------------------------------------------------------------

def build_base_style(
    accent: str,
    accent_dim: str,
    bg_deep: str,
    bg_card: str,
    text_pri: str,
    border: str,
) -> str:
    return f"""
QDialog, QWidget {{
    background: {bg_deep};
    color: {text_pri};
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}}
QScrollBar:vertical {{
    background: {bg_deep};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {accent_dim};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {bg_deep};
    height: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {accent_dim};
    border-radius: 3px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QSlider::groove:horizontal {{
    background: rgba(192,132,252,0.15);
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {accent};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {accent};
    border-radius: 2px;
}}
QLineEdit {{
    background: rgba(255,255,255,0.04);
    border: 1px solid {border};
    border-radius: 6px;
    padding: 4px 8px;
    color: {text_pri};
}}
QTextEdit {{
    background: {bg_card};
    border: 1px solid {border};
    border-radius: 8px;
    color: {text_pri};
    padding: 8px;
}}
QProgressBar {{
    background: rgba(255,255,255,0.06);
    border: 1px solid {border};
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {accent_dim}, stop:1 {accent});
    border-radius: 4px;
}}
"""


# ---------------------------------------------------------------------------
# Button factory
# ---------------------------------------------------------------------------

def make_button(
    text: str,
    *,
    accent: bool = False,
    ghost: bool = False,
    danger: bool = False,
    ac: str = ACCENT,
    ac2: str = ACCENT2,
    acd: str = ACCENT_DIM,
    ts: str = TEXT_SEC,
    bd: str = BORDER,
    rd: str = RED,
) -> QPushButton:
    """Фабрика стилизованных кнопок."""
    from PyQt6.QtCore import Qt

    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)

    if accent:
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {acd}, stop:1 {ac});
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ac}, stop:1 {ac2});
            }}
            QPushButton:pressed {{ opacity: 0.8; }}
        """)
    elif ghost:
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {ts};
                border: 1px solid {bd};
                border-radius: 6px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                border-color: {ac};
                color: {ac};
            }}
        """)
    elif danger:
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(231,76,60,0.15);
                color: {rd};
                border: 1px solid rgba(231,76,60,0.35);
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background: rgba(231,76,60,0.30);
            }}
        """)
    return btn


# ---------------------------------------------------------------------------
# Misc widget style helpers
# ---------------------------------------------------------------------------

def section_label_style(text_dim: str) -> str:
    return f"""
        color: {text_dim};
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        padding: 8px 0 4px 0;
    """


def hline_style(border: str) -> str:
    return f"background: {border}; max-height: 1px;"


def tool_btn_style(active: bool, accent: str, text_pri: str, text_dim: str) -> str:
    if active:
        return f"""
            QPushButton {{
                background: rgba(192,132,252,0.25);
                border-left: 3px solid {accent};
                border-top: none; border-right: none; border-bottom: none;
                border-radius: 0;
                font-size: 18px;
                color: {text_pri};
            }}
        """
    return f"""
        QPushButton {{
            background: transparent;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            color: {text_dim};
        }}
        QPushButton:hover {{
            background: rgba(192,132,252,0.12);
            color: {text_pri};
        }}
    """


def engine_pill_style(checked: bool, accent: str, text_sec: str, border: str, text_pri: str) -> str:
    if checked:
        return f"""
            QPushButton {{
                background: rgba(192,132,252,0.22);
                color: {accent};
                border: 1px solid rgba(192,132,252,0.55);
                border-radius: 16px;
                padding: 5px 10px;
                font-size: 12px;
                text-align: left;
            }}
        """
    return f"""
        QPushButton {{
            background: rgba(255,255,255,0.04);
            color: {text_sec};
            border: 1px solid {border};
            border-radius: 16px;
            padding: 5px 10px;
            font-size: 12px;
            text-align: left;
        }}
        QPushButton:hover {{
            border-color: {accent};
            color: {text_pri};
        }}
    """
