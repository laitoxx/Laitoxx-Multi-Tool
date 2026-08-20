import contextlib
import logging
import threading

from PyQt6.QtCore import QObject, pyqtSignal

from .worker_io import (
    SignalWriter,
    _InputOverride,
    remove_ansi_codes,
)
from .worker_io import (
    stop_and_detach_thread as stop_and_detach_thread,
)

# Global registry to keep references to stopped threads until they finish
# naturally, preventing "QThread: Destroyed while thread is still running" crashes.
# ---------------------------------------------------------------------------
# Thread-local input override
# ---------------------------------------------------------------------------
# Each worker thread stores its input value here so that builtins.input can
# be patched once globally and route to the correct per-thread value instead
# of overwriting a shared global (which caused race conditions when two tools
# ran concurrently).
from .worker_plugin import PluginExecutionMixin


class Worker(PluginExecutionMixin, QObject):
    finished = pyqtSignal()
    update = pyqtSignal(str)
    error = pyqtSignal(str)
    graph_ready = pyqtSignal(str)  # emits graph file path

    def __init__(
        self,
        func,
        input_data=None,
        is_plugin=False,
        tool_info=None,
        is_lua_plugin=False,
        lua_plugin_meta=None,
        lua_function_name=None,
    ):
        super().__init__()
        self.func = func
        self.input_data = input_data
        self.is_plugin = is_plugin
        self.tool_info = tool_info
        self.is_lua_plugin = is_lua_plugin
        self.lua_plugin_meta = lua_plugin_meta
        self.lua_function_name = lua_function_name
        self._cancel_event = threading.Event()

    def cancel(self):
        self._cancel_event.set()

    def run(self):
        if self._cancel_event.is_set():
            self.finished.emit()
            return
        if self.is_lua_plugin:
            self._run_lua_plugin()
        elif self.is_plugin:
            self._run_plugin()
        else:
            self._run_tool()

    # ------------------------------------------------------------------
    # Lua plugin runner
    # ------------------------------------------------------------------

    def _run_lua_plugin(self):
        try:
            from laitoxx.app.plugins.engine import run_lua_plugin

            func_name = self.lua_function_name or "search"
            result = run_lua_plugin(
                self.lua_plugin_meta,
                func_name,
                query=self.input_data or "",
                output_callback=lambda msg: self._emit_update(msg),
                graph_callback=lambda path: self.graph_ready.emit(path),
            )
            if result:
                self._emit_update(result)
        except Exception as e:
            logging.error(f"Lua plugin error: {e}", exc_info=True)
            self.error.emit(f"Lua plugin error: {e}")
        finally:
            self.finished.emit()

    # ------------------------------------------------------------------
    # Tool runner
    # ------------------------------------------------------------------

    def _run_tool(self):
        try:
            if isinstance(self.input_data, dict):
                self._run_with_writer(lambda: self.func(self.input_data))
            else:
                self._run_with_input(self.func, self.input_data)
        except Exception as e:
            logging.error(f"Error in worker thread for {self.func.__name__}: {e}", exc_info=True)
            self.error.emit(f"An error occurred: {e}")
        finally:
            self.finished.emit()

    def _run_with_writer(self, func):
        writer = SignalWriter(
            self.update.emit,
            transform=remove_ansi_codes,
            cancel_event=self._cancel_event,
        )
        with contextlib.redirect_stdout(writer):
            func()
        writer.flush()

    def _run_with_input(self, func, input_data):
        with _InputOverride(input_data or ""):
            self._run_with_writer(func)

    # ------------------------------------------------------------------
    # Plugin runner
    # ------------------------------------------------------------------
