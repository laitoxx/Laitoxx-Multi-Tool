import logging
import os

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTextEdit,
    QVBoxLayout,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.interfaces.gui.plugin_builder import PluginBuilderWindow

from .dialog_helpers import save_file as _save_file


class PluginExecutionWindow(QDialog):
    def __init__(self, plugin_data, parent=None):
        super().__init__(parent)
        self.plugin_data = plugin_data
        self.parent_window = parent
        self.setWindowTitle(translator.get("running_plugin", name=plugin_data.get("name")))
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        self.button_box = QDialogButtonBox()
        self.button_box.addButton(
            translator.get("edit_plugin"), QDialogButtonBox.ButtonRole.ActionRole
        ).clicked.connect(self._edit_plugin)
        self.button_box.addButton(translator.get("save_log"), QDialogButtonBox.ButtonRole.ActionRole).clicked.connect(
            self._save_log
        )
        self.button_box.addButton(translator.get("close"), QDialogButtonBox.ButtonRole.RejectRole).clicked.connect(
            self.accept
        )
        self.button_box.setVisible(False)
        layout.addWidget(self.button_box)

    def append_log(self, text):
        self.log_area.append(text)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def execution_finished(self):
        self.append_log(translator.get("execution_finished"))
        self.button_box.setVisible(True)

    def _edit_plugin(self):
        plugin_path = self.plugin_data.get("plugin_path")
        if plugin_path and os.path.isdir(plugin_path):
            builder = PluginBuilderWindow(self.parent_window, plugin_path=plugin_path, translator=translator)
            if builder.exec():
                self.parent_window.reload_plugins_and_ui()
        else:
            logging.error(translator.get("plugin_path_error", name=self.plugin_data.get("name")))

    def _save_log(self):
        content = self.log_area.toPlainText()
        filepath = _save_file(self, translator.get("save_log"), "Text Files (*.txt);;All Files (*)")
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                logging.error(translator.get("log_save_error", e=e))
