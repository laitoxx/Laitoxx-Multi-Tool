# ruff: noqa: F405
from .theme_widget_context import *  # noqa: F403


class _PreviewPane(QWidget):
    """Live preview of how the current theme looks on real UI elements."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QLineEdit as _LE
        from PyQt6.QtWidgets import QPlainTextEdit

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        self._title_lbl = QLabel(translator.get("te_preview_title_text"))
        self._title_lbl.setObjectName("preview_title")
        lay.addWidget(self._title_lbl)

        self._secondary_lbl = QLabel(translator.get("te_preview_secondary_text"))
        self._secondary_lbl.setObjectName("preview_secondary")
        lay.addWidget(self._secondary_lbl)

        row = QHBoxLayout()
        self._btn_normal = QPushButton(translator.get("te_preview_sample_button"))
        self._btn_normal.setObjectName("preview_btn")
        self._btn_hover = QPushButton(translator.get("te_preview_hover_state"))
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
        panel_lbl = QLabel("  " + translator.get("te_preview_panel"))
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
