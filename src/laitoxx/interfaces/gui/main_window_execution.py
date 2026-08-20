"""Main window responsibility mixin."""

from PyQt6.QtWidgets import (
    QApplication,
    QMessageBox,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.features.utilities.ioc_extractor import extract_entities
from laitoxx.interfaces.gui.command_palette import SmartPasteDialog
from laitoxx.interfaces.gui.dialogs import (
    LuaPluginInputDialog,
)
from laitoxx.interfaces.gui.tool_input_controller import ToolInputController
from laitoxx.interfaces.gui.worker import (
    Worker,
)
from laitoxx.shared.graph.model import Node


class MainWindowExecutionMixin:
    def _smart_paste(self):
        text = QApplication.clipboard().text().strip()
        if not text:
            QMessageBox.information(self, translator.get("Smart Paste"), translator.get("Clipboard is empty."))
            return
        entities = extract_entities(text)
        if not entities:
            QMessageBox.information(
                self, translator.get("Smart Paste"), translator.get("No recognizable entities found.")
            )
            return
        dialog = SmartPasteDialog(entities, self)
        if not dialog.exec():
            return
        if dialog.action == "graph":
            self._add_entities_to_graph(entities)
        elif dialog.action == "extract":
            self._run_tool_with_input("IOC Extractor", text)
        elif dialog.action == "run" and dialog.suggested_tool:
            self._run_tool_with_input(dialog.suggested_tool, dialog.selected_entity.value)

    def _run_tool_with_input(self, tool_name: str, input_data):
        info = self.tool_registry.get(tool_name)
        if not info:
            return
        self.output_area.clear()
        if info.threaded:
            self._run_threaded(tool_name, info.func, input_data)
        elif isinstance(input_data, dict):
            self._execute_dict_tool(info.func, input_data)
        else:
            # Registry tools conventionally read simple input through input().
            self._execute_tool(info.func, input_data)

    def _add_output_to_graph(self):
        entities = extract_entities(self.output_area.toPlainText())
        if not entities:
            QMessageBox.information(
                self, translator.get("Graph Editor"), translator.get("No recognizable entities found.")
            )
            return
        self._add_entities_to_graph(entities)

    def _add_entities_to_graph(self, entities):
        self._open_graph_editor()
        editor = self._graph_editor_window
        if not editor:
            return
        existing = {(node.node_type, node.label.casefold()) for node in editor._graph.nodes}
        added = 0
        for entity in entities:
            key = (entity.graph_type, entity.value.casefold())
            if key in existing:
                continue
            node = Node.from_type(entity.value, entity.graph_type)
            node.description = f"Imported from {entity.kind.upper()} extraction"
            editor._graph.add_node(node)
            existing.add(key)
            added += 1
        editor._refresh_all()
        editor.raise_()
        self._append_output(f"\n[GRAPH] Added {added} entities.\n")

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
        if input_data is ToolInputController.OPENED_WINDOW:
            return

        if info.threaded:
            self._run_threaded(tool_name, info.func, input_data)
        elif isinstance(input_data, dict):
            self._execute_dict_tool(info.func, input_data)
        else:
            self._execute_tool(info.func, input_data)

    def _collect_input(self, tool_name, info):
        return self.input_controller.collect(tool_name, info)

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
        self.execution_controller.start_worker(
            tool_name, worker, start_message=start_message, connect_graph=connect_graph
        )

    def _run_threaded(self, tool_name, func, input_data):
        self.execution_controller.run_threaded(tool_name, func, input_data)

    def _execute_tool(self, func, input_data):
        self.execution_controller.execute(func, input_data)

    def _execute_dict_tool(self, func, data):
        self.execution_controller.execute_dict(func, data)

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
            None,
            query,
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
