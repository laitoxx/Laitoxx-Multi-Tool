"""Settings window — unified dialog with sections:
  • General (open website on startup, language)
  • Themes  (dropdown from resources/themes, theme editor button)
  • Background (dropdown + import file)
  • Proxy  (type, host, port, username, password)
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QStackedWidget, QWidget, QCheckBox, QComboBox,
    QLineEdit, QFileDialog, QMessageBox, QFormLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal

from .app_settings import settings
from .theme import list_themes, load_theme, save_theme_to_resources, DEFAULT_THEME
from .background import list_backgrounds, import_background, SUPPORTED_EXT


class SettingsWindow(QDialog):
    """Main settings dialog."""

    _PAGE_MARGINS = (24, 24, 24, 24)
    _TITLE_STYLE = "color:white; font-size:18px; font-weight:bold;"
    _LABEL_STYLE = "color:white; font-size:13px;"

    # Emitted when theme changes so MainWindow can re-apply immediately.
    theme_changed = pyqtSignal(dict, str)          # (theme_data, filepath)
    background_changed = pyqtSignal(str)            # new background path
    language_changed = pyqtSignal(str)              # "en" / "ru"
    proxy_changed = pyqtSignal()                    # proxy config updated

    def __init__(self, parent=None, theme_data: dict | None = None,
                 translator=None):
        super().__init__(parent)
        self._theme_data = theme_data or DEFAULT_THEME.copy()
        self._tr = translator  # may be None
        self.setWindowTitle(self._t("settings_window_title"))
        self.setMinimumSize(720, 500)
        self._build_ui()
        self._apply_theme()

    # ── Translation helper ─────────────────────────────────────────────────────

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

    # ── UI ─────────────────────────────────────────────────────────────────────

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
            ("sw_nav_general",    self._t("sw_nav_general")),
            ("sw_nav_themes",     self._t("sw_nav_themes")),
            ("sw_nav_background", self._t("sw_nav_background")),
            ("sw_nav_proxy",      self._t("sw_nav_proxy")),
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

        self._page_general    = self._build_page_general()
        self._page_themes     = self._build_page_themes()
        self._page_background = self._build_page_background()
        self._page_proxy      = self._build_page_proxy()

        for page in (self._page_general, self._page_themes,
                     self._page_background, self._page_proxy):
            self._stack.addWidget(page)

        root.addWidget(self._nav)
        root.addWidget(self._stack)

    def _on_nav_changed(self, idx: int):
        self._stack.setCurrentIndex(idx)
        if idx == 1:
            self._refresh_themes_list()
        elif idx == 2:
            self._refresh_bg_list()

    # ── Page: General ─────────────────────────────────────────────────────────

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
        return page

    # ── Page: Themes ──────────────────────────────────────────────────────────

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
            from gui.theme_editor import ThemeEditorDialog
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

    def _ask_theme_name(self) -> tuple[str, bool]:
        from PyQt6.QtWidgets import QInputDialog
        return QInputDialog.getText(self, self._t("sw_theme_name_title"),
                                    self._t("sw_theme_name_prompt"))

    # ── Page: Background ──────────────────────────────────────────────────────

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

    # ── Page: Proxy ───────────────────────────────────────────────────────────

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

        form.addRow(lbl("sw_proxy_type"),     self._combo_proxy_type)
        form.addRow(lbl("sw_proxy_host"),     self._edit_proxy_host)
        form.addRow(lbl("sw_proxy_port"),     self._edit_proxy_port)
        form.addRow(lbl("sw_proxy_username"), self._edit_proxy_user)
        form.addRow(lbl("sw_proxy_password"), self._edit_proxy_pass)

        lay.addWidget(form_widget)

        btn_save_proxy = QPushButton(self._t("sw_proxy_save"))
        btn_save_proxy.clicked.connect(self._on_save_proxy)
        lay.addWidget(btn_save_proxy)

        lay.addStretch()
        return page

    def _on_save_proxy(self):
        from .proxy import apply_proxy_settings
        from .network_manager import NetworkManager
        proxy_cfg = {
            "enabled":  self._chk_proxy.isChecked(),
            "type":     self._combo_proxy_type.currentData(),
            "host":     self._edit_proxy_host.text().strip(),
            "port":     self._edit_proxy_port.text().strip(),
            "username": self._edit_proxy_user.text().strip(),
            "password": self._edit_proxy_pass.text(),
        }
        settings.proxy = proxy_cfg
        apply_proxy_settings(proxy_cfg)   # legacy env/session compat
        NetworkManager.apply(proxy_cfg)   # installs/removes OS-level guards
        self.proxy_changed.emit()
        QMessageBox.information(self, self._t("sw_proxy_saved_title"),
                                self._t("sw_proxy_saved_msg"))

    # ── General page callbacks ────────────────────────────────────────────────

    def _on_open_site_toggled(self, checked: bool):
        settings.open_website_on_startup = checked

    def _on_performance_toggled(self, checked: bool):
        settings.performance_mode = checked

    def _on_language_changed(self, idx: int):
        lang = self._combo_lang.itemData(idx)
        if lang:
            settings.language = lang
            self.language_changed.emit(lang)

    # ── Theme application helper ──────────────────────────────────────────────

    def _apply_theme(self):
        td = self._theme_data
        btn_style = (
            f"QPushButton {{"
            f" background-color: {td.get('button_bg_color','rgba(255,0,0,0.1)')};"
            f" border: 1px solid {td.get('button_border_color','rgba(255,255,255,0.2)')};"
            f" border-radius: 8px; color: {td.get('button_text_color','white')};"
            f" padding: 8px 16px; font-size: 13px; }}"
            f"QPushButton:hover {{ background-color: {td.get('button_hover_bg_color','rgba(255,0,0,0.2)')}; }}"
            f"QPushButton:pressed {{ background-color: {td.get('button_pressed_bg_color','rgba(255,0,0,0.3)')}; }}"
        )
        combo_style = (
            "QComboBox { background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.2);"
            " border-radius:6px; color:white; padding:4px 8px; }"
            "QComboBox::drop-down { border:none; }"
            "QComboBox QAbstractItemView { background:#1e1e1e; color:white; selection-background-color:rgba(200,80,80,0.5); }"
        )
        edit_style = (
            "QLineEdit { background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.2);"
            " border-radius:6px; color:white; padding:4px 8px; }"
        )
        check_style = "QCheckBox { color:white; font-size:13px; }"
        self.setStyleSheet(
            f"QDialog {{ background: rgba(20,20,20,0.95); }}"
            + btn_style + combo_style + edit_style + check_style
        )
