"""Focused behavior slice for ThemeEditorDialog."""
# ruff: noqa: F405

from .theme_editor_context import *  # noqa: F403


class ThemeEditorDialogMixin1:
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("PageHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 9, 12, 9)
        header_copy = QVBoxLayout()
        header_copy.setSpacing(1)
        title = QLabel(translator.get("theme_editor_title"))
        title.setObjectName("PanelTitle")
        self._header_state = QLabel(translator.get("te_live_preview"))
        self._header_state.setObjectName("Muted")
        header_copy.addWidget(title)
        header_copy.addWidget(self._header_state)
        header_layout.addLayout(header_copy)
        header_layout.addStretch()
        header_save = QPushButton(translator.get("save_theme"))
        header_save.setProperty("variant", "primary")
        header_save.clicked.connect(self._save_and_close)
        header_layout.addWidget(header_save)
        root.addWidget(header)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        root.addWidget(body, 1)

        # ── Left panel ──────────────────────────────────────────────────────
        self._left_pane = QWidget()
        left = self._left_pane
        left.setFixedWidth(270)
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
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._list.currentItemChanged.connect(self._on_item_selected)
        left_layout.addWidget(self._list, 1)

        body_layout.addWidget(left)

        # ── Center panel with tabs ───────────────────────────────────────────
        self._center_pane = QWidget()
        center = self._center_pane
        center.setStyleSheet(f"background: {_PANEL};")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(12, 12, 12, 12)
        center_layout.setSpacing(8)

        # Title of selected element (outside tabs)
        self._element_lbl = QLabel("")
        self._element_lbl.setObjectName("PanelTitle")
        center_layout.addWidget(self._element_lbl)
        self._element_key_lbl = QLabel("")
        self._element_key_lbl.setObjectName("Muted")
        center_layout.addWidget(self._element_key_lbl)

        # Tabs
        self._center_tabs = QTabWidget()
        self._center_tabs.addTab(self._build_picker_tab(), translator.get("te_color_picker"))
        self._center_tabs.addTab(self._build_palettes_tab(), translator.get("te_tab_palettes"))
        center_layout.addWidget(self._center_tabs, 3)
        center_layout.addWidget(self._build_preview_tab(), 2)

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

        body_layout.addWidget(center, 1)

        # ── Right panel - tabbed (Tools + Library) ───────────────────────────
        self._right_pane = QWidget()
        right = self._right_pane
        right.setFixedWidth(300)
        right.setStyleSheet(f"background: {_PANEL2}; border-left: 1px solid {_BORDER};")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._right_tabs = QTabWidget()
        self._right_tabs.addTab(self._build_tools_tab(), translator.get("te_presets"))
        self._right_tabs.addTab(self._build_library_tab(), translator.get("te_tab_library"))
        right_layout.addWidget(self._right_tabs)

        body_layout.addWidget(right)

    def _build_picker_tab(self) -> QWidget:
        """Color Picker tab - existing wheel/alpha/hex/contrast/history."""
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
        alpha_lbl = QLabel(translator.get("te_alpha"))
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
        hex_lbl = QLabel(translator.get("te_hex_css"))
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
        """Smart Palettes tab - harmony generation + image extraction."""
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
