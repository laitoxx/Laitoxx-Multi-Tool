"""Shared semantic QSS for the Laitoxx desktop workspace."""

from __future__ import annotations

STYLE_MODES = {
    "glass": "Glass",
    "metallic": "Metallic",
    "glitch": "Glitch",
    "solid": "Solid",
}
from .theme_resolution import resolved_theme as resolved_theme


def build_workspace_qss(theme: dict | None = None) -> str:
    t = resolved_theme(theme)
    radius = int(t.get("border_radius", 10))
    radius = max(2, radius + int(t.get("radius_delta", 0)))
    small = max(2, radius - 4)
    edge_width = int(t.get("edge_width", 1))
    edge_style = t.get("edge_style", "solid")
    material = t.get("material", "glass")
    font_family = str(t.get("font_family") or "Segoe UI").replace('"', "")
    code_font_family = str(t.get("code_font_family") or "Cascadia Mono").replace('"', "")
    font_size = max(10, min(18, int(t.get("font_size", 13))))
    panel_bg = t["surface_glass_color"]
    content_bg = t["surface_base_color"]
    button_bg = t["surface_raised_color"]
    input_bg = t["surface_input_color"]
    panel_border = t["border_subtle_color"]
    button_border = "transparent"
    card_border = t["border_subtle_color"]
    nav_checked_border = f"border-left: 3px solid {t['accent_color']};"
    mode_extra = ""
    if material == "metallic":
        panel_bg = (
            f"qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {t['surface_raised_color']}, "
            f"stop:0.46 {t['surface_glass_color']}, stop:0.5 {t['border_strong_color']}, "
            f"stop:0.54 {t['surface_glass_color']}, stop:1 {t['surface_base_color']})"
        )
        button_bg = (
            f"qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {t['surface_hover_color']}, "
            f"stop:0.48 {t['surface_raised_color']}, stop:1 {t['surface_pressed_color']})"
        )
        panel_border = t["border_strong_color"]
        button_border = t["border_strong_color"]
    elif material == "glitch":
        panel_border = t["accent_color"]
        card_border = t["accent_dim_color"]
        button_border = t["border_strong_color"]
        nav_checked_border = (
            f"border-left: 4px solid {t['accent_color']}; border-right: 2px solid {t['accent_dim_color']};"
        )
        mode_extra = f"""
QWidget#TopBar {{ border-left: 4px solid {t["accent_color"]}; border-right: 2px solid {t["accent_dim_color"]}; }}
QWidget#ContentSurface {{ border-top: 2px solid {t["accent_color"]}; border-bottom: 2px solid {t["accent_dim_color"]}; }}
QPushButton:hover {{ border-left: 3px solid {t["accent_color"]}; border-right: 2px solid {t["accent_dim_color"]}; }}
QLineEdit:focus, QComboBox:focus {{ border-left: 3px solid {t["accent_color"]}; border-right: 2px solid {t["accent_dim_color"]}; }}
"""
    elif material == "solid":
        panel_bg = t["surface_raised_color"]
        content_bg = t["surface_work_color"]
        panel_border = t["border_strong_color"]
        button_border = t["border_subtle_color"]
    return f"""
QWidget {{
    color: {t["text_primary_color"]};
    font-family: "{font_family}", "Segoe UI", sans-serif;
    font-size: {font_size}px;
}}
QWidget#WorkspaceRoot {{ background: transparent; }}
QWidget#TopBar, QWidget#Sidebar, QWidget#ActivityPanel, QFrame#PageHeader {{
    background: {panel_bg};
    border: {edge_width}px {edge_style} {panel_border};
    border-radius: {radius + 4}px;
}}
QWidget#ContentSurface {{
    background: {content_bg};
    border: {edge_width}px {edge_style} {panel_border};
    border-radius: {radius + 4}px;
}}
QFrame#PanelSurface, QFrame#ToolPanel {{
    background: {panel_bg}; border: {edge_width}px {edge_style} {panel_border};
    border-radius: {radius}px;
}}
QFrame#WorkSurface, QFrame#EmptyState, QWidget#WorkSurface {{
    background: {t["surface_work_color"]}; border: 1px solid {t["border_subtle_color"]};
    border-radius: {radius}px;
}}
QLabel#Brand {{ font-size: 20px; font-weight: 700; color: {t["text_primary_color"]}; }}
QLabel#PageTitle {{ font-size: 28px; font-weight: 700; color: {t["text_primary_color"]}; }}
QLabel#PageSubtitle, QLabel#Muted {{ color: {t["text_secondary_color"]}; }}
QLabel#PanelTitle {{ font-size: 15px; font-weight: 650; color: {t["text_primary_color"]}; }}
QLabel#EmptyTitle {{ font-size: 20px; font-weight: 700; color: {t["text_primary_color"]}; }}
QLabel#CodeText {{ font-family: "{code_font_family}", Consolas, monospace; }}
QLabel#SectionLabel {{
    color: {t["text_muted_color"]}; font-size: 11px; font-weight: 700;
    padding: 8px 4px 3px 4px;
}}
QLabel#StatusDot {{ color: {t["success_color"]}; font-size: 12px; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    min-height: 30px; background: {input_bg};
    border: {edge_width}px {edge_style} {panel_border}; border-radius: {small}px;
    padding: 0 12px; selection-background-color: {t["accent_color"]};
}}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {t["accent_color"]}; }}
QPushButton {{
    min-height: 30px; background: {button_bg};
    border: {edge_width}px {edge_style} {button_border}; border-radius: {small}px;
    padding: 0 13px; font-weight: 600;
}}
QPushButton:hover {{ background: {t["surface_hover_color"]}; }}
QPushButton:pressed {{ background: {t["surface_pressed_color"]}; }}
QPushButton:disabled {{ color: {t["text_muted_color"]}; background: {t["surface_input_color"]}; }}
QPushButton[variant="primary"] {{ background: {t["accent_color"]}; color: {t["accent_text_color"]}; }}
QPushButton[variant="primary"]:hover {{ background: {t["accent_hover_color"]}; }}
QPushButton[variant="ghost"] {{ background: transparent; color: {t["text_secondary_color"]}; }}
QPushButton[variant="ghost"]:hover {{ background: {t["surface_hover_color"]}; color: {t["text_primary_color"]}; }}
QPushButton[nav="true"] {{ text-align: left; padding-left: 12px; }}
QPushButton[nav="true"]:checked {{
    background: {t["accent_soft_color"]}; color: {t["text_primary_color"]};
    {nav_checked_border}
}}
QPushButton[toolCard="true"] {{
    min-height: 40px; text-align: left; padding: 5px 10px;
    background: {button_bg}; border: {edge_width}px {edge_style} {card_border};
    border-radius: {radius}px; font-size: {font_size}px;
}}
QPushButton[toolCard="true"]:hover {{
    background: {t["surface_hover_color"]}; border-color: {t["border_strong_color"]};
}}
QPlainTextEdit, QTextEdit, QTableView, QTreeView, QListView {{
    background: {t["surface_work_color"]}; border: 1px solid {t["border_subtle_color"]};
    border-radius: {radius}px; padding: 8px; selection-background-color: {t["accent_soft_color"]};
}}
QAbstractItemView {{
    background: {t["surface_work_color"]}; color: {t["text_primary_color"]};
    alternate-background-color: {t["surface_input_color"]};
    border: 1px solid {t["border_subtle_color"]};
    selection-background-color: {t["accent_soft_color"]};
    selection-color: {t["text_primary_color"]};
    outline: none;
}}
QHeaderView {{ background: {t["surface_raised_color"]}; }}
QHeaderView::section {{
    background: {t["surface_raised_color"]}; color: {t["text_primary_color"]};
    border: none; border-right: 1px solid {t["border_subtle_color"]};
    border-bottom: 1px solid {t["border_strong_color"]}; padding: 7px 10px;
    font-weight: 600;
}}
QTableCornerButton::section {{
    background: {t["surface_raised_color"]}; border: none;
    border-right: 1px solid {t["border_subtle_color"]};
    border-bottom: 1px solid {t["border_strong_color"]};
}}
QTableView, QTableWidget {{
    gridline-color: {t["border_subtle_color"]};
    alternate-background-color: {t["surface_input_color"]};
}}
QTabWidget::pane {{
    background: {t["surface_work_color"]};
    border: 1px solid {t["border_subtle_color"]}; border-radius: {radius}px;
    top: -1px;
}}
QTabBar::tab {{
    background: {t["surface_input_color"]}; color: {t["text_secondary_color"]};
    border: 1px solid {t["border_subtle_color"]}; border-bottom: none;
    padding: 7px 12px; min-height: 22px;
}}
QTabBar::tab:selected {{
    background: {t["surface_raised_color"]}; color: {t["text_primary_color"]};
    border-bottom: 2px solid {t["accent_color"]};
}}
QTabBar::tab:hover:!selected {{ background: {t["surface_hover_color"]}; color: {t["text_primary_color"]}; }}
QTabBar QToolButton, QToolButton {{
    background: {t["surface_raised_color"]}; color: {t["text_primary_color"]};
    border: 1px solid {t["border_subtle_color"]}; border-radius: {small}px;
    min-width: 24px; min-height: 24px;
}}
QTabBar QToolButton:hover, QToolButton:hover {{ background: {t["surface_hover_color"]}; }}
QGroupBox {{
    background: {t["surface_raised_color"]}; border: 1px solid {t["border_subtle_color"]};
    border-radius: {radius}px; margin-top: 12px; padding: 12px 8px 8px 8px;
}}
QGroupBox::title {{ color: {t["text_secondary_color"]}; subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
QStackedWidget, QScrollArea > QWidget > QWidget {{ background: transparent; }}
QMenu {{
    background: {t["surface_overlay_color"]}; color: {t["text_primary_color"]};
    border: 1px solid {t["border_strong_color"]}; padding: 4px;
}}
QMenu::item {{ padding: 6px 18px; border-radius: {small}px; }}
QMenu::item:selected {{ background: {t["accent_soft_color"]}; color: {t["text_primary_color"]}; }}
QPlainTextEdit {{ font-family: "{code_font_family}", Consolas, monospace; font-size: 13px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 3px; }}
QScrollBar::handle:vertical {{ background: {t["border_strong_color"]}; min-height: 28px; border-radius: 4px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QSplitter::handle {{ background: transparent; width: 8px; }}
QToolTip {{ background: {t["surface_overlay_color"]}; color: {t["text_primary_color"]};
    border: 1px solid {t["border_strong_color"]}; padding: 6px; }}
{mode_extra}
"""
