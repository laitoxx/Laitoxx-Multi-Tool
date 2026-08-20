# ruff: noqa: F405
from .plugin_builder_context import *  # noqa: F403


class PluginBuilderMixin1:
    def update_theme(self, theme_data: dict):
        self._theme = resolved_theme(theme_data)
        self.setStyleSheet(
            build_workspace_qss(self._theme) + f"QDialog {{ background: {self._theme['surface_base_color']}; }}"
        )
        if hasattr(self, "editor"):
            self.editor.apply_theme(self._theme)
        if hasattr(self, "issues_area"):
            self.issues_area.setStyleSheet(
                f"background: {self._theme['surface_work_color']}; color: {self._theme['text_primary_color']};"
                f"border: 1px solid {self._theme['border_subtle_color']}; border-radius: 6px;"
            )
        if hasattr(self, "tip_label"):
            self.tip_label.setStyleSheet(
                f"color: {self._theme['text_secondary_color']}; font-style: italic; padding: 4px;"
            )

    def retranslate_ui(self):
        t = self.translator
        self.setWindowTitle(t.get("lua_builder_title"))
        self.meta_continue_btn.setText(t.get("continue"))
        self.meta_cancel_btn.setText(t.get("cancel"))
        self.btn_save.setText(t.get("save_plugin"))
        self.btn_check_syntax.setText(t.get("lua_check_syntax"))
        self.btn_snippets.setText(t.get("lua_insert_snippet"))
        self.btn_open_file.setText(t.get("lua_open_file"))

    def _create_meta_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Lua Plugin Builder")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()

        self.meta_name = QLineEdit()
        self.meta_name.setPlaceholderText("My Awesome Plugin")
        form.addRow("Plugin Name:", self.meta_name)

        self.meta_author = QLineEdit()
        self.meta_author.setPlaceholderText("Your Name")
        form.addRow("Author:", self.meta_author)

        self.meta_description = QTextEdit()
        self.meta_description.setFixedHeight(80)
        self.meta_description.setPlaceholderText("What does this plugin do?")
        form.addRow("Description:", self.meta_description)

        self.meta_type = QComboBox()
        self.meta_type.addItem("Search - query external sources", "search")
        self.meta_type.addItem("Processor - transform/enrich data", "processor")
        self.meta_type.addItem("Formatter - format/export results", "formatter")
        self.meta_type.addItem("Passive Scanner - analyze input", "passive_scanner")
        form.addRow("Plugin Type:", self.meta_type)

        # OS checkboxes
        os_widget = QWidget()
        os_layout = QHBoxLayout(os_widget)
        os_layout.setContentsMargins(0, 0, 0, 0)
        self.os_checks = {}
        for os_name in ["Windows", "Linux", "macOS"]:
            cb = QCheckBox(os_name)
            cb.setChecked(True)
            self.os_checks[os_name] = cb
            os_layout.addWidget(cb)
        form.addRow("Target OS:", os_widget)

        layout.addLayout(form)

        btn_box = QDialogButtonBox()
        self.meta_continue_btn = btn_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.meta_cancel_btn = btn_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._go_to_editor)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.stacked_widget.addWidget(page)

    def _go_to_editor(self):
        name = self.meta_name.text().strip()
        if not name:
            return

        target_os = [n for n, cb in self.os_checks.items() if cb.isChecked()]
        code = generate_plugin_template(
            plugin_name=name,
            plugin_type=self.meta_type.currentData(),
            author=self.meta_author.text().strip() or "Unknown",
            description=self.meta_description.toPlainText().strip(),
            target_os=target_os,
        )

        self.editor.setPlainText(code)
        self._current_filename = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower() + ".lua"
        self.setWindowTitle(f"Plugin Builder - {self._current_filename}")
        self.stacked_widget.setCurrentIndex(1)
        self._show_random_tip()

    def _create_editor_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # Toolbar
        toolbar = QHBoxLayout()

        self.btn_snippets = QPushButton()
        self.btn_snippets.setMenu(self._build_snippets_menu())
        toolbar.addWidget(self.btn_snippets)

        self.btn_check_syntax = QPushButton()
        self.btn_check_syntax.clicked.connect(self._check_syntax)
        toolbar.addWidget(self.btn_check_syntax)

        self.btn_open_file = QPushButton()
        self.btn_open_file.clicked.connect(self._open_lua_file)
        toolbar.addWidget(self.btn_open_file)

        toolbar.addStretch()

        self.btn_save = QPushButton()
        self.btn_save.clicked.connect(self._save_plugin)
        toolbar.addWidget(self.btn_save)

        layout.addLayout(toolbar)

        # Splitter: editor | issues panel
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Code editor
        self.editor = LuaCodeEditor()
        self._highlighter = LuaSyntaxHighlighter(self.editor.document())
        splitter.addWidget(self.editor)

        # Issues / output panel
        self.issues_area = QTextEdit()
        self.issues_area.setReadOnly(True)
        self.issues_area.setMaximumHeight(150)
        self.issues_area.setStyleSheet(
            "QTextEdit { background-color: #1e2127; color: #abb2bf;"
            " border: 1px solid #3e4451; border-radius: 4px; font-size: 12px; }"
        )
        self.issues_area.setFont(QFont("Consolas", 10))
        splitter.addWidget(self.issues_area)

        splitter.setSizes([500, 150])
        layout.addWidget(splitter)

        # Tip bar
        self.tip_label = QLabel()
        self.tip_label.setWordWrap(True)
        self.tip_label.setStyleSheet("color: #5c6370; font-style: italic; padding: 4px;")
        layout.addWidget(self.tip_label)

        self._current_filename = "new_plugin.lua"
        self.stacked_widget.addWidget(page)

    def _build_snippets_menu(self) -> QMenu:
        menu = QMenu(self)
        for key, snippet in CODE_SNIPPETS.items():
            action = menu.addAction(snippet["label"])
            action.setToolTip(snippet["description"])
            action.triggered.connect(lambda checked, k=key: self._insert_snippet(k))
        return menu

    def _insert_snippet(self, snippet_key: str):
        snippet = CODE_SNIPPETS[snippet_key]
        if snippet["fields"]:
            dlg = SnippetInsertDialog(self, snippet_key)
            if dlg.exec():
                self.editor.insert_snippet(dlg.get_code())
        else:
            self.editor.insert_snippet(snippet["template"])
        self._show_random_tip()

    def _check_syntax(self):
        source = self.editor.toPlainText()
        issues = check_lua_syntax(source)

        self.issues_area.clear()
        if not issues:
            self.issues_area.setHtml('<span style="color: #98c379;">&#10004; No issues found. Code looks good!</span>')
            return

        html_parts = []
        for issue in issues:
            color = "#e06c75" if issue["severity"] == "error" else "#e5c07b"
            icon = "&#10006;" if issue["severity"] == "error" else "&#9888;"
            html_parts.append(f'<span style="color:{color};">{icon} Line {issue["line"]}: {issue["message"]}</span>')
        self.issues_area.setHtml("<br>".join(html_parts))

    def _open_lua_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Lua Plugin", "lua_plugins", "Lua Files (*.lua);;All Files (*)"
        )
        if filepath:
            self._load_file(filepath)

    def _load_existing_plugin(self):
        self._load_file(self.plugin_path)
        self.stacked_widget.setCurrentIndex(1)

    def _load_file(self, filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                self.editor.setPlainText(f.read())
            self._current_filename = os.path.basename(filepath)
            self.plugin_path = filepath
            self.setWindowTitle(f"Plugin Builder - {self._current_filename}")
            self._show_random_tip()
        except Exception as e:
            self.issues_area.setText(f"Error loading file: {e}")
