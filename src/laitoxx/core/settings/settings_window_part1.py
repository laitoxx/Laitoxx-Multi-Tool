"""Focused behavior slice for SettingsWindow."""
# ruff: noqa: F405

from .settings_window_context import *  # noqa: F403


class SettingsWindowMixin1:
    def _t(self, key: str, **kw) -> str:
        if self._tr:
            return self._tr.get(key, **kw)
        return key

    def _make_page(self, title_key: str, *, spacing: int = 12) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(*self._PAGE_MARGINS)
        layout.setSpacing(spacing)

        title = QLabel(self._t(title_key))
        title.setStyleSheet(self._TITLE_STYLE)
        layout.addWidget(title)
        return page, layout

    def _label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(self._LABEL_STYLE)
        return label

    def _add_labeled_row(self, layout: QVBoxLayout, label_text: str, widget: QWidget):
        row = QHBoxLayout()
        row.addWidget(self._label(label_text))
        row.addWidget(widget)
        row.addStretch()
        layout.addLayout(row)

    def _populate_combo(self, combo: QComboBox, items: list[tuple[str, str]], current: str | None):
        combo.clear()
        for name, path in items:
            combo.addItem(name, path)
        if current:
            self._select_combo_value(combo, current)

    @staticmethod
    def _select_combo_value(combo: QComboBox, value: str):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                break

    def _open_background_file(self) -> str | None:
        exts = " ".join(f"*{e}" for e in SUPPORTED_EXT)
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._t("sw_import_bg_dialog"),
            "",
            f"Background files ({exts})",
        )
        return path or None

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left navigation list ──────────────────────────────────────────────
        self._nav = QListWidget()
        self._nav.setFixedWidth(170)
        self._nav.setStyleSheet(
            "QListWidget { background: rgba(0,0,0,0.35); border: none; }"
            "QListWidget::item { color: white; padding: 12px 16px; font-size: 13px; }"
            "QListWidget::item:selected { background: rgba(255,255,255,0.12); "
            "border-left: 3px solid rgba(200,80,80,0.9); }"
            "QListWidget::item:hover { background: rgba(255,255,255,0.07); }"
        )

        sections = [
            ("sw_nav_general", self._t("sw_nav_general")),
            ("sw_nav_themes", self._t("sw_nav_themes")),
            ("sw_nav_background", self._t("sw_nav_background")),
            ("sw_nav_proxy", self._t("sw_nav_proxy")),
            ("sw_nav_schedule", self._t("sw_nav_schedule")),
            ("sw_nav_web_scanner", self._t("sw_nav_web_scanner")),
        ]
        for key, label in sections:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._nav.addItem(item)

        self._nav.setCurrentRow(0)
        self._nav.currentRowChanged.connect(self._on_nav_changed)

        # ── Right stacked pages ───────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: rgba(0,0,0,0.18);")

        self._page_general = self._build_page_general()
        self._page_themes = self._build_page_themes()
        self._page_background = self._build_page_background()
        self._page_proxy = self._build_page_proxy()
        self._page_schedule = self._build_page_schedule()
        self._page_web_scanner = self._build_page_web_scanner()

        for page in (
            self._page_general,
            self._page_themes,
            self._page_background,
            self._page_proxy,
            self._page_schedule,
            self._page_web_scanner,
        ):
            self._stack.addWidget(page)

        root.addWidget(self._nav)
        root.addWidget(self._stack)

    def _on_nav_changed(self, idx: int):
        self._stack.setCurrentIndex(idx)
        if idx == 1:
            self._refresh_themes_list()
        elif idx == 2:
            self._refresh_bg_list()

    def _build_page_web_scanner(self) -> QWidget:
        page, lay = self._make_page("sw_nav_web_scanner", spacing=16)
        note = QLabel(self._t("sw_web_scanner_note"))
        note.setWordWrap(True)
        note.setStyleSheet(self._LABEL_STYLE)
        lay.addWidget(note)
        button = QPushButton(self._t("sw_web_scanner_open"))
        button.clicked.connect(self._open_web_scanner_settings)
        lay.addWidget(button)
        lay.addStretch()
        return page

    def _open_web_scanner_settings(self):
        from laitoxx.interfaces.gui.advanced_web_scanner_settings import AdvancedWebScannerSettingsDialog

        AdvancedWebScannerSettingsDialog(self, self._theme_data).exec()

    def _build_page_general(self) -> QWidget:
        page, lay = self._make_page("sw_nav_general", spacing=16)

        # Open website on startup
        self._chk_open_site = QCheckBox(self._t("sw_open_site_on_startup"))
        self._chk_open_site.setChecked(settings.open_website_on_startup)
        self._chk_open_site.setStyleSheet(self._LABEL_STYLE)
        self._chk_open_site.toggled.connect(self._on_open_site_toggled)
        lay.addWidget(self._chk_open_site)

        # Performance mode (reduce effects)
        self._chk_perf_mode = QCheckBox(self._t("sw_performance_mode"))
        self._chk_perf_mode.setChecked(settings.performance_mode)
        self._chk_perf_mode.setStyleSheet(self._LABEL_STYLE)
        self._chk_perf_mode.toggled.connect(self._on_performance_toggled)
        lay.addWidget(self._chk_perf_mode)

        # Language
        self._combo_lang = QComboBox()
        self._combo_lang.addItem("English", "en")
        self._combo_lang.addItem("Русский", "ru")
        cur_lang = settings.language
        idx = self._combo_lang.findData(cur_lang)
        if idx >= 0:
            self._combo_lang.setCurrentIndex(idx)
        self._combo_lang.currentIndexChanged.connect(self._on_language_changed)
        self._add_labeled_row(lay, self._t("sw_language") + ":", self._combo_lang)

        lay.addStretch()

        reset_note = QLabel(self._t("sw_clear_cache_hint"))
        reset_note.setWordWrap(True)
        reset_note.setStyleSheet(self._LABEL_STYLE)
        lay.addWidget(reset_note)

        clear_cache = QPushButton(self._t("sw_clear_cache"))
        clear_cache.setProperty("variant", "danger")
        clear_cache.clicked.connect(self._confirm_application_reset)
        lay.addWidget(clear_cache)
        return page

    def _confirm_application_reset(self):
        answer = QMessageBox.warning(
            self,
            self._t("sw_clear_cache_confirm_title"),
            self._t("sw_clear_cache_confirm_text"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        from .data_reset import reset_application_data

        result = reset_application_data()
        if result.errors:
            details = "\n".join(result.errors[:8])
            QMessageBox.warning(
                self,
                self._t("sw_clear_cache_partial_title"),
                self._t(
                    "sw_clear_cache_partial_text",
                    count=result.removed_files,
                    details=details,
                ),
            )
        else:
            QMessageBox.information(
                self,
                self._t("sw_clear_cache_done_title"),
                self._t("sw_clear_cache_done_text", count=result.removed_files),
            )
        self.application_reset.emit()
        self.accept()

    def _build_page_themes(self) -> QWidget:
        page, lay = self._make_page("sw_nav_themes")

        # Dropdown of available themes
        self._combo_theme = QComboBox()
        self._combo_theme.setMinimumWidth(220)
        self._add_labeled_row(lay, self._t("sw_select_theme") + ":", self._combo_theme)

        # Apply button
        btn_apply = QPushButton(self._t("sw_apply_theme"))
        btn_apply.clicked.connect(self._on_apply_theme)
        lay.addWidget(btn_apply)

        # Theme editor (opens ThemeEditorDialog)
        btn_edit = QPushButton(self._t("sw_open_theme_editor"))
        btn_edit.clicked.connect(self._on_open_theme_editor)
        lay.addWidget(btn_edit)

        appearance_title = QLabel("Interface style")
        appearance_title.setObjectName("SectionLabel")
        lay.addWidget(appearance_title)

        self._combo_style_mode = QComboBox()
        for key, title in STYLE_MODES.items():
            self._combo_style_mode.addItem(title, key)
        index = self._combo_style_mode.findData(settings.style_mode)
        self._combo_style_mode.setCurrentIndex(max(0, index))
        self._add_labeled_row(lay, "Style mode:", self._combo_style_mode)

        self._combo_font = QComboBox()
        self._combo_font.addItems(_font_choices(settings.font_family, _SAFE_UI_FONTS))
        self._combo_font.setItemDelegate(_FontPreviewDelegate(self._combo_font))
        index = self._combo_font.findText(settings.font_family)
        if index >= 0:
            self._combo_font.setCurrentIndex(index)
        self._add_labeled_row(lay, "Font:", self._combo_font)

        self._combo_code_font = QComboBox()
        self._combo_code_font.addItems(_font_choices(settings.code_font_family, _SAFE_CODE_FONTS))
        self._combo_code_font.setItemDelegate(_FontPreviewDelegate(self._combo_code_font))
        index = self._combo_code_font.findText(settings.code_font_family)
        if index >= 0:
            self._combo_code_font.setCurrentIndex(index)
        self._add_labeled_row(lay, "Code font:", self._combo_code_font)

        self._spin_font_size = QSpinBox()
        self._spin_font_size.setRange(10, 18)
        self._spin_font_size.setSuffix(" px")
        self._spin_font_size.setValue(settings.font_size)
        self._add_labeled_row(lay, "Font size:", self._spin_font_size)

        btn_appearance = QPushButton("Apply interface settings")
        btn_appearance.setProperty("variant", "primary")
        btn_appearance.clicked.connect(self._on_apply_appearance)
        lay.addWidget(btn_appearance)

        lay.addStretch()
        self._refresh_themes_list()
        return page

    def _refresh_themes_list(self):
        self._populate_combo(self._combo_theme, list_themes(), settings.theme_path)

    def _on_apply_theme(self):
        path = self._combo_theme.currentData()
        if not path:
            return
        data = load_theme(path)
        if data:
            settings.theme_path = path
            self._theme_data = data
            self.theme_changed.emit(data, path)

    def _on_open_theme_editor(self):
        try:
            from laitoxx.interfaces.gui.theme_editor import ThemeEditorDialog
        except ImportError:
            QMessageBox.warning(self, "Error", "ThemeEditorDialog not available.")
            return
        editor = ThemeEditorDialog(self, self._theme_data)
        if editor.exec():
            new_data = editor.get_theme_data()
            name, ok = self._ask_theme_name()
            if ok and name:
                path = save_theme_to_resources(name, new_data)
                settings.theme_path = path
                self._theme_data = new_data
                self._refresh_themes_list()
                self.theme_changed.emit(new_data, path)

    def _on_apply_appearance(self):
        settings.style_mode = self._combo_style_mode.currentData()
        settings.font_family = self._combo_font.currentText()
        settings.code_font_family = self._combo_code_font.currentText()
        settings.font_size = self._spin_font_size.value()
        self._theme_data.update(
            style_mode=settings.style_mode,
            font_family=settings.font_family,
            code_font_family=settings.code_font_family,
            font_size=settings.font_size,
        )
        self._apply_theme()
        self.theme_changed.emit(dict(self._theme_data), settings.theme_path)

    def _ask_theme_name(self) -> tuple[str, bool]:
        from PyQt6.QtWidgets import QInputDialog

        return QInputDialog.getText(self, self._t("sw_theme_name_title"), self._t("sw_theme_name_prompt"))
