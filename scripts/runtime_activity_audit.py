"""Runtime lifecycle audit for the main-window activity registry."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QSizePolicy, QSpacerItem, QVBoxLayout, QWidget

from laitoxx.interfaces.gui.main_window_tasks import MainWindowTasksMixin


class ActivityHost(MainWindowTasksMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.running_tools = {}
        self._zombie_threads = set()
        self.active_tools_widget = QWidget(self)
        self.activity_items_layout = QVBoxLayout(self.active_tools_widget)
        self.activity_status = QLabel("●  System ready")
        self.activity_hint = QLabel("Empty")
        self.activity_items_layout.addWidget(self.activity_status)
        self.activity_items_layout.addWidget(self.activity_hint)
        self.activity_items_layout.addSpacerItem(
            QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )


class Worker:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


def main() -> int:
    app = QApplication.instance() or QApplication([])
    host = ActivityHost()
    first = QThread(host)
    second = QThread(host)
    worker = Worker()
    host._add_running_tool("Same tool", first, worker)
    host._add_running_tool("Same tool", second, Worker())
    assert len(host.running_tools) == 2
    assert host.activity_status.text() == "●  2 active"

    dialog = QDialog(host)
    host._add_open_window("Modeless tool", dialog)
    dialog.show()
    app.processEvents()
    assert len(host.running_tools) == 3
    dialog.accept()
    app.processEvents()
    assert len(host.running_tools) == 2

    first.start()
    host._stop_tool(f"task:{id(first)}")
    assert worker.cancelled and first.wait(2000)
    host._remove_running_tool(f"task:{id(second)}")
    assert not host.running_tools
    assert host.activity_status.text() == "●  System ready"
    print("PASS active_task_and_window_lifecycle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
