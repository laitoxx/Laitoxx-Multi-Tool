"""
 @@@  @@@  @@@@@@  @@@@@@@ @@@@@@@  @@@@@@@  @@@ @@@@@@@@ @@@ @@@
 @@!  @@@ @@!  @@@   @@!   @@!  @@@ @@!  @@@ @@! @@!      @@! !@@
 @!@!@!@! @!@  !@!   @!!   @!@  !@! @!@!!@!  !!@ @!!!:!    !@!@! 
 !!:  !!! !!:  !!!   !!:   !!:  !!! !!: :!!  !!: !!:        !!:  
  :   : :  : :. :     :    :: :  :   :   : : :    :         .:   
                                                                 
    HOTDRIFY cooked with the refactor for the LAITOXX squad.
                    github.com/hotdrify
                      t.me/hotdrify

                    github.com/laitoxx
                      t.me/laitoxx
"""

from ..utils.translations import Translator

from PyQt6.QtWidgets import (QVBoxLayout, QTextEdit, QFileDialog,
                             QDialog, QDialogButtonBox)

from typing import Any
import logging
import os

translator = Translator()

class PluginExecutionWindow(QDialog):
    def __init__(self, plugin_data: dict, 
                 parent: Any = None):
        super().__init__(parent)
        self.plugin_data: dict = plugin_data
        self.parent_window = parent
        self.setWindowTitle(translator.get(
            "running_plugin", name=plugin_data.get('name')))
        self.setMinimumSize(700, 500)

        self.layout = QVBoxLayout(self)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.layout.addWidget(self.log_area)

        self.button_box: Any = QDialogButtonBox()
        self.edit_button = self.button_box.addButton(translator.get(
            "edit_plugin"), QDialogButtonBox.ButtonRole.ActionRole)
        self.save_log_button = self.button_box.addButton(
            translator.get("save_log"), QDialogButtonBox.ButtonRole.ActionRole)
        self.close_button = self.button_box.addButton(
            translator.get("close"), QDialogButtonBox.ButtonRole.RejectRole)

        self.edit_button.clicked.connect(self.edit_plugin)
        self.save_log_button.clicked.connect(self.save_log)
        self.close_button.clicked.connect(self.accept)

        self.button_box.setVisible(False)
        self.layout.addWidget(self.button_box)

    def append_log(self, text):
        self.log_area.append(text)
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum())

    def execution_finished(self):
        self.append_log(translator.get("execution_finished"))
        self.button_box.setVisible(True)

    def edit_plugin(self):
        plugin_path: str = self.plugin_data.get('plugin_path')
        if plugin_path and os.path.isdir(plugin_path):
            builder = PluginBuilderWindow(
                self.parent_window, plugin_path=plugin_path, translator=translator)
            if builder.exec():
                self.parent_window.reload_plugins_and_ui()
        else:
            logging.error(translator.get("plugin_path_error",
                          name=self.plugin_data.get('name')))

    def save_log(self):
        log_content = self.log_area.toPlainText()
        filepath, _ = QFileDialog.getSaveFileName(self, translator.get(
            "save_log"), "", "Text Files (*.txt);;All Files (*)")
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(log_content)
            except Exception as e:
                logging.error(translator.get("log_save_error", e=e))