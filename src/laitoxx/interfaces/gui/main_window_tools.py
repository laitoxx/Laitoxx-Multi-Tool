"""Main window responsibility mixin."""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.interfaces.gui.command_palette import CommandPalette
from laitoxx.interfaces.gui.graph_editor import GraphEditorWindow
from laitoxx.interfaces.gui.plugin_builder import PluginBuilderWindow
from laitoxx.interfaces.gui.terminal_window import TerminalWindow
from laitoxx.interfaces.gui.username_osint_window import UsernameOsintWindow

try:
    from laitoxx.app.plugins.engine import (
        apply_settings_to_plugins,
        discover_lua_plugins,
        load_lua_plugin_settings,
    )

    HAS_LUA = True
except ImportError:
    HAS_LUA = False

from .main_window_ui import GlassButton


class MainWindowToolsMixin:
    def _open_plugin_builder(self):
        self.plugin_builder_window = PluginBuilderWindow(self, translator=translator)
        self._add_open_window("Plugin Builder", self.plugin_builder_window)
        if self.plugin_builder_window.exec():
            self.reload_plugins_and_ui()
        self.plugin_builder_window = None

    def _open_username_osint(self):
        if self._username_osint_window and self._username_osint_window.isVisible():
            self._username_osint_window.raise_()
            self._username_osint_window.activateWindow()
            return
        dlg = UsernameOsintWindow(
            None,
            theme_data=self.theme_data,
            lua_plugins=self.lua_plugins,
        )
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dlg.finished.connect(lambda: setattr(self, "_username_osint_window", None))
        self._username_osint_window = dlg
        self._add_open_window("Username OSINT", dlg)
        dlg.show()

    def _open_graph_editor(self):
        if self._graph_editor_window and self._graph_editor_window.isVisible():
            self._graph_editor_window.raise_()
            self._graph_editor_window.activateWindow()
            return
        editor = GraphEditorWindow(
            None,
            theme_data=self.theme_data,
            lua_plugins=self.lua_plugins,
        )
        editor.run_action_requested.connect(self._on_graph_action)
        editor.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        editor.finished.connect(lambda: setattr(self, "_graph_editor_window", None))
        self._graph_editor_window = editor
        self._add_open_window("Graph Editor", editor)
        editor.show()

    # ------------------------------------------------------------------
    # Pop-out terminal
    # ------------------------------------------------------------------

    def _toggle_terminal_window(self, checked: bool):
        if checked:
            # Keep the floating window owned by MainWindow.  It still behaves
            # as an independent top-level window because TerminalWindow uses
            # Qt.Window, but it can no longer outlive its application window.
            self._terminal_window = TerminalWindow(self.theme_data, parent=self)
            # Seed with current content
            self._terminal_window.set_text(self.output_area.toPlainText())
            self._terminal_window.closed.connect(self._on_terminal_closed)
            self._add_open_window("Terminal", self._terminal_window)
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
            logging.warning("lupa not installed - Lua plugins disabled.")
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
        layout = QGridLayout(menu_widget)
        layout.setContentsMargins(0, 12, 0, 4)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        categories = dict(self.categories)

        # Single "plugins" category for all Lua plugins
        enabled_lua = [p for p in self.lua_plugins if p.enabled]
        if enabled_lua:
            categories["plugins"] = [p.name for p in enabled_lua]

        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)

        for category_index, (cat_key, tool_keys) in enumerate(categories.items()):
            col = QWidget()
            col_layout = QVBoxLayout(col)
            col_layout.setContentsMargins(4, 4, 4, 4)
            col_layout.setSpacing(6)

            title = QLabel(translator.get(cat_key))
            title.setFont(title_font)
            title.setAlignment(Qt.AlignmentFlag.AlignLeft)
            title.setObjectName("SectionLabel")
            title.setProperty("is_title", True)
            col_layout.addWidget(title)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

            buttons_widget = QWidget()
            buttons_widget.setStyleSheet("background: transparent;")
            buttons_layout = QVBoxLayout(buttons_widget)
            buttons_layout.setContentsMargins(2, 2, 6, 2)
            buttons_layout.setSpacing(6)
            scroll.setWidget(buttons_widget)
            col_layout.addWidget(scroll, 1)

            self.tool_widgets[cat_key] = {
                "title": title,
                "buttons": [],
                "widget": col,
                "scroll": scroll,
                "buttons_widget": buttons_widget,
            }

            for key in tool_keys:
                btn = self._make_tool_button(cat_key, key)
                if btn:
                    btn.setMinimumWidth(0)
                    btn.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
                    buttons_layout.addWidget(btn)
                    self.tool_widgets[cat_key]["buttons"].append(btn)

            buttons_layout.addStretch(1)
            layout.addWidget(col, category_index // 3, category_index % 3)

        self.stacked_widget.addWidget(menu_widget)

    def _make_tool_button(self, cat_key, tool_key):
        if cat_key == "plugins":
            lua_p = next((p for p in self.lua_plugins if p.name == tool_key), None)
            if lua_p:
                btn = GlassButton(lua_p.name)
                btn.setProperty("toolCard", True)
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
        btn.setProperty("toolCard", True)
        tooltip_text = translator.get(info.desc) if info.desc else ""
        btn.setToolTip(tooltip_text)
        btn.setEnabled(not info.disabled)
        btn.clicked.connect(lambda _, t=tool_key: self._run_tool_dispatcher(t))
        return btn

    def _filter_tools(self, text):
        search = text.lower()
        for data in self.tool_widgets.values():
            any_visible = False
            for btn in data["buttons"]:
                visible = search in btn.text().lower()
                btn.setVisible(visible)
                if visible:
                    any_visible = True
            data["title"].setVisible(any_visible)
            data["widget"].setVisible(any_visible)

    def _open_command_palette(self):
        commands = [(translator.get(name), f"tool:{name}") for name in self.tool_registry]
        commands.extend(
            [
                (translator.get("Smart Paste"), "action:smart_paste"),
                (translator.get("Add results to graph"), "action:add_graph"),
                (translator.get("Open Graph Editor"), "action:open_graph"),
                (translator.get("Open Settings"), "action:settings"),
            ]
        )
        dialog = CommandPalette(commands, self)
        if not dialog.exec() or not dialog.selected_command:
            return
        command = dialog.selected_command[1]
        if command.startswith("tool:"):
            self._run_tool_dispatcher(command.removeprefix("tool:"))
        elif command == "action:smart_paste":
            self._smart_paste()
        elif command == "action:add_graph":
            self._add_output_to_graph()
        elif command == "action:open_graph":
            self._open_graph_editor()
        elif command == "action:settings":
            self._open_settings()
