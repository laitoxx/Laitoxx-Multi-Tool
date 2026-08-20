"""Focused behavior slice for ImageSearchWindow."""
# ruff: noqa: F405

from .image_search_window_context import *  # noqa: F403


class ImageSearchWindowMixin1:
    def _load_theme_from_parent(self) -> None:
        td = None
        p = self.parent()
        if p and hasattr(p, "theme_data"):
            td = p.theme_data
        if not td:
            td = load_default_theme()
        self._theme = dict(DEFAULT_THEME)
        self._theme.update(td or {})

    def _tc(self) -> dict[str, str]:
        """Return the active semantic color values."""
        td = resolved_theme(self._theme)
        return {
            "accent": td.get("accent_color", ACCENT),
            "accent2": td.get("accent_color", ACCENT2),
            "accent_dim": td.get("accent_dim_color", ACCENT_DIM),
            "bg_deep": td.get("window_bg_color", td.get("text_area_bg_color", BG_DEEP)),
            "bg_card": td.get("panel_bg_color", BG_CARD),
            "bg_panel": td.get("panel_bg_color", BG_PANEL),
            "text_pri": td.get("text_primary_color", TEXT_PRI),
            "text_sec": td.get("text_secondary_color", TEXT_SEC),
            "text_dim": td.get("text_secondary_color", TEXT_DIM),
            "border": td.get("border_color", td.get("button_border_color", BORDER)),
        }

    def _apply_style(self) -> None:
        c = self._tc()
        semantic = resolved_theme(self._theme)
        self.setStyleSheet(
            build_base_style(
                c["accent"],
                c["accent_dim"],
                c["bg_deep"],
                c["bg_card"],
                c["text_pri"],
                c["border"],
            )
            + build_workspace_qss(semantic)
            + f"QDialog {{ background: {semantic['surface_base_color']}; }}"
        )

    def update_theme(self, theme_data: dict) -> None:
        """Apply a theme update received from the main window."""
        self._theme = dict(DEFAULT_THEME)
        self._theme.update(theme_data)
        self._apply_style()
        self._restyle_all()

    def _restyle_all(self) -> None:
        """Reapply theme dependent styles to existing widgets."""
        c = self._tc()
        ac, acd, ac2 = c["accent"], c["accent_dim"], c["accent2"]
        bd = c["border"]
        tp, ts, td = c["text_pri"], c["text_sec"], c["text_dim"]

        if hasattr(self, "_toolbar_widget"):
            self._toolbar_widget.setStyleSheet(f"background: {c['bg_panel']};")
        if hasattr(self, "_center_widget"):
            self._center_widget.setStyleSheet(f"background: {c['bg_deep']};")
        if hasattr(self, "_context_panel"):
            self._context_panel.setStyleSheet(f"background: {c['bg_panel']};")

        splitter_style = f"QSplitter::handle {{ background: {bd}; }}"
        for attr in ("_h_splitter", "_v_splitter"):
            if hasattr(self, attr):
                getattr(self, attr).setStyleSheet(splitter_style)

        for attr, style in [
            ("_hdr_filename", f"color: {tp}; font-weight: 600;"),
            ("_hdr_size", f"color: {ts}; font-size: 12px;"),
            ("_hdr_dims", f"color: {ts}; font-size: 12px;"),
            ("_hdr_status", f"color: {td}; font-size: 12px;"),
        ]:
            if hasattr(self, attr):
                getattr(self, attr).setStyleSheet(style)

        if hasattr(self, "_tool_buttons"):
            self._highlight_tool(self._current_tool)

        if hasattr(self, "_preview_label"):
            self._preview_label._apply_colors(c["bg_card"], bd, td)

        if hasattr(self, "_toggle_preview_btn"):
            btn = self._toggle_preview_btn
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {ts};
                    border: 1px solid {bd}; border-radius: 6px; padding: 5px 10px;
                }}
                QPushButton:hover {{ border-color: {ac}; color: {ac}; }}
            """)

        if hasattr(self, "_forensics_btn"):
            self._forensics_btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 {acd}, stop:1 {ac});
                    color: white; border: none; border-radius: 8px;
                    padding: 8px 16px; font-weight: 600; font-size: 13px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 {ac}, stop:1 {ac2});
                }}
            """)

        if hasattr(self, "_engine_buttons"):
            for btn in self._engine_buttons.values():
                btn.setStyleSheet(self._engine_pill_style(btn.isChecked()))

        if hasattr(self, "_hashes_placeholder"):
            self._hashes_placeholder.setStyleSheet(f"color: {td}; font-size: 12px; padding: 20px;")

        if hasattr(self, "_hash_row_widgets"):
            for edit in self._hash_row_widgets.values():
                edit.setStyleSheet(f"""
                    QLineEdit {{
                        background: rgba(255,255,255,0.04);
                        border: 1px solid {bd};
                        border-radius: 5px;
                        color: {tp};
                        font-family: 'Consolas', 'Courier New', monospace;
                        font-size: 10px;
                        padding: 3px 6px;
                    }}
                """)

        if hasattr(self, "_slider_labels"):
            for lbl in self._slider_labels.values():
                lbl.setStyleSheet(f"color: {ac}; font-size: 11px; font-family: monospace;")

        if hasattr(self, "_editor_btn_area"):
            self._editor_btn_area.setStyleSheet(f"background: {c['bg_panel']}; border-top: 1px solid {bd};")

        if hasattr(self, "_hashes_btn_area"):
            self._hashes_btn_area.setStyleSheet(f"background: {c['bg_panel']}; border-top: 1px solid {bd};")

    def _build_ui(self) -> None:
        c = self._tc()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {c['border']};")
        root.addWidget(sep)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._toolbar_widget = self._build_toolbar()
        body.addWidget(self._toolbar_widget)

        vsep = QFrame()
        vsep.setFixedWidth(1)
        vsep.setStyleSheet(f"background: {c['border']};")
        body.addWidget(vsep)

        self._h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._h_splitter.setHandleWidth(1)
        self._h_splitter.setStyleSheet(f"QSplitter::handle {{ background: {c['border']}; }}")

        self._center_widget = self._build_center()
        self._h_splitter.addWidget(self._center_widget)

        self._context_panel = self._build_context_panel()
        self._h_splitter.addWidget(self._context_panel)

        self._h_splitter.setStretchFactor(0, 1)
        self._h_splitter.setStretchFactor(1, 0)
        self._h_splitter.setSizes([700, 240])

        body.addWidget(self._h_splitter, stretch=1)
        root.addLayout(body, stretch=1)

        self._restyle_all()

    def _build_header(self) -> QWidget:
        c = self._tc()
        w = QFrame()
        w.setObjectName("PageHeader")
        w.setFixedHeight(72)
        w.setStyleSheet(f"background: {c['bg_panel']};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(18, 8, 14, 8)
        lay.setSpacing(16)

        identity = QVBoxLayout()
        identity.setSpacing(1)
        title = QLabel(_t("is_title", "Image Analysis"))
        title.setObjectName("PanelTitle")
        self._hdr_filename = QLabel(_t("is_no_file", "No file selected"))
        self._hdr_filename.setStyleSheet(f"color: {c['text_sec']};")
        identity.addWidget(title)
        identity.addWidget(self._hdr_filename)
        lay.addLayout(identity)

        self._hdr_size = QLabel("")
        self._hdr_size.setStyleSheet(f"color: {c['text_sec']}; font-size: 12px;")
        lay.addWidget(self._hdr_size)

        self._hdr_dims = QLabel("")
        self._hdr_dims.setStyleSheet(f"color: {c['text_sec']}; font-size: 12px;")
        lay.addWidget(self._hdr_dims)

        lay.addStretch()

        self._hdr_status = QLabel("")
        self._hdr_status.setStyleSheet(f"color: {c['text_dim']}; font-size: 12px;")
        lay.addWidget(self._hdr_status)

        open_button = QPushButton(_t("is_open_file_dialog", "Open image"))
        open_button.setProperty("variant", "primary")
        open_button.clicked.connect(self._browse_file)
        lay.addWidget(open_button)

        return w

    def _build_toolbar(self) -> QWidget:
        c = self._tc()
        w = QWidget()
        w.setFixedWidth(188)
        w.setStyleSheet(f"background: {c['bg_panel']};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 12, 8, 12)
        lay.setSpacing(4)

        self._tool_buttons: dict[str, QPushButton] = {}
        tools = [
            ("fingerprint", "◎", _t("Avatar Fingerprinting", "Avatar fingerprint")),
            ("search", "⌕", _t("is_tool_search", "Reverse search")),
            ("editor", "✎", _t("is_tool_editor", "Editor")),
            ("hashes", "#", _t("is_tool_hashes", "Hashes")),
            ("forensics", "◇", _t("is_tool_forensics", "Forensics")),
        ]
        for key, icon, tip in tools:
            btn = QPushButton(f"{icon}   {tip}")
            btn.setToolTip(tip)
            btn.setFixedHeight(42)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._tool_btn_style(False))
            btn.clicked.connect(lambda _, k=key: self._switch_tool(k))
            lay.addWidget(btn)
            self._tool_buttons[key] = btn

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {c['border']}; max-height: 1px; margin: 6px 4px;")
        lay.addWidget(sep)

        open_btn = QPushButton(f"+   {_t('is_open_file_tooltip', 'Open image')}")
        open_btn.setToolTip(_t("is_open_file_tooltip", "Open file"))
        open_btn.setFixedHeight(42)
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet(self._tool_btn_style(False))
        open_btn.clicked.connect(self._browse_file)
        lay.addWidget(open_btn)

        lay.addStretch()
        self._highlight_tool("search")
        return w

    def _tool_btn_style(self, active: bool) -> str:
        c = self._tc()
        return tool_btn_style(active, c["accent"], c["text_pri"], c["text_dim"])

    def _highlight_tool(self, tool: str) -> None:
        for k, btn in self._tool_buttons.items():
            btn.setStyleSheet(self._tool_btn_style(k == tool))
