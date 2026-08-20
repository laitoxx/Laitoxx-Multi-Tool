"""Focused behavior slice for SettingsWindow."""
# ruff: noqa: F405

from .settings_window_context import *  # noqa: F403


class SettingsWindowMixin2:
    def _build_page_background(self) -> QWidget:
        page, lay = self._make_page("sw_nav_background")

        # Dropdown
        self._combo_bg = QComboBox()
        self._combo_bg.setMinimumWidth(260)
        self._add_labeled_row(lay, self._t("sw_select_bg") + ":", self._combo_bg)

        # Apply
        btn_apply_bg = QPushButton(self._t("sw_apply_bg"))
        btn_apply_bg.clicked.connect(self._on_apply_bg)
        lay.addWidget(btn_apply_bg)

        # Import
        btn_import = QPushButton(self._t("sw_import_bg"))
        btn_import.clicked.connect(self._on_import_bg)
        lay.addWidget(btn_import)

        lay.addStretch()
        self._refresh_bg_list()
        return page

    def _refresh_bg_list(self):
        self._populate_combo(self._combo_bg, list_backgrounds(), settings.background_path)

    def _on_apply_bg(self):
        path = self._combo_bg.currentData()
        if path:
            settings.background_path = path
            self.background_changed.emit(path)

    def _on_import_bg(self):
        path = self._open_background_file()
        if not path:
            return
        dest = import_background(path)
        settings.background_path = dest
        self._refresh_bg_list()
        # Select the newly imported file
        self._select_combo_value(self._combo_bg, dest)
        self.background_changed.emit(dest)

    def _build_page_proxy(self) -> QWidget:
        page, lay = self._make_page("sw_nav_proxy")

        proxy = settings.proxy

        self._chk_proxy = QCheckBox(self._t("sw_proxy_enable"))
        self._chk_proxy.setChecked(proxy.get("enabled", False))
        self._chk_proxy.setStyleSheet(self._LABEL_STYLE)
        lay.addWidget(self._chk_proxy)

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        def lbl(key):
            w = QLabel(self._t(key) + ":")
            w.setStyleSheet("color:white;")
            return w

        self._combo_proxy_type = QComboBox()
        for t in ("http", "https", "socks5"):
            self._combo_proxy_type.addItem(t, t)
        cur_type = proxy.get("type", "http")
        idx = self._combo_proxy_type.findData(cur_type)
        if idx >= 0:
            self._combo_proxy_type.setCurrentIndex(idx)

        self._edit_proxy_host = QLineEdit(proxy.get("host", ""))
        self._edit_proxy_host.setPlaceholderText("127.0.0.1")

        self._edit_proxy_port = QLineEdit(str(proxy.get("port", "")))
        self._edit_proxy_port.setPlaceholderText("1080")

        self._edit_proxy_user = QLineEdit(proxy.get("username", ""))
        self._edit_proxy_user.setPlaceholderText(self._t("sw_proxy_user_placeholder"))

        self._edit_proxy_pass = QLineEdit(proxy.get("password", ""))
        self._edit_proxy_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._edit_proxy_pass.setPlaceholderText(self._t("sw_proxy_pass_placeholder"))

        form.addRow(lbl("sw_proxy_type"), self._combo_proxy_type)
        form.addRow(lbl("sw_proxy_host"), self._edit_proxy_host)
        form.addRow(lbl("sw_proxy_port"), self._edit_proxy_port)
        form.addRow(lbl("sw_proxy_username"), self._edit_proxy_user)
        form.addRow(lbl("sw_proxy_password"), self._edit_proxy_pass)

        lay.addWidget(form_widget)

        btn_save_proxy = QPushButton(self._t("sw_proxy_save"))
        btn_save_proxy.clicked.connect(self._on_save_proxy)
        lay.addWidget(btn_save_proxy)

        lay.addStretch()
        return page

    def _on_save_proxy(self):
        from .network_manager import NetworkManager

        proxy_cfg = {
            "enabled": self._chk_proxy.isChecked(),
            "type": self._combo_proxy_type.currentData(),
            "host": self._edit_proxy_host.text().strip(),
            "port": self._edit_proxy_port.text().strip(),
            "username": self._edit_proxy_user.text().strip(),
            "password": self._edit_proxy_pass.text(),
        }
        settings.proxy = proxy_cfg
        NetworkManager.apply(proxy_cfg)
        self.proxy_changed.emit()
        QMessageBox.information(self, self._t("sw_proxy_saved_title"), self._t("sw_proxy_saved_msg"))

    def _build_page_schedule(self) -> QWidget:
        page, lay = self._make_page("sw_schedule_title", spacing=16)

        self._chk_schedule = QCheckBox(self._t("sw_schedule_enable"))
        self._chk_schedule.setChecked(settings.auto_theme_schedule)
        self._chk_schedule.setStyleSheet(self._LABEL_STYLE)
        lay.addWidget(self._chk_schedule)

        self._combo_day_theme = QComboBox()
        self._combo_day_theme.setMinimumWidth(180)
        self._populate_combo(self._combo_day_theme, list_themes(), settings.day_theme)
        self._add_labeled_row(lay, self._t("sw_schedule_day_theme") + ":", self._combo_day_theme)

        self._spin_day_start = QSpinBox()
        self._spin_day_start.setRange(0, 23)
        self._spin_day_start.setValue(settings.day_start)
        self._spin_day_start.setSuffix(":00")
        self._spin_day_start.setStyleSheet(
            "QSpinBox { background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.2); border-radius:6px; color:white; padding:4px 8px; }"
        )
        self._add_labeled_row(lay, self._t("sw_schedule_day_start") + ":", self._spin_day_start)

        self._combo_night_theme = QComboBox()
        self._combo_night_theme.setMinimumWidth(180)
        self._populate_combo(self._combo_night_theme, list_themes(), settings.night_theme)
        self._add_labeled_row(lay, self._t("sw_schedule_night_theme") + ":", self._combo_night_theme)

        self._spin_night_start = QSpinBox()
        self._spin_night_start.setRange(0, 23)
        self._spin_night_start.setValue(settings.night_start)
        self._spin_night_start.setSuffix(":00")
        self._spin_night_start.setStyleSheet(
            "QSpinBox { background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.2); border-radius:6px; color:white; padding:4px 8px; }"
        )
        self._add_labeled_row(lay, self._t("sw_schedule_night_start") + ":", self._spin_night_start)

        btn_save = QPushButton(self._t("save"))
        btn_save.clicked.connect(self._on_save_schedule)
        lay.addWidget(btn_save)

        lay.addStretch()
        return page

    def _on_save_schedule(self):
        settings.auto_theme_schedule = self._chk_schedule.isChecked()
        settings.day_theme = self._combo_day_theme.currentData() or ""
        settings.night_theme = self._combo_night_theme.currentData() or ""
        settings.day_start = self._spin_day_start.value()
        settings.night_start = self._spin_night_start.value()

    def _on_open_site_toggled(self, checked: bool):
        settings.open_website_on_startup = checked

    def _on_performance_toggled(self, checked: bool):
        settings.performance_mode = checked

    def _on_language_changed(self, idx: int):
        lang = self._combo_lang.itemData(idx)
        if lang:
            settings.language = lang
            self.language_changed.emit(lang)

    def _apply_theme(self):
        self._theme_data.update(
            style_mode=settings.style_mode,
            font_family=settings.font_family,
            code_font_family=settings.code_font_family,
            font_size=settings.font_size,
        )
        # Settings remain typographically stable; the font picker previews each
        # family in its popup while the chosen font applies to the application.
        settings_theme = dict(self._theme_data)
        settings_theme.update(font_family="Segoe UI", code_font_family="Cascadia Mono", font_size=13)
        td = resolved_theme(settings_theme)
        self.setStyleSheet(
            build_workspace_qss(td)
            + f"""
            QDialog {{ background: {td["surface_base_color"]}; }}
            QListWidget {{ background: {td["surface_raised_color"]}; border: none; padding: 6px 0; }}
            QListWidget::item {{ min-height: 30px; padding: 4px 12px; color: {td["text_secondary_color"]}; }}
            QListWidget::item:selected {{ background: {td["accent_soft_color"]}; color: {td["accent_color"]};
                border-left: 3px solid {td["accent_color"]}; }}
            QStackedWidget {{ background: {td["surface_base_color"]}; }}
            QCheckBox {{ color: {td["text_primary_color"]}; spacing: 7px; }}
            QComboBox QAbstractItemView {{ background: {td["surface_overlay_color"]};
                color: {td["text_primary_color"]}; selection-background-color: {td["accent_soft_color"]}; }}
            """
        )
        self._nav.setStyleSheet("")
        self._stack.setStyleSheet("")
