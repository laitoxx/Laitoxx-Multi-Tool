"""Focused GraphEditorWindow responsibility mixin."""
# ruff: noqa: F405

from __future__ import annotations

from laitoxx.interfaces.gui.design_system import resolved_theme
from laitoxx.interfaces.gui.graph_controls import GradientButton, IconButton, SectionLabel
from laitoxx.interfaces.gui.graph_properties import _PropPanel

from .graph_ui_style import *  # noqa: F403


class GraphEditorThemeMixin:
    def _on_panel_opacity(self, value: float):
        self._panel_alpha = value
        for panel in (self._left_panel, self._center_panel, self._right_panel):
            panel.set_alpha(value)

    # ------------------------------------------------------------------
    # Global stylesheet
    # ------------------------------------------------------------------

    def update_theme(self, theme_data: dict):
        """Called from MainWindow when user changes the theme."""
        theme_data = resolved_theme(theme_data)
        self._theme = theme_data
        border = theme_data.get("border_color", theme_data.get("button_border_color", _BORDER))
        bg = theme_data.get("panel_bg_color", theme_data.get("window_bg_color", ""))
        for panel in (self._left_panel, self._center_panel, self._right_panel):
            panel.set_theme(border, bg)
        self._apply_global_style()
        self._restyle_widgets(theme_data)

    def _restyle_widgets(self, td: dict):
        """Re-apply inline styles on widgets that were styled at build time."""
        accent = td.get("accent_color", _ACCENT)
        accent2 = td.get("accent_color", _ACCENT2)  # edge count uses second accent
        dim = td.get("accent_dim_color", _ACCENT_DIM)
        bdr = td.get("border_color", td.get("button_border_color", _BORDER))
        txt_pri = td.get("text_area_text_color", _TEXT_PRI)
        txt_sec = td.get("text_secondary_color", _TEXT_SEC)
        btn_bg = td.get("button_bg_color", "rgba(124,58,237,0.5)")
        btn_hov = td.get("button_hover_bg_color", "rgba(139,92,246,0.7)")
        panel_bg = td.get("panel_bg_color", td.get("window_bg_color", ""))

        # Status bar labels
        if hasattr(self, "_status"):
            self._status.setStyleSheet(f"color: {txt_sec}; font-size: 11px;")
        if hasattr(self, "_node_count"):
            self._node_count.setStyleSheet(f"color: {accent}; font-size: 11px; font-weight: 600;")
        if hasattr(self, "_edge_count"):
            self._edge_count.setStyleSheet(f"color: {accent2}; font-size: 11px; font-weight: 600;")

        # Accent separator line
        if hasattr(self, "_accent_line"):
            self._accent_line.setStyleSheet(
                f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                f"stop:0 transparent, stop:0.3 {accent}, stop:0.7 {accent2}, stop:1 transparent);"
                f" border: none;"
            )

        # Splitter handles
        if hasattr(self, "_main_splitter"):
            self._main_splitter.setStyleSheet(f"QSplitter::handle {{ background: {bdr}; }}")

        # Opacity slider
        if hasattr(self, "_opacity_panels"):
            self._opacity_panels._slider.setStyleSheet(f"""
                QSlider::groove:horizontal {{
                    height: 4px;
                    background: rgba(255,255,255,0.1);
                    border-radius: 2px;
                }}
                QSlider::handle:horizontal {{
                    width: 14px; height: 14px;
                    margin: -5px 0;
                    border-radius: 7px;
                    background: {accent};
                    border: none;
                }}
                QSlider::sub-page:horizontal {{
                    background: {dim};
                    border-radius: 2px;
                }}
            """)

        # All nested QSplitter handles
        from PyQt6.QtWidgets import QFrame as _QFrame
        from PyQt6.QtWidgets import QSplitter as _QSplitter

        for spl in self.findChildren(_QSplitter):
            spl.setStyleSheet(f"QSplitter::handle {{ background: {bdr}; }}")

        # Vertical separator lines (VLine QFrames with background: border color)
        for frm in self.findChildren(_QFrame):
            ss = frm.styleSheet()
            if (
                ss
                and "background:" in ss
                and "border: none" in ss
                and frm.frameShape() in (_QFrame.Shape.VLine, _QFrame.Shape.HLine)
            ):
                frm.setStyleSheet(f"background: {bdr}; border: none;")

        # GradientButton colours follow theme via btn_bg/btn_hov - update all GradientButtons
        # by overriding their stylesheet with theme-derived colours
        grad_ss = f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {btn_bg}, stop:1 {btn_hov});
                border: 1px solid {dim};
                border-radius: 8px;
                color: {txt_pri};
                font-size: 12px;
                font-weight: 600;
                padding: 0 14px;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {btn_hov}, stop:1 {btn_bg});
                border-color: {accent};
            }}
            QPushButton:pressed {{ background: {btn_bg}; padding-top: 2px; }}
            QPushButton:disabled {{
                background: rgba(80,70,100,0.3);
                border-color: rgba(255,255,255,0.08);
                color: {_TEXT_DIM};
            }}
        """
        # Walk all GradientButton children and restyle them
        for child in self.findChildren(GradientButton):
            child.setStyleSheet(grad_ss)

        # SectionLabel children - restyle
        sect_ss = f"""
            QLabel {{
                color: {accent};
                background: {btn_bg};
                border-bottom: 1px solid {bdr};
                padding: 2px 8px;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
        """
        for child in self.findChildren(SectionLabel):
            child.setStyleSheet(sect_ss)

        # IconButton children
        icon_ss = f"""
            QPushButton {{
                background: {btn_bg};
                border: 1px solid {bdr};
                border-radius: 7px;
                color: {txt_pri};
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {btn_hov};
                border-color: {accent};
            }}
            QPushButton:pressed {{ background: {btn_hov}; }}
        """
        for child in self.findChildren(IconButton):
            child.setStyleSheet(icon_ss)

        # _PropPanel (NodePropertiesPanel / EdgePropertiesPanel)
        for prop_panel in (
            getattr(self, "_node_props", None),
            getattr(self, "_edge_props", None),
        ):
            if prop_panel and isinstance(prop_panel, _PropPanel):
                prop_panel.apply_theme(accent, bdr, txt_sec, _TEXT_DIM)
                prop_panel.set_theme(bdr, panel_bg)

        # Node / Edge list widgets
        new_list_ss = self._list_style(accent, txt_pri, bdr)
        if hasattr(self, "_nodes_list"):
            self._nodes_list.setStyleSheet(new_list_ss)
        if hasattr(self, "_edges_list"):
            self._edges_list.setStyleSheet(new_list_ss)

        # Raw Mermaid code display
        if hasattr(self, "_raw_code"):
            self._raw_code.setStyleSheet(
                f"font-family: 'Cascadia Code', Consolas, monospace; font-size: 11px;"
                f" background: rgba(0,0,0,0.45); color: {txt_sec};"
                f" border: 1px solid {bdr}; border-radius: 8px; padding: 6px;"
            )

        # Update MermaidView theme and re-render graph with new colors
        if hasattr(self, "_mermaid_view"):
            self._mermaid_view.apply_theme(td)
            self._mermaid_view.render_graph(self._graph)

        # Re-colour all plain QLabel children that have inline colour styles.
        # We distinguish role by inspecting current style string for known token values.
        _ACCENT_VALS = {"#c084fc", "#f472b6", "#7c3aed"}  # default purple accents
        _SEC_VALS = {"#a99fc0"}
        _DIM_VALS = {"#6b6580"}
        _PRI_VALS = {"#f1f0ff"}
        import re as _re

        from PyQt6.QtWidgets import QLabel as _QLabel

        _color_re = _re.compile(r"color\s*:\s*([^;\"']+)")
        _bg_re = _re.compile(r"background\s*:\s*rgba\(\s*192\s*,\s*132\s*,\s*252\s*,\s*[\d.]+\s*\)")
        for lbl in self.findChildren(_QLabel):
            ss = lbl.styleSheet()
            if not ss:
                continue
            changed = False
            # Replace hardcoded purple rgba backgrounds
            if "rgba(192" in ss and "252" in ss:
                new_ss = _bg_re.sub(f"background: {btn_bg}", ss)
                if new_ss != ss:
                    ss = new_ss
                    changed = True
            if "color" in ss:
                m = _color_re.search(ss)
                if m:
                    cur = m.group(1).strip().lower()
                    if cur in {v.lower() for v in _ACCENT_VALS}:
                        ss = _color_re.sub(f"color: {accent}", ss)
                        changed = True
                    elif cur in {v.lower() for v in _SEC_VALS}:
                        ss = _color_re.sub(f"color: {txt_sec}", ss)
                        changed = True
                    elif cur in {v.lower() for v in _DIM_VALS}:
                        ss = _color_re.sub(f"color: {txt_sec}", ss)
                        changed = True
                    elif cur in {v.lower() for v in _PRI_VALS}:
                        ss = _color_re.sub(f"color: {txt_pri}", ss)
                        changed = True
            if changed:
                lbl.setStyleSheet(ss)

    # ------------------------------------------------------------------
    # Graph actions
    # ------------------------------------------------------------------
