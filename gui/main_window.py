import os
import logging
import contextlib

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QPlainTextEdit, QSplitter, QSpacerItem, QSizePolicy,
    QLineEdit, QFileDialog, QInputDialog, QApplication, QMenu, QMessageBox,
)
from PyQt6.QtGui import QMovie, QResizeEvent, QFont, QTextCursor
from PyQt6.QtCore import Qt, QUrl, QThread
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QGraphicsBlurEffect

from gui.translator import translator
from settings.app_settings import settings
from settings.theme import (
    DEFAULT_THEME,
    load_theme,
    save_theme_to_resources,
    load_default_theme,
)
from settings.background import default_background, import_background
from settings.paths import ensure_resource_dirs, DEFAULT_THEME_FILE
from settings.settings_window import SettingsWindow
from settings.proxy import apply_proxy_settings
from gui.worker import Worker, SignalWriter, remove_ansi_codes, _InputOverride
from gui.terminal_window import TerminalWindow
from gui.dialogs import (
    CustomInputDialog, TelegramSearchDialog,
    HashToolsDialog, JwtAnalyzerDialog, WebSecurityDialog,
    TextTransformerDialog, PasswordGeneratorDialog,
    RegexTesterDialog, CidrCalculatorDialog,
    LuaPluginInputDialog, LuaPluginConfigDialog,
)
from gui.theme_editor import ThemeEditorDialog
from plugin_builder import PluginBuilderWindow
from gui.graph_editor import GraphEditorWindow
from gui.username_osint_window import UsernameOsintWindow
from gui.image_search_window import ImageSearchWindow
from gui.tool_registry import TOOL_REGISTRY, CATEGORIES

try:
    from lua_engine import (
        discover_lua_plugins, load_lua_plugin_settings,
        save_lua_plugin_settings, apply_settings_to_plugins,
    )
    HAS_LUA = True
except ImportError:
    HAS_LUA = False


class GlassButton(QPushButton):
    pass


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        logging.info("MainWindow.__init__ started.")
        self.tool_registry = TOOL_REGISTRY
        self.categories = CATEGORIES
        self.running_tools = {}
        self.plugin_builder_window = None
        self.unhide_button = None
        self.lua_plugins: list = []
        self._terminal_window: TerminalWindow | None = None
        self._graph_editor_window = None
        self._username_osint_window = None
        self._image_search_window = None

        ensure_resource_dirs()
        apply_proxy_settings(settings.proxy)
        translator.set_language(settings.language)

        self.load_initial_theme()
        self._build_ui()
        self.load_lua_plugins()
        self.retranslate_ui()
        self._load_and_set_initial_background()
        logging.info("MainWindow.__init__ finished.")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.main_container = QWidget()
        self.setCentralWidget(self.main_container)

        # Background layer
        self.background_container = QStackedWidget(self.main_container)
        self.gif_label = QLabel()
        self.gif_label.setScaledContents(True)
        self.video_widget = QVideoWidget()
        self.background_container.addWidget(self.gif_label)
        self.background_container.addWidget(self.video_widget)

        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video_widget)
        self.player.setLoops(-1)
        self._apply_performance_mode()

        # UI layer
        self.ui_container = QWidget(self.main_container)
        self.ui_container.setStyleSheet("background:transparent;")

        self._build_sidebar()
        self._build_main_content()
        self._build_active_tools_panel()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.sidebar_widget)
        self.splitter.addWidget(self._main_content_widget)
        self.splitter.addWidget(self.active_tools_widget)
        self.splitter.setSizes([150, 1050, 150])
        self.splitter.setStyleSheet("QSplitter::handle { background-color: transparent; }")

        ui_layout = QHBoxLayout(self.ui_container)
        ui_layout.addWidget(self.splitter)
        ui_layout.setContentsMargins(0, 0, 0, 0)

    def _build_sidebar(self):
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setMaximumWidth(200)
        layout = QVBoxLayout(self.sidebar_widget)

        self.btn_settings = GlassButton("")
        self.btn_load_theme = GlassButton("")
        self.btn_create_theme = GlassButton("")
        self.btn_plugin_builder = GlassButton("")
        self.btn_graph_editor = GlassButton("")
        self.btn_lang_switch = GlassButton("RU/EN")
        self.btn_hide_ui = GlassButton("")
        self.btn_exit = GlassButton("")

        for btn in (self.btn_settings, self.btn_load_theme, self.btn_create_theme,
                    self.btn_plugin_builder, self.btn_graph_editor, self.btn_lang_switch, self.btn_hide_ui):
            layout.addWidget(btn)
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        layout.addWidget(self.btn_exit)

        self.btn_settings.clicked.connect(self._open_settings)
        self.btn_load_theme.clicked.connect(self._load_theme_from_file)
        self.btn_create_theme.clicked.connect(self._create_new_theme)
        self.btn_plugin_builder.clicked.connect(self._open_plugin_builder)
        self.btn_graph_editor.clicked.connect(self._open_graph_editor)
        self.btn_lang_switch.clicked.connect(self._switch_language)
        self.btn_hide_ui.clicked.connect(self._toggle_ui_visibility)
        self.btn_exit.clicked.connect(self.close)

    def _build_main_content(self):
        self._main_content_widget = QWidget()
        layout = QVBoxLayout(self._main_content_widget)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(translator.get("search"))
        self.search_bar.textChanged.connect(self._filter_tools)
        layout.addWidget(self.search_bar)

        self.stacked_widget = QStackedWidget()
        self.output_area = QPlainTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumBlockCount(2000)

        # Output header row with pop-out button
        output_header = QHBoxLayout()
        output_header.setContentsMargins(0, 2, 0, 0)
        output_header.setSpacing(6)
        output_header.addStretch()
        self._btn_popout = QPushButton("⧉ " + translator.get("terminal"))
        self._btn_popout.setFixedHeight(22)
        self._btn_popout.setToolTip(translator.get("terminal_tooltip"))
        self._btn_popout.setCheckable(True)
        self._btn_popout.clicked.connect(self._toggle_terminal_window)
        output_header.addWidget(self._btn_popout)

        layout.addWidget(self.stacked_widget)
        layout.addLayout(output_header)
        layout.addWidget(self.output_area)
        layout.setStretch(1, 2)
        layout.setStretch(3, 1)

    def _append_output(self, text: str) -> None:
        if not text:
            return
        cursor = self.output_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.output_area.setTextCursor(cursor)
        self.output_area.ensureCursorVisible()
        if self._terminal_window and self._terminal_window.isVisible():
            self._terminal_window.append_text(text)

    def _set_output(self, text: str) -> None:
        self.output_area.setPlainText(text or "")
        if self._terminal_window and self._terminal_window.isVisible():
            self._terminal_window.set_text(text or "")

    def _build_active_tools_panel(self):
        self.active_tools_widget = QWidget()
        self.active_tools_widget.setMaximumWidth(200)
        layout = QVBoxLayout(self.active_tools_widget)
        layout.addWidget(QLabel("Active Tools"))
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------

    def _apply_performance_mode(self):
        """Toggle visual effects that affect performance."""
        perf = bool(settings.performance_mode)
        # Blur effect is expensive on large video surfaces
        if perf:
            self.background_container.setGraphicsEffect(None)
        else:
            self.background_container.setGraphicsEffect(QGraphicsBlurEffect(blurRadius=10))

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.background_container.setGeometry(self.rect())
        self.ui_container.setGeometry(self.rect())
        self.ui_container.raise_()

    def _set_background(self, path):
        self.player.stop()
        if not path or not os.path.exists(path):
            path = default_background()
        if not path or not os.path.exists(path):
            self._set_output("Background file not found.")
            return
        try:
            bg_dir = os.path.abspath(os.path.dirname(default_background()))
            if not os.path.abspath(path).startswith(bg_dir):
                path = import_background(path)
        except OSError:
            pass
        _, ext = os.path.splitext(path.lower())
        if ext == ".gif":
            movie = QMovie(path)
            movie.setCacheMode(QMovie.CacheMode.CacheNone)
            if movie.isValid():
                self.gif_label.setMovie(movie)
                movie.start()
                self.background_container.setCurrentWidget(self.gif_label)
        elif ext in (".mp4", ".avi"):
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            self.background_container.setCurrentWidget(self.video_widget)
            self.player.play()
        else:
            self._set_output(f"Unsupported file format: {ext}")
            return
        settings.background_path = path

    def _load_and_set_initial_background(self):
        path = settings.background_path or default_background()
        self._set_background(path)

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def load_initial_theme(self, use_last_saved=True):
        self.theme_data = load_default_theme()
        if use_last_saved:
            theme_path = settings.theme_path
            if theme_path:
                saved = load_theme(theme_path)
                if saved:
                    self.theme_data.update(saved)
                else:
                    settings.theme_path = DEFAULT_THEME_FILE

    def apply_theme(self):
        td = DEFAULT_THEME.copy()
        td.update(self.theme_data or {})
        btn = (
            f"QPushButton {{"
            f" background-color: {td['button_bg_color']};"
            f" border: 1px solid {td['button_border_color']};"
            f" border-radius: 10px; color: {td['button_text_color']};"
            f" padding: 10px; font-size: 14px; }}"
            f"QPushButton:hover {{ background-color: {td['button_hover_bg_color']}; }}"
            f"QPushButton:pressed {{ background-color: {td['button_pressed_bg_color']}; }}"
        )
        self.setStyleSheet(btn)
        if self.unhide_button:
            self.unhide_button.setStyleSheet(btn)
        self.sidebar_widget.setStyleSheet(
            f"background-color: {td['sidebar_bg_color']}; border-radius: 10px;"
        )
        self.active_tools_widget.setStyleSheet(
            f"background-color: {td['sidebar_bg_color']}; border-radius: 10px;"
        )
        scrollbar = (
            f"QScrollBar:vertical {{ border: none; background: transparent; width: 8px;"
            f" margin: 0; border-radius: 4px; }}"
            f"QScrollBar::handle:vertical {{ background-color: rgba(160,160,160,0.85);"
            f" min-height: 24px; border-radius: 4px; }}"
            f"QScrollBar::handle:vertical:hover {{ background-color: rgba(200,200,200,0.95); }}"
            f"QScrollBar::handle:vertical:pressed {{ background-color: rgba(220,220,220,1.0); }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}"
            f"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}"
            f"QScrollBar:horizontal {{ border: none; background: transparent; height: 8px;"
            f" margin: 0; border-radius: 4px; }}"
            f"QScrollBar::handle:horizontal {{ background-color: rgba(160,160,160,0.85);"
            f" min-width: 24px; border-radius: 4px; }}"
            f"QScrollBar::handle:horizontal:hover {{ background-color: rgba(200,200,200,0.95); }}"
            f"QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}"
            f"QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}"
        )
        text_area = (
            f"QPlainTextEdit {{ background-color: {td['text_area_bg_color']};"
            f" border: 1px solid {td['text_area_border_color']};"
            f" border-radius: 10px; color: {td['text_area_text_color']}; font-size: 14px; }}"
        )
        self.output_area.setStyleSheet(text_area + scrollbar)
        # Apply scrollbar style globally to the entire application
        QApplication.instance().setStyleSheet(scrollbar)
        # Update terminal window theme if open
        if self._terminal_window:
            self._terminal_window.update_theme(td)
        # Update detached windows theme if open
        if self._graph_editor_window and self._graph_editor_window.isVisible():
            self._graph_editor_window.update_theme(td)
        if self._username_osint_window and self._username_osint_window.isVisible():
            self._username_osint_window.update_theme(td)
        if self._image_search_window and self._image_search_window.isVisible():
            self._image_search_window.update_theme(td)
        for label in self.findChildren(QLabel):
            try:
                if label.property("is_title"):
                    label.setStyleSheet(
                        f"color: {td['title_text_color']}; padding-top: 10px; background: transparent;"
                    )
            except RuntimeError:
                # QLabel was deleted during UI rebuild/retranslate
                continue
        self.stacked_widget.setStyleSheet("background: transparent;")
        for i in range(self.stacked_widget.count()):
            self.stacked_widget.widget(i).setStyleSheet("background: transparent;")

    def _load_theme_from_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, translator.get("change_theme"), "", "JSON Files (*.json)")
        if filepath:
            new_theme = load_theme(filepath)
            if new_theme:
                self.theme_data.update(new_theme)
                self.apply_theme()
                name = os.path.splitext(os.path.basename(filepath))[0]
                saved_path = save_theme_to_resources(name, self.theme_data)
                settings.theme_path = saved_path
            else:
                self._set_output(translator.get("load_theme_error"))

    def _create_new_theme(self):
        editor = ThemeEditorDialog(self, self.theme_data)
        if editor.exec():
            self.theme_data = editor.get_theme_data()
            name, ok = QInputDialog.getText(
                self, translator.get("theme_name_title"), translator.get("theme_name_prompt")
            )
            if ok and name:
                saved_path = save_theme_to_resources(name, self.theme_data)
                settings.theme_path = saved_path
                logging.info(translator.get("theme_saved_success", path=saved_path))
        self.apply_theme()

    # ------------------------------------------------------------------
    # Settings Window
    # ------------------------------------------------------------------

    def _open_settings(self):
        dlg = SettingsWindow(self, theme_data=self.theme_data, translator=translator)
        dlg.theme_changed.connect(self._on_settings_theme_changed)
        dlg.background_changed.connect(self._on_settings_background_changed)
        dlg.language_changed.connect(self._on_settings_language_changed)
        dlg.proxy_changed.connect(self._on_settings_proxy_changed)
        dlg.exec()
        self._apply_performance_mode()

    def _on_settings_theme_changed(self, theme_data: dict, _path: str):
        self.theme_data = theme_data
        self.apply_theme()

    def _on_settings_background_changed(self, path: str):
        self._set_background(path)

    def _on_settings_language_changed(self, lang: str):
        translator.set_language(lang)
        self.retranslate_ui()

    def _on_settings_proxy_changed(self):
        apply_proxy_settings(settings.proxy)

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------

    def _switch_language(self):
        new_lang = 'ru' if translator.lang == 'en' else 'en'
        translator.set_language(new_lang)
        settings.language = new_lang
        self.retranslate_ui()

    def retranslate_ui(self):
        self.setWindowTitle(translator.get("app_title"))
        self.search_bar.setPlaceholderText(translator.get("search"))
        self.btn_settings.setText(translator.get("settings"))
        self.btn_load_theme.setText(translator.get("change_theme"))
        self.btn_create_theme.setText(translator.get("create_color_theme"))
        self.btn_plugin_builder.setText(translator.get("plugin_builder"))
        self.btn_graph_editor.setText(translator.get("graph_editor"))
        self.btn_hide_ui.setText(translator.get("hide_ui"))
        self.btn_exit.setText(translator.get("exit"))
        self._btn_popout.setText("⧉ " + translator.get("terminal"))
        self._btn_popout.setToolTip(translator.get("terminal_tooltip"))
        if self.unhide_button:
            self.unhide_button.setText(translator.get("show_ui"))
        if self.plugin_builder_window:
            self.plugin_builder_window.retranslate_ui()
        self.reload_plugins_and_ui()

    # ------------------------------------------------------------------
    # UI visibility
    # ------------------------------------------------------------------

    def _toggle_ui_visibility(self):
        if self.ui_container.isVisible():
            self.ui_container.hide()
            self._show_unhide_button()
        else:
            self.ui_container.show()
            self._hide_unhide_button()

    def _show_unhide_button(self):
        if not self.unhide_button:
            self.unhide_button = QPushButton(translator.get("show_ui"), self)
            self.unhide_button.setFixedSize(100, 40)
            self.unhide_button.move(10, 10)
            self.unhide_button.clicked.connect(self._toggle_ui_visibility)
        else:
            self.unhide_button.setText(translator.get("show_ui"))
        self.unhide_button.setStyleSheet(self.styleSheet())
        self.unhide_button.show()
        self.unhide_button.raise_()

    def _hide_unhide_button(self):
        if self.unhide_button:
            self.unhide_button.hide()

    # ------------------------------------------------------------------
    # Plugins (Lua only)
    # ------------------------------------------------------------------

    def _open_plugin_builder(self):
        self.plugin_builder_window = PluginBuilderWindow(self, translator=translator)
        if self.plugin_builder_window.exec():
            self.reload_plugins_and_ui()
        self.plugin_builder_window = None

    def _open_username_osint(self):
        if self._username_osint_window and self._username_osint_window.isVisible():
            self._username_osint_window.raise_()
            self._username_osint_window.activateWindow()
            return
        dlg = UsernameOsintWindow(
            None, theme_data=self.theme_data,
            lua_plugins=self.lua_plugins,
        )
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dlg.finished.connect(lambda: setattr(self, '_username_osint_window', None))
        self._username_osint_window = dlg
        dlg.show()

    def _open_graph_editor(self):
        if self._graph_editor_window and self._graph_editor_window.isVisible():
            self._graph_editor_window.raise_()
            self._graph_editor_window.activateWindow()
            return
        editor = GraphEditorWindow(
            None, theme_data=self.theme_data,
            lua_plugins=self.lua_plugins,
        )
        editor.run_action_requested.connect(self._on_graph_action)
        editor.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        editor.finished.connect(lambda: setattr(self, '_graph_editor_window', None))
        self._graph_editor_window = editor
        editor.show()

    # ------------------------------------------------------------------
    # Pop-out terminal
    # ------------------------------------------------------------------

    def _toggle_terminal_window(self, checked: bool):
        if checked:
            self._terminal_window = TerminalWindow(self.theme_data, parent=None)
            # Seed with current content
            self._terminal_window.set_text(self.output_area.toPlainText())
            self._terminal_window.closed.connect(self._on_terminal_closed)
            self._terminal_window.show()
        else:
            if self._terminal_window:
                self._terminal_window.close()

    def _on_terminal_closed(self):
        self._terminal_window = None
        self._btn_popout.setChecked(False)

    def load_lua_plugins(self):
        """Discover and load Lua plugins from the lua_plugins directory."""
        self.lua_plugins = []
        if not HAS_LUA:
            logging.warning("lupa not installed — Lua plugins disabled.")
            return
        try:
            self.lua_plugins = discover_lua_plugins()
            settings = load_lua_plugin_settings()
            apply_settings_to_plugins(self.lua_plugins, settings)
            logging.info(f"Loaded {len(self.lua_plugins)} Lua plugin(s).")
        except Exception as e:
            logging.error(f"Error loading Lua plugins: {e}", exc_info=True)

    def reload_plugins_and_ui(self):
        self.load_lua_plugins()
        for i in reversed(range(self.stacked_widget.count())):
            w = self.stacked_widget.widget(i)
            self.stacked_widget.removeWidget(w)
            if w:
                w.deleteLater()
        self._create_categorized_menu()
        self.apply_theme()

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------

    def _create_categorized_menu(self):
        self.tool_widgets = {}
        menu_widget = QWidget()
        layout = QHBoxLayout(menu_widget)

        categories = dict(self.categories)

        # Single "plugins" category for all Lua plugins
        enabled_lua = [p for p in self.lua_plugins if p.enabled]
        if enabled_lua:
            categories["plugins"] = [p.name for p in enabled_lua]

        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)

        for cat_key, tool_keys in categories.items():
            col = QWidget()
            col_layout = QVBoxLayout(col)

            title = QLabel(translator.get(cat_key))
            title.setFont(title_font)
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setProperty("is_title", True)
            col_layout.addWidget(title)

            self.tool_widgets[cat_key] = {'title': title, 'buttons': [], 'widget': col}

            for key in tool_keys:
                btn = self._make_tool_button(cat_key, key)
                if btn:
                    col_layout.addWidget(btn)
                    self.tool_widgets[cat_key]['buttons'].append(btn)

            col_layout.addSpacerItem(
                QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
            )
            layout.addWidget(col)

        self.stacked_widget.addWidget(menu_widget)

    def _make_tool_button(self, cat_key, tool_key):
        if cat_key == "plugins":
            lua_p = next((p for p in self.lua_plugins if p.name == tool_key), None)
            if lua_p:
                btn = GlassButton(lua_p.name)
                tooltip = f"{lua_p.description}\n[{lua_p.plugin_type}] v{lua_p.version} by {lua_p.author}"
                btn.setToolTip(tooltip)
                btn.clicked.connect(lambda _, p=lua_p: self._run_lua_plugin_dispatcher(p))
                btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                btn.customContextMenuRequested.connect(
                    lambda pos, p=lua_p: self._show_lua_plugin_context_menu(p, pos, btn)
                )
                return btn
            return None

        info = self.tool_registry.get(tool_key)
        if not info:
            return None
        label = "Temporarily Unavailable" if info.disabled else translator.get(tool_key)
        btn = GlassButton(label)
        btn.setToolTip(info.desc or "")
        btn.setEnabled(not info.disabled)
        btn.clicked.connect(lambda _, t=tool_key: self._run_tool_dispatcher(t))
        return btn

    def _filter_tools(self, text):
        search = text.lower()
        for data in self.tool_widgets.values():
            any_visible = False
            for btn in data['buttons']:
                visible = search in btn.text().lower()
                btn.setVisible(visible)
                if visible:
                    any_visible = True
            data['title'].setVisible(any_visible)
            data['widget'].setVisible(any_visible)

    # ------------------------------------------------------------------
    # Tool dispatchers
    # ------------------------------------------------------------------

    def _run_tool_dispatcher(self, tool_name):
        self.output_area.clear()
        info = self.tool_registry.get(tool_name)
        if not info:
            self._set_output(f"Error: Tool '{tool_name}' not defined.")
            return

        input_data, ok = self._collect_input(tool_name, info)
        if not ok:
            self._set_output(translator.get("operation_cancelled"))
            return

        if info.threaded:
            self._run_threaded(tool_name, info.func, input_data)
        elif isinstance(input_data, dict):
            self._execute_dict_tool(info.func, input_data)
        else:
            self._execute_tool(info.func, input_data)

    def _collect_input(self, tool_name, info):
        input_type = info.input_type
        if input_type is None:
            return None, True
        if input_type == "text":
            prompt = info.prompt or "Enter value:"
            dlg = CustomInputDialog(self, title=tool_name, prompt=prompt)
            if dlg.exec() and dlg.get_text():
                return dlg.get_text(), True
        elif input_type == "telegram":
            dlg = TelegramSearchDialog(self)
            if dlg.exec() and dlg.get_values():
                return dlg.get_values(), True
        elif input_type == "hash":
            dlg = HashToolsDialog(self, tool_name)
            if dlg.exec() and dlg.get_values():
                return dlg.get_values(), True
        elif input_type == "google_osint":
            from script.tools.google_osint import GoogleOsintDialog
            dlg = GoogleOsintDialog(self)
            if dlg.exec():
                return None, True
        elif input_type == "jwt":
            dlg = JwtAnalyzerDialog(self, tool_name)
            if dlg.exec() and dlg.get_values():
                return dlg.get_values(), True
        elif input_type == "web_security":
            dlg = WebSecurityDialog(self, tool_name)
            if dlg.exec() and dlg.get_values():
                return dlg.get_values(), True
        elif input_type == "text_transformer":
            dlg = TextTransformerDialog(self, tool_name)
            if dlg.exec() and dlg.get_values():
                return dlg.get_values(), True
        elif input_type == "password_gen":
            dlg = PasswordGeneratorDialog(self, tool_name)
            if dlg.exec() and dlg.get_values():
                return dlg.get_values(), True
        elif input_type == "regex":
            dlg = RegexTesterDialog(self, tool_name)
            if dlg.exec() and dlg.get_values():
                return dlg.get_values(), True
        elif input_type == "cidr":
            dlg = CidrCalculatorDialog(self, tool_name)
            if dlg.exec() and dlg.get_values():
                return dlg.get_values(), True
        elif input_type == "username_osint_dialog":
            self._open_username_osint()
            return None, False
        elif input_type == "image_search":
            dlg = ImageSearchWindow(self)
            self._image_search_window = dlg
            dlg.exec()
            self._image_search_window = None
            return None, False
        return None, False

    def _handle_worker_error(self, message: str) -> None:
        self._append_output(f"\n[ERROR] {message}\n")

    def _start_worker_thread(
        self,
        tool_name: str,
        worker: Worker,
        *,
        start_message: str | None = None,
        connect_graph: bool = False,
    ) -> None:
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        worker.update.connect(self._append_output)
        worker.error.connect(self._handle_worker_error)
        if connect_graph:
            worker.graph_ready.connect(self._on_graph_ready)
        thread.start()
        self._add_running_tool(tool_name, thread, worker)
        if start_message:
            self._set_output(start_message)
        self._current_thread = thread
        self._current_worker = worker

    def _run_threaded(self, tool_name, func, input_data):
        worker = Worker(func, input_data)
        self._start_worker_thread(
            tool_name,
            worker,
            start_message=f"Running {tool_name} in the background...",
        )

    def _execute_tool(self, func, input_data):
        try:
            writer = SignalWriter(self._append_output, transform=remove_ansi_codes)
            with _InputOverride(input_data or ""), contextlib.redirect_stdout(writer):
                func()
            writer.flush()
        except Exception as e:
            self._set_output(f"An error occurred: {e}")

    def _execute_dict_tool(self, func, data):
        try:
            writer = SignalWriter(self._append_output, transform=remove_ansi_codes)
            with contextlib.redirect_stdout(writer):
                func(data)
            writer.flush()
        except Exception as e:
            self._set_output(f"An error occurred: {e}")

    # ------------------------------------------------------------------
    # Lua plugin dispatcher
    # ------------------------------------------------------------------

    def _run_lua_plugin_dispatcher(self, plugin_meta):
        self.output_area.clear()

        func_map = {
            "search": "search",
            "processor": "search",
            "formatter": "format",
            "passive_scanner": "search",
        }
        func_name = func_map.get(plugin_meta.plugin_type, "search")

        dlg = LuaPluginInputDialog(self, plugin_meta)
        if not dlg.exec():
            self._set_output(translator.get("operation_cancelled"))
            return
        query = dlg.get_query()
        if not query:
            self._set_output(translator.get("input_empty"))
            return

        worker = Worker(
            None, query,
            is_lua_plugin=True,
            lua_plugin_meta=plugin_meta,
            lua_function_name=func_name,
        )
        self._start_worker_thread(
            plugin_meta.name,
            worker,
            start_message=f"Running Lua plugin '{plugin_meta.name}'...\n",
            connect_graph=True,
        )

    def _on_graph_ready(self, graph_path: str):
        """Called when a Lua plugin saves a graph file. Ask user to open it."""
        self._append_output(f"\n[Graph] Граф сохранён: {graph_path}")
        reply = QMessageBox.question(
            self,
            translator.get("graph_editor"),
            translator.get("graph_open_prompt", path=graph_path),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from gui.graph_model import Graph
                graph = Graph.load_json(graph_path)
                editor = GraphEditorWindow(self, theme_data=self.theme_data,
                                          lua_plugins=self.lua_plugins)
                editor.run_action_requested.connect(self._on_graph_action)
                editor._graph = graph
                editor._current_filepath = graph_path
                editor._graph_name_edit.setText(graph.name)
                idx = editor._dir_combo.findText(graph.direction)
                if idx >= 0:
                    editor._dir_combo.setCurrentIndex(idx)
                editor._refresh_all()
                editor.exec()
            except Exception as e:
                self._append_output(f"\n[ERROR] Failed to open graph: {e}")

    def _on_graph_action(self, action_type: str, action_data, value: str):
        """Handle an action request from the Graph Editor."""
        if action_type == "builtin":
            tool_name = action_data
            if tool_name not in self.tool_registry:
                self._set_output(f"[ERROR] Tool '{tool_name}' not found.")
                return
            self.output_area.clear()
            self._set_output(
                f"{translator.get('ge_act_running')}: {tool_name}\n"
                f"{translator.get('ge_act_value')}: {value}\n{'─' * 40}\n"
            )
            tool_info = self.tool_registry[tool_name]
            func = tool_info.func
            if tool_info.threaded:
                worker = Worker(func, value)
                self._start_worker_thread(tool_name, worker)
            else:
                try:
                    result = func(value) if callable(func) else str(func)
                    self._append_output(str(result) if result else "Done.")
                except Exception as e:
                    self._append_output(f"[ERROR] {e}")

        elif action_type == "plugin":
            plugin_meta = action_data
            self.output_area.clear()
            self._set_output(
                f"{translator.get('ge_act_running')}: {plugin_meta.name}\n"
                f"{translator.get('ge_act_value')}: {value}\n{'─' * 40}\n"
            )
            worker = Worker(
                None, value,
                is_lua_plugin=True,
                lua_plugin_meta=plugin_meta,
                lua_function_name="search",
            )
            self._start_worker_thread(
                plugin_meta.name,
                worker,
                connect_graph=True,
            )

    def _show_lua_plugin_context_menu(self, plugin_meta, pos, button):
        menu = QMenu(self)
        settings_action = menu.addAction(translator.get("lua_plugin_settings"))
        edit_action = menu.addAction(translator.get("lua_plugin_edit"))
        reload_action = menu.addAction(translator.get("lua_plugin_reload"))
        disable_action = menu.addAction(
            translator.get("lua_plugin_disable") if plugin_meta.enabled
            else translator.get("lua_plugin_enable")
        )

        action = menu.exec(button.mapToGlobal(pos))
        if action == settings_action:
            self._open_lua_plugin_settings(plugin_meta)
        elif action == edit_action:
            self._edit_lua_plugin(plugin_meta)
        elif action == reload_action:
            self.reload_plugins_and_ui()
            self._set_output(translator.get("lua_plugins_reloaded"))
        elif action == disable_action:
            plugin_meta.enabled = not plugin_meta.enabled
            self._save_lua_plugin_state()
            self.reload_plugins_and_ui()

    def _edit_lua_plugin(self, plugin_meta):
        """Open the plugin builder to edit an existing Lua plugin."""
        builder = PluginBuilderWindow(
            self, plugin_path=plugin_meta.filepath, translator=translator
        )
        if builder.exec():
            self.reload_plugins_and_ui()

    def _open_lua_plugin_settings(self, plugin_meta):
        dlg = LuaPluginConfigDialog(self, plugin_meta)
        if dlg.exec():
            plugin_meta.config_values = dlg.get_config()
            self._save_lua_plugin_state()
            self._set_output(
                translator.get("lua_plugin_settings_saved", name=plugin_meta.name)
            )

    def _save_lua_plugin_state(self):
        """Persist Lua plugin enabled/disabled state and config values."""
        if not HAS_LUA:
            return
        settings = load_lua_plugin_settings()
        for p in self.lua_plugins:
            settings[p.id] = {
                "enabled": p.enabled,
                "config": p.config_values,
            }
        save_lua_plugin_settings(settings)

    # ------------------------------------------------------------------
    # Active tools panel
    # ------------------------------------------------------------------

    def _add_running_tool(self, tool_name, thread, worker):
        if tool_name in self.running_tools:
            return
        label = QLabel(tool_name)
        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(lambda: self._stop_tool(tool_name))
        layout = self.active_tools_widget.layout()
        layout.insertWidget(layout.count() - 1, label)
        layout.insertWidget(layout.count() - 1, stop_btn)
        self.running_tools[tool_name] = {
            'thread': thread,
            'worker': worker,
            'label': label,
            'stop_button': stop_btn,
        }
        thread.finished.connect(lambda: self._remove_running_tool(tool_name))

    def _remove_running_tool(self, tool_name):
        if tool_name not in self.running_tools:
            return
        layout = self.active_tools_widget.layout()
        entry = self.running_tools.pop(tool_name)
        layout.removeWidget(entry['label'])
        layout.removeWidget(entry['stop_button'])
        entry['label'].deleteLater()
        entry['stop_button'].deleteLater()

    def _stop_tool(self, tool_name):
        if tool_name in self.running_tools:
            entry = self.running_tools[tool_name]
            worker = entry.get('worker')
            if worker:
                try:
                    worker.cancel()
                except Exception:
                    pass
            thread = entry.get('thread')
            if thread:
                try:
                    thread.requestInterruption()
                except Exception:
                    pass
                thread.quit()
            self._remove_running_tool(tool_name)
