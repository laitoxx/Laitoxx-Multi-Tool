"""Focused behavior slice for ThemeEditorDialog."""
# ruff: noqa: F405

from .theme_editor_context import *  # noqa: F403


class ThemeEditorDialogMixin2:
    def _build_preview_tab(self) -> QWidget:
        """Preview tab - live demo of the current theme."""
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
        """Tools tab - copy/paste/eyedropper, WCAG fix, colorblind sim, border radius, invert, presets, export."""
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
        """Library tab - browse all themes with favorites."""
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(8, 10, 8, 8)
        lay.setSpacing(6)

        self._lib_search = QLineEdit()
        self._lib_search.setPlaceholderText(translator.get("te_search_themes"))
        self._library_filter_timer = QTimer(self)
        self._library_filter_timer.setSingleShot(True)
        self._library_filter_timer.setInterval(140)
        self._library_filter_timer.timeout.connect(lambda: self._populate_library(self._lib_search.text()))
        self._lib_search.textChanged.connect(lambda: self._library_filter_timer.start())
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

    def _restyle_panels(self, theme: dict):
        theme = resolved_theme(theme)
        accent = theme.get("accent_color", _ACCENT)
        bdr = theme["border_strong_color"]
        txt = theme["text_primary_color"]
        txt_dim = theme["text_secondary_color"]
        bg_win = theme["surface_base_color"]
        panel_bg = theme["surface_raised_color"]
        btn_bg = theme.get("button_bg_color", "rgba(192,132,252,0.12)")
        btn_hov = theme.get("button_hover_bg_color", "rgba(192,132,252,0.28)")
        radius = max(2, int(theme.get("border_radius", 10)) + int(theme.get("radius_delta", 0)))
        edge = int(theme.get("edge_width", 1))
        material = theme.get("material", "glass")
        if material == "metallic":
            panel_bg = (
                f"qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {theme['surface_hover_color']}, "
                f"stop:0.48 {theme['surface_raised_color']}, stop:0.52 {theme['border_strong_color']}, "
                f"stop:0.56 {theme['surface_raised_color']}, stop:1 {theme['surface_base_color']})"
            )
        left_edge = f"border-right: {edge}px solid {bdr};"
        right_edge = f"border-left: {edge}px solid {bdr};"
        if material == "glitch":
            left_edge = f"border-right: 3px solid {accent}; border-bottom: 2px solid {theme['accent_dim_color']};"
            right_edge = f"border-left: 3px solid {theme['accent_dim_color']}; border-top: 2px solid {accent};"

        if hasattr(self, "_left_pane"):
            self._left_pane.setStyleSheet(f"background: {panel_bg}; {left_edge}")
        if hasattr(self, "_center_pane"):
            self._center_pane.setStyleSheet(f"background: {bg_win};")
        if hasattr(self, "_right_pane"):
            self._right_pane.setStyleSheet(f"background: {panel_bg}; {right_edge}")
        if hasattr(self, "_search_lbl"):
            self._search_lbl.setStyleSheet(f"color: {txt_dim}; font-size: 11px; background: transparent;")
        if hasattr(self, "_element_lbl"):
            self._element_lbl.setStyleSheet(
                f"color: {txt}; font-size: 14px; font-weight: 700; background: transparent;"
            )
        if hasattr(self, "_alpha_val_lbl"):
            self._alpha_val_lbl.setStyleSheet(
                f"color: {accent}; font-size: 11px; font-weight: 600; background: transparent;"
            )
        if hasattr(self, "_presets_lbl"):
            self._presets_lbl.setStyleSheet(
                f"color: {txt_dim}; font-size: 12px; font-weight: 700; background: transparent;"
            )
        if hasattr(self, "_export_lbl"):
            self._export_lbl.setStyleSheet(
                f"color: {txt_dim}; font-size: 12px; font-weight: 700; background: transparent;"
            )
        # Save button
        if hasattr(self, "_btn_apply"):
            self._btn_apply.setStyleSheet(
                f"QPushButton {{ background: {btn_bg}; border: 1px solid {accent};"
                f" border-radius: {radius}px; color: {txt}; padding: 5px 14px; font-weight: 600; }}"
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
                    f"color: {txt_dim}; font-size: 11px; font-weight: 700; background: transparent;"
                )

        # Preset buttons - walk all QPushButton in right pane
        preset_ss = (
            f"QPushButton {{ background: rgba(255,255,255,0.04); border: 1px solid {bdr};"
            f" border-radius: 6px; color: {txt}; padding: 4px 8px; text-align: left; }}"
            f"QPushButton:hover {{ background: {btn_hov}; border-color: {accent}; }}"
        )
        if hasattr(self, "_right_pane"):
            from PyQt6.QtWidgets import QPushButton as _QPB

            for btn in self._right_pane.findChildren(_QPB):
                btn.setStyleSheet(preset_ss)
