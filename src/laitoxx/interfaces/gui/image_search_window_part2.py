"""Focused behavior slice for ImageSearchWindow."""
# ruff: noqa: F405

from .image_search_window_context import *  # noqa: F403


class ImageSearchWindowMixin2:
    def _build_center(self) -> QWidget:
        c = self._tc()
        w = QWidget()
        w.setStyleSheet(f"background: {c['bg_deep']};")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._v_splitter = QSplitter(Qt.Orientation.Vertical)
        self._v_splitter.setHandleWidth(4)
        self._v_splitter.setStyleSheet(f"QSplitter::handle {{ background: {c['border']}; }}")

        # Preview block
        preview_widget = QWidget()
        preview_widget.setStyleSheet("background: transparent;")
        preview_lay = QVBoxLayout(preview_widget)
        preview_lay.setContentsMargins(12, 12, 12, 4)
        preview_lay.setSpacing(4)

        self._preview_label = _ScalableImageLabel()
        self._preview_label.setMinimumHeight(80)
        preview_lay.addWidget(self._preview_label)

        self._toggle_preview_btn = make_button(
            _t("is_toggle_before_after", "Before / After"),
            ghost=True,
            ac=c["accent"],
            ac2=c["accent2"],
            acd=c["accent_dim"],
            ts=c["text_sec"],
            bd=c["border"],
        )
        self._toggle_preview_btn.setVisible(False)
        self._toggle_preview_btn.clicked.connect(self._toggle_original)
        preview_lay.addWidget(self._toggle_preview_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Results block
        self._results_scroll = QScrollArea()
        self._results_scroll.setWidgetResizable(True)
        self._results_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._results_scroll.setMinimumHeight(60)
        self._results_scroll.setStyleSheet("background: transparent;")

        self._results_container = QWidget()
        self._results_container.setStyleSheet("background: transparent;")
        self._results_layout = QVBoxLayout(self._results_container)
        self._results_layout.setContentsMargins(12, 4, 12, 12)
        self._results_layout.setSpacing(6)
        self._results_layout.addStretch()
        self._results_scroll.setWidget(self._results_container)

        self._v_splitter.addWidget(preview_widget)
        self._v_splitter.addWidget(self._results_scroll)
        self._v_splitter.setStretchFactor(0, 3)
        self._v_splitter.setStretchFactor(1, 2)
        self._v_splitter.setSizes([340, 200])

        outer.addWidget(self._v_splitter)
        return w

    def _build_context_panel(self) -> QWidget:
        c = self._tc()
        w = QWidget()
        w.setMinimumWidth(180)
        w.setMaximumWidth(400)
        w.setStyleSheet(f"background: {c['bg_panel']};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._ctx_search = self._build_ctx_search()
        self._ctx_editor = self._build_ctx_editor()
        self._ctx_hashes = self._build_ctx_hashes()
        self._ctx_fingerprint = self._build_ctx_fingerprint()
        self._ctx_forensics = self._build_ctx_forensics()

        for panel in (
            self._ctx_search,
            self._ctx_editor,
            self._ctx_hashes,
            self._ctx_fingerprint,
            self._ctx_forensics,
        ):
            lay.addWidget(panel, stretch=1)
            panel.setVisible(False)

        self._ctx_search.setVisible(True)
        return w

    def _build_ctx_search(self) -> QWidget:
        c = self._tc()
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        outer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        vlay = QVBoxLayout(outer)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(12, 12, 12, 8)
        lay.setSpacing(4)

        lay.addWidget(_section_label(_t("is_engines_section", "Search Engines"), c["text_dim"]))

        self._engine_buttons: dict[str, QPushButton] = {}
        for key, engines in _ENGINE_GROUPS:
            grp_name = _t(key, _ENGINE_GROUP_FALLBACKS[key])
            hdr = QLabel(grp_name)
            hdr.setStyleSheet(f"""
                color: {c["text_dim"]};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 10px 0 2px 0;
            """)
            lay.addWidget(hdr)
            for eng in engines:
                checked = eng in _DEFAULT_ENGINES_ON
                btn = QPushButton(eng)
                btn.setCheckable(True)
                btn.setChecked(checked)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(self._engine_pill_style(checked))
                btn.toggled.connect(lambda ch, b=btn: b.setStyleSheet(self._engine_pill_style(ch)))
                lay.addWidget(btn)
                self._engine_buttons[eng] = btn

        lay.addStretch()
        scroll.setWidget(inner)
        vlay.addWidget(scroll, stretch=1)
        return outer

    def _engine_pill_style(self, checked: bool) -> str:
        c = self._tc()
        return engine_pill_style(checked, c["accent"], c["text_sec"], c["border"], c["text_pri"])

    def _build_ctx_editor(self) -> QWidget:
        c = self._tc()
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        outer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        vlay = QVBoxLayout(outer)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        lay.addWidget(_section_label(_t("is_editor_section", "Image Settings"), c["text_dim"]))

        self._sliders: dict[str, QSlider] = {}
        self._slider_labels: dict[str, QLabel] = {}

        for key, t_key, mn, mx in _SLIDER_DEFS:
            name = _t(t_key, key.capitalize())
            row = QHBoxLayout()
            row.setSpacing(6)

            lbl_name = QLabel(name)
            lbl_name.setFixedWidth(100)
            lbl_name.setStyleSheet(f"color: {c['text_sec']}; font-size: 11px;")
            row.addWidget(lbl_name)

            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(mn, mx)
            sl.setValue(0)
            sl.setFixedHeight(18)
            row.addWidget(sl, stretch=1)

            lbl_val = QLabel("+0")
            lbl_val.setFixedWidth(36)
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl_val.setStyleSheet(f"color: {c['accent']}; font-size: 11px; font-family: monospace;")
            row.addWidget(lbl_val)

            sl.valueChanged.connect(lambda v, lv=lbl_val, k=key: self._on_slider_changed(k, v, lv))
            self._sliders[key] = sl
            self._slider_labels[key] = lbl_val
            lay.addLayout(row)

        lay.addStretch()
        scroll.setWidget(inner)
        vlay.addWidget(scroll, stretch=1)

        self._editor_btn_area = QWidget()
        self._editor_btn_area.setStyleSheet(f"background: {c['bg_panel']}; border-top: 1px solid {c['border']};")
        btn_lay = QVBoxLayout(self._editor_btn_area)
        btn_lay.setContentsMargins(12, 8, 12, 12)
        btn_lay.setSpacing(6)

        reset_btn = make_button(
            _t("is_reset_btn", "Reset All"),
            ghost=True,
            ac=c["accent"],
            ac2=c["accent2"],
            acd=c["accent_dim"],
            ts=c["text_sec"],
            bd=c["border"],
        )
        reset_btn.clicked.connect(self._reset_sliders)
        btn_lay.addWidget(reset_btn)

        save_btn = make_button(
            _t("is_save_btn", "Save Image"),
            accent=True,
            ac=c["accent"],
            ac2=c["accent2"],
            acd=c["accent_dim"],
        )
        save_btn.clicked.connect(self._save_edited)
        btn_lay.addWidget(save_btn)

        vlay.addWidget(self._editor_btn_area)
        return outer
