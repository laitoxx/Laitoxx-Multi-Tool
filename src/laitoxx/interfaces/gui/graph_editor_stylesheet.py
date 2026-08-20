"""Focused GraphEditorWindow responsibility mixin."""
# ruff: noqa: F405

from __future__ import annotations

from laitoxx.interfaces.gui.design_system import build_workspace_qss

from .graph_ui_style import *  # noqa: F403


class GraphEditorStylesheetMixin:
    def _apply_global_style(self):
        td = self._theme
        bg_color = td.get("window_bg_color", td.get("text_area_bg_color", "rgba(13,11,26,0.95)"))
        text_color = td.get("text_area_text_color", _TEXT_PRI)
        btn_bg = td.get("button_bg_color", "rgba(124,58,237,0.5)")
        btn_hover = td.get("button_hover_bg_color", "rgba(139,92,246,0.7)")
        btn_border = td.get("border_color", td.get("button_border_color", _BORDER))
        btn_text = td.get("button_text_color", "white")
        sb_bg = td.get("panel_bg_color", td.get("sidebar_bg_color", "rgba(13,11,26,0.95)"))
        accent = td.get("accent_color", _ACCENT)

        # Update module-level tokens so newly created widgets pick them up
        import laitoxx.interfaces.gui.graph_editor as _self_mod

        _self_mod._ACCENT = accent
        _self_mod._ACCENT2 = td.get("text_secondary_color", accent)
        _self_mod._ACCENT_DIM = td.get("accent_dim_color", _ACCENT_DIM)
        _self_mod._BORDER = btn_border
        _self_mod._BORDER_FOCUS = accent
        _self_mod._TEXT_PRI = text_color
        _self_mod._TEXT_SEC = td.get("text_secondary_color", _TEXT_SEC)
        _self_mod._TEXT_DIM = td.get("text_secondary_color", _TEXT_SEC)
        _self_mod._BG_DEEP = bg_color

        self.setStyleSheet(f"""
            QDialog {{
                background: {bg_color};
                color: {text_color};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QFrame#graphAnalysisBar {{
                background: {sb_bg};
                border: 1px solid {btn_border};
                border-radius: 9px;
            }}
            QLabel {{
                color: {text_color};
                background: transparent;
                font-size: 12px;
            }}
            QPushButton {{
                background: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 7px;
                color: {btn_text};
                padding: 4px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {btn_hover};
            }}
            QLineEdit, QComboBox {{
                background: rgba(255,255,255,0.04);
                border: 1px solid {btn_border};
                border-radius: 7px;
                color: {text_color};
                padding: 4px 8px;
                font-size: 12px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {accent};
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background: {sb_bg};
                color: {text_color};
                selection-background-color: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 6px;
            }}
            QScrollBar:vertical {{
                background: transparent; width: 6px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {btn_border};
                border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {btn_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QMenu {{
                background: {sb_bg};
                border: 1px solid {btn_border};
                border-radius: 8px;
                color: {text_color};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 5px 18px;
                border-radius: 5px;
            }}
            QMenu::item:selected {{
                background: {btn_hover};
                color: white;
            }}
            QMessageBox {{
                background: {bg_color};
                color: {text_color};
            }}
            QMessageBox QPushButton {{
                background: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 6px;
                color: {btn_text};
                padding: 5px 14px;
                min-width: 60px;
            }}
            QMessageBox QPushButton:hover {{
                background: {btn_hover};
            }}
            QSplitter::handle {{
                background: {btn_border};
            }}
        """)
        self.setStyleSheet(self.styleSheet() + build_workspace_qss(td))
