# ruff: noqa: F405
from .username_window_context import *  # noqa: F403


class UsernameOsintMixin2:
    def _restyle_widgets(self, td: dict):
        """Re-apply inline styles on every widget that has a hardcoded stylesheet."""
        accent = td.get("accent_color", _ACCENT)
        dim = td.get("accent_dim_color", _ACCENT_DIM)
        bdr = td.get("border_color", td.get("button_border_color", _BORDER))
        txt_pri = td.get("text_area_text_color", _TEXT_PRI)
        txt_sec = td.get("text_secondary_color", _TEXT_SEC)
        btn_bg = td.get("button_bg_color", "rgba(124,58,237,0.5)")
        btn_hov = td.get("button_hover_bg_color", "rgba(139,92,246,0.7)")
        bg_win = td.get("window_bg_color", td.get("text_area_bg_color", _BG_DEEP))
        panel_bg = td.get("panel_bg_color", bg_win)

        # Glass panel (left sidebar)
        if hasattr(self, "_left_panel"):
            self._left_panel.set_theme(bdr, panel_bg)

        # Hero @ label
        if hasattr(self, "_at_label"):
            self._at_label.setStyleSheet(
                f"color: {accent}; font-size: 22px; font-weight: 700; background: transparent;"
            )

        # Username input (big hero field)
        if hasattr(self, "_username_input"):
            self._username_input.setStyleSheet(f"""
                QLineEdit {{
                    background: rgba(255,255,255,0.04);
                    border: 1px solid {bdr};
                    border-radius: 10px;
                    color: {txt_pri};
                    padding: 6px 14px;
                    font-size: 16px;
                    font-weight: 500;
                }}
                QLineEdit:focus {{
                    border-color: {accent};
                    background: rgba(255,255,255,0.06);
                }}
            """)

        # Search button (_AccentButton)
        if hasattr(self, "_btn_search"):
            self._btn_search.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 {dim}, stop:1 {accent});
                    border: 1px solid {dim};
                    border-radius: 8px;
                    color: white;
                    font-size: 13px;
                    font-weight: 700;
                    padding: 0 20px;
                    letter-spacing: 0.5px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 {accent}, stop:1 {btn_hov});
                    border-color: {accent};
                }}
                QPushButton:pressed {{ background: {dim}; padding-top: 2px; }}
                QPushButton:disabled {{
                    background: rgba(60,50,80,0.3);
                    border-color: rgba(255,255,255,0.06);
                    color: {_TEXT_DIM};
                }}
            """)

        # Ghost buttons (Variants / Graph / Export)
        ghost_ss = f"""
            QPushButton {{
                background: {btn_bg};
                border: 1px solid {bdr};
                border-radius: 7px;
                color: {txt_sec};
                font-size: 11px;
                font-weight: 600;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: {btn_hov};
                color: {txt_pri};
                border-color: {accent};
            }}
            QPushButton:pressed {{ background: {btn_hov}; }}
            QPushButton:disabled {{
                background: rgba(50,50,50,0.15);
                color: {_TEXT_DIM};
                border-color: rgba(255,255,255,0.05);
            }}
        """
        for btn_name in ("_btn_nicks", "_btn_graph", "_btn_export"):
            btn = getattr(self, btn_name, None)
            if btn:
                btn.setStyleSheet(ghost_ss)

        # Portrait / phonetic text
        if hasattr(self, "_portrait_text"):
            self._portrait_text.setStyleSheet(f"""
                QTextEdit {{
                    background: rgba(0,0,0,0.2);
                    border: 1px solid {bdr};
                    border-radius: 8px;
                    color: {txt_sec};
                    font-size: 11px;
                    font-family: 'Consolas', monospace;
                }}
            """)
        if hasattr(self, "_phonetic_text"):
            self._phonetic_text.setStyleSheet(f"color: {txt_sec}; font-size: 9px; background: transparent;")

        # Nick list widget (QTextEdit)
        if hasattr(self, "_nick_list"):
            self._nick_list.setStyleSheet(f"""
                QTextEdit {{
                    background: rgba(255,255,255,0.03);
                    border: 1px solid {bdr};
                    border-radius: 6px;
                    color: {txt_pri};
                    font-size: 10px;
                    font-family: 'Consolas', monospace;
                }}
            """)

        # Re-style mini buttons (All/None in categories row)
        mini_css = self._mini_btn_css()
        if hasattr(self, "_left_panel"):
            from PyQt6.QtWidgets import QPushButton as _QPushButton

            for btn in self._left_panel.findChildren(_QPushButton):
                btn.setStyleSheet(mini_css)

        import re as _re

        from PyQt6.QtWidgets import QLabel as _QLabel

        _bg_re = _re.compile(r"background\s*:\s*rgba\(\s*192\s*,\s*132\s*,\s*252\s*,\s*[\d.]+\s*\)")

        # Re-colour all QLabel children that have hardcoded purple token colours.
        _ACCENT_VALS = {"#c084fc", "#f472b6", "#7c3aed"}
        _SEC_VALS = {"#a99fc0"}
        _DIM_VALS = {"#6b6580"}
        _PRI_VALS = {"#f1f0ff"}
        _simple_color_re = _re.compile(r"color\s*:\s*([^;\"'\n]+)")
        for lbl in self.findChildren(_QLabel):
            ss = lbl.styleSheet()
            if not ss:
                continue
            changed = False
            # Fix purple rgba backgrounds in section labels
            if "rgba(192,132,252" in ss or "rgba(192, 132, 252" in ss:
                ss = _bg_re.sub(f"background: {btn_bg}", ss)
                changed = True
            if "color" in ss:
                m = _simple_color_re.search(ss)
                if m:
                    cur = m.group(1).strip().lower()
                    if cur in {v.lower() for v in _ACCENT_VALS}:
                        ss = _simple_color_re.sub(f"color: {accent}", ss)
                        changed = True
                    elif cur in {v.lower() for v in _SEC_VALS}:
                        ss = _simple_color_re.sub(f"color: {txt_sec}", ss)
                        changed = True
                    elif cur in {v.lower() for v in _DIM_VALS}:
                        ss = _simple_color_re.sub(f"color: {txt_sec}", ss)
                        changed = True
                    elif cur in {v.lower() for v in _PRI_VALS}:
                        ss = _simple_color_re.sub(f"color: {txt_pri}", ss)
                        changed = True
            if changed:
                lbl.setStyleSheet(ss)
