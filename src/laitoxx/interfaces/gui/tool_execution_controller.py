"""Execution lifecycle for built-in and plugin tools."""

from __future__ import annotations

import contextlib

from PyQt6.QtCore import QThread

from laitoxx.interfaces.gui.worker import SignalWriter, Worker, _InputOverride, remove_ansi_codes


class ToolExecutionController:
    def __init__(self, host):
        self.host = host
        self.threads: set[QThread] = set()

    def start_worker(
        self,
        tool_name: str,
        worker: Worker,
        *,
        start_message: str | None = None,
        connect_graph: bool = False,
    ) -> None:
        thread = QThread(self.host)
        self.threads.add(thread)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self.threads.discard(thread))
        worker.update.connect(self.host._append_output)
        worker.error.connect(self.host._handle_worker_error)
        if connect_graph:
            worker.graph_ready.connect(self.host._on_graph_ready)
        thread.start()
        self.host._add_running_tool(tool_name, thread, worker)
        if start_message:
            self.host._set_output(start_message)
        self.host._current_thread = thread
        self.host._current_worker = worker

    def run_threaded(self, tool_name, func, input_data) -> None:
        self.start_worker(
            tool_name,
            Worker(func, input_data),
            start_message=f"Running {tool_name} in the background...",
        )

    def execute(self, func, input_data) -> None:
        try:
            writer = SignalWriter(self.host._append_output, transform=remove_ansi_codes)
            with _InputOverride(input_data or ""), contextlib.redirect_stdout(writer):
                func()
            writer.flush()
        except Exception as exc:
            self.host._set_output(f"An error occurred: {exc}")

    def execute_dict(self, func, data) -> None:
        try:
            writer = SignalWriter(self.host._append_output, transform=remove_ansi_codes)
            with contextlib.redirect_stdout(writer):
                func(data)
            writer.flush()
        except Exception as exc:
            self.host._set_output(f"An error occurred: {exc}")
