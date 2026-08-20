"""Main window responsibility mixin."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMenu,
    QMessageBox,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.interfaces.gui.dialogs import (
    LuaPluginConfigDialog,
)
from laitoxx.interfaces.gui.graph_editor import GraphEditorWindow
from laitoxx.interfaces.gui.plugin_builder import PluginBuilderWindow
from laitoxx.interfaces.gui.worker import (
    Worker,
)

try:
    from laitoxx.app.plugins.engine import (
        load_lua_plugin_settings,
        save_lua_plugin_settings,
    )

    HAS_LUA = True
except ImportError:
    HAS_LUA = False


class MainWindowGraphMixin:
    def _on_graph_ready(self, graph_path: str):
        """Called when a Lua plugin saves a graph file. Ask user to open it."""
        self._append_output(f"\n[Graph] Граф сохранён: {graph_path}")
        reply = QMessageBox.question(
            self,
            translator.get("graph_editor_title"),
            translator.get("graph_open_prompt", path=graph_path),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from laitoxx.shared.graph.model import Graph

                graph = Graph.load_json(graph_path)
                if self._graph_editor_window and self._graph_editor_window.isVisible():
                    self._graph_editor_window.close()
                editor = GraphEditorWindow(None, theme_data=self.theme_data, lua_plugins=self.lua_plugins)
                editor.run_action_requested.connect(self._on_graph_action)
                editor._current_filepath = graph_path
                editor.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
                editor.finished.connect(lambda: setattr(self, "_graph_editor_window", None))
                self._graph_editor_window = editor
                editor.set_graph(graph)
                editor.show()
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
                None,
                value,
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
            translator.get("lua_plugin_disable") if plugin_meta.enabled else translator.get("lua_plugin_enable")
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
        builder = PluginBuilderWindow(self, plugin_path=plugin_meta.filepath, translator=translator)
        if builder.exec():
            self.reload_plugins_and_ui()

    def _open_lua_plugin_settings(self, plugin_meta):
        dlg = LuaPluginConfigDialog(self, plugin_meta)
        if dlg.exec():
            plugin_meta.config_values = dlg.get_config()
            self._save_lua_plugin_state()
            self._set_output(translator.get("lua_plugin_settings_saved", name=plugin_meta.name))

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
