"""
theme_editor.py - Modern Theme Editor for LAITOXX.

Layout (3-panel monolithic window):
  Left: searchable element list grouped by category
  Center: custom color picker (hue wheel + SV square + hex input + alpha slider)
  Right: preset themes, contrast indicator, color history, glow/glass settings
"""

from __future__ import annotations

import colorsys

from PyQt6.QtCore import (
    Qt,
    QTimer,
)
from PyQt6.QtGui import (
    QColor,
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

from laitoxx.core.localization.i18n import translator
from laitoxx.core.settings.theme import DEFAULT_THEME, save_theme_to_resources
from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme
from laitoxx.interfaces.gui.theme_widgets import (
    _AlphaBar,
    _build_dialog_ss,
    _ColorHistory,
    _ContrastBadge,
    _EyedropperOverlay,
    _generate_palette,
    _HueSatWheel,
    _palette_to_theme,
    _parse_color,
    _PreviewPane,
    _SwatchLabel,
    _to_css,
    _wcag_autofix,
)

_BG = "rgba(10, 7, 22, 0.97)"

_PANEL = "#0f0c1e"

_PANEL2 = "#130f26"

_BORDER = "rgba(192, 132, 252, 0.25)"

_ACCENT = "#c084fc"

_ACCENT2 = "#f472b6"

_TEXT = "#f1f0ff"

_TEXT_DIM = "#6b6580"

_NON_COLOR_KEYS = {"style_mode", "font_family", "font_size", "radius_delta", "edge_width", "edge_style", "material"}

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
    "te_group_graph": [
        "graph_canvas_bg_color",
        "graph_node_border_color",
        "graph_node_text_color",
        "graph_node_ip_color",
        "graph_node_domain_color",
        "graph_node_url_color",
        "graph_node_asn_color",
        "graph_node_prefix_color",
        "graph_node_service_color",
        "graph_node_service_group_color",
        "graph_node_cpe_color",
        "graph_node_cve_color",
        "graph_node_organization_color",
        "graph_node_dns_record_color",
        "graph_edge_high_color",
        "graph_edge_medium_color",
        "graph_edge_low_color",
    ],
}

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

__all__ = [
    "DEFAULT_THEME",
    "PRESETS",
    "QApplication",
    "QColor",
    "QComboBox",
    "QDialog",
    "QFrame",
    "QHBoxLayout",
    "QLabel",
    "QLineEdit",
    "QListWidget",
    "QListWidgetItem",
    "QMessageBox",
    "QPixmap",
    "QPushButton",
    "QScrollArea",
    "QSlider",
    "QTabWidget",
    "QTimer",
    "QVBoxLayout",
    "QWidget",
    "Qt",
    "_ACCENT",
    "_ACCENT2",
    "_AlphaBar",
    "_BG",
    "_BORDER",
    "_ColorHistory",
    "_ContrastBadge",
    "_EyedropperOverlay",
    "_GROUPS",
    "_HueSatWheel",
    "_NON_COLOR_KEYS",
    "_PANEL",
    "_PANEL2",
    "_PreviewPane",
    "_SwatchLabel",
    "_TEXT",
    "_TEXT_DIM",
    "_build_dialog_ss",
    "_generate_palette",
    "_palette_to_theme",
    "_parse_color",
    "_to_css",
    "_wcag_autofix",
    "build_workspace_qss",
    "colorsys",
    "resolved_theme",
    "save_theme_to_resources",
    "translator",
]
