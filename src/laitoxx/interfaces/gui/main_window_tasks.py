"""Registry for running jobs and modeless tool windows."""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from laitoxx.interfaces.gui.worker import stop_and_detach_thread


class MainWindowTasksMixin:
    def _refresh_activity_status(self) -> None:
        count = len(self.running_tools)
        if hasattr(self, "activity_status"):
            self.activity_status.setText(f"●  {count} active" if count else "●  System ready")
        if hasattr(self, "activity_hint"):
            self.activity_hint.setVisible(count == 0)

    def _register_activity(self, name, owner, stop_callback, kind: str) -> str:
        key = f"{kind}:{id(owner)}"
        if key in self.running_tools:
            return key
        row = QWidget(self.active_tools_widget)
        row.setObjectName("ActivityItem")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 2, 0, 2)
        label = QLabel(name)
        label.setWordWrap(True)
        stop_btn = QPushButton("Close" if kind == "window" else "Stop")
        stop_btn.clicked.connect(stop_callback)
        row_layout.addWidget(label, 1)
        row_layout.addWidget(stop_btn)
        self.activity_items_layout.insertWidget(self.activity_items_layout.count() - 1, row)
        self.running_tools[key] = {
            "kind": kind,
            "owner": owner,
            "row": row,
            "label": label,
            "stop_button": stop_btn,
        }
        self._refresh_activity_status()
        return key

    def _add_running_tool(self, tool_name, thread, worker):
        key = f"task:{id(thread)}"
        self._register_activity(tool_name, thread, lambda activity_key=key: self._stop_tool(activity_key), "task")
        self.running_tools[key].update(thread=thread, worker=worker)
        thread.finished.connect(lambda activity_key=key: self._remove_running_tool(activity_key))

    def _add_open_window(self, tool_name, window):
        key = f"window:{id(window)}"
        self._register_activity(tool_name, window, window.close, "window")
        if hasattr(window, "finished"):
            window.finished.connect(lambda _result=0, activity_key=key: self._remove_running_tool(activity_key))
        if hasattr(window, "closed"):
            window.closed.connect(lambda activity_key=key: self._remove_running_tool(activity_key))
        window.destroyed.connect(lambda _object=None, activity_key=key: self._remove_running_tool(activity_key))

    def _remove_running_tool(self, activity_key):
        entry = self.running_tools.pop(activity_key, None)
        if entry is None:
            return
        row = entry["row"]
        self.activity_items_layout.removeWidget(row)
        row.deleteLater()
        self._refresh_activity_status()

    def _stop_tool(self, activity_key):
        entry = self.running_tools.get(activity_key)
        if entry is None:
            return
        worker = entry.get("worker")
        if worker:
            try:
                worker.cancel()
            except Exception:
                pass
        thread = entry.get("thread")
        if thread:
            try:
                stop_and_detach_thread(thread, worker)
            except Exception:
                pass
        self._remove_running_tool(activity_key)
