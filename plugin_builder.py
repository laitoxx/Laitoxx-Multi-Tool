import sys
import json
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QListWidget, QListWidgetItem, QLineEdit, QTextEdit,
                             QFormLayout, QDialog, QComboBox, QFileDialog, QMessageBox, QDialogButtonBox)
from PyQt6.QtCore import Qt

class PluginBuilderWindow(QMainWindow):
    def __init__(self, tool_info, parent=None):
        super().__init__(parent)
        self.tool_info = tool_info
        self.setWindowTitle("Plugin Builder")
        self.setGeometry(150, 150, 900, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        self.steps = []

        self.init_ui()

    def init_ui(self):
        # --- Left Panel: Metadata and Workflow Steps ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(300)

        # Metadata
        meta_form = QFormLayout()
        self.plugin_name = QLineEdit()
        self.plugin_desc = QTextEdit()
        self.plugin_desc.setMaximumHeight(60)
        self.plugin_author = QLineEdit()
        self.plugin_version = QLineEdit("1.0")
        meta_form.addRow("Plugin Name:", self.plugin_name)
        meta_form.addRow("Description:", self.plugin_desc)
        meta_form.addRow("Author:", self.plugin_author)
        meta_form.addRow("Version:", self.plugin_version)
        left_layout.addLayout(meta_form)

        # Workflow Steps List
        self.steps_list_widget = QListWidget()
        self.steps_list_widget.currentItemChanged.connect(self.on_step_selected)
        left_layout.addWidget(self.steps_list_widget)

        # Workflow Action Buttons
        steps_button_layout = QHBoxLayout()
        btn_add_step = QPushButton("Add Step")
        btn_add_step.clicked.connect(self.add_step)
        btn_remove_step = QPushButton("Remove Step")
        btn_remove_step.clicked.connect(self.remove_step)
        steps_button_layout.addWidget(btn_add_step)
        steps_button_layout.addWidget(btn_remove_step)
        left_layout.addLayout(steps_button_layout)

        # --- Right Panel: Step Configuration ---
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_panel.setVisible(False) # Initially hidden

        self.step_config_form = QFormLayout()
        self.step_id_label = QLineEdit()
        self.step_tool_label = QLineEdit()
        self.step_tool_label.setReadOnly(True)
        self.step_prompt_input = QLineEdit()
        self.step_input_source_combo = QComboBox()

        self.step_config_form.addRow("Step ID:", self.step_id_label)
        self.step_config_form.addRow("Tool:", self.step_tool_label)
        self.step_config_form.addRow("User Prompt:", self.step_prompt_input)
        self.step_config_form.addRow("Input Source:", self.step_input_source_combo)
        self.right_layout.addLayout(self.step_config_form)
        self.right_layout.addStretch()

        # --- Main Layout Setup ---
        self.main_layout.addWidget(left_panel)
        self.main_layout.addWidget(self.right_panel)

        # --- Bottom Save Button ---
        bottom_layout = QVBoxLayout()
        btn_save = QPushButton("Save Plugin")
        btn_save.clicked.connect(self.save_plugin)
        bottom_layout.addWidget(btn_save)
        left_layout.addLayout(bottom_layout)

    def add_step(self):
        dialog = AddStepDialog(self.tool_info, self)
        if dialog.exec():
            selected_tool = dialog.get_selected_tool()
            if selected_tool:
                step_id = f"step{len(self.steps) + 1}"
                new_step = {
                    "id": step_id,
                    "tool": selected_tool,
                    "prompt": self.tool_info[selected_tool].get("prompt", ""),
                    "input_source": "user"
                }
                self.steps.append(new_step)
                self.refresh_steps_list()
                self.steps_list_widget.setCurrentRow(len(self.steps) - 1)

    def remove_step(self):
        current_row = self.steps_list_widget.currentRow()
        if current_row > -1:
            del self.steps[current_row]
            self.refresh_steps_list()
            self.right_panel.setVisible(False)

    def refresh_steps_list(self):
        self.steps_list_widget.clear()
        for i, step in enumerate(self.steps):
            step['id'] = f"step{i+1}" # Re-index IDs
            item = QListWidgetItem(f"{step['id']}: {step['tool']}")
            self.steps_list_widget.addItem(item)

    def on_step_selected(self, current_item, previous_item):
        if not current_item:
            self.right_panel.setVisible(False)
            return

        current_row = self.steps_list_widget.row(current_item)
        selected_step = self.steps[current_row]

        # Update form fields
        self.step_id_label.setText(selected_step['id'])
        self.step_tool_label.setText(selected_step['tool'])
        self.step_prompt_input.setText(selected_step.get('prompt', ''))

        # Update input source dropdown
        self.step_input_source_combo.clear()
        self.step_input_source_combo.addItem("user")
        for i in range(current_row):
            self.step_input_source_combo.addItem(self.steps[i]['id'])
        
        current_source = selected_step.get('input_source', 'user')
        self.step_input_source_combo.setCurrentText(current_source)

        # Disconnect signals to prevent loops before connecting them
        try:
            self.step_id_label.textChanged.disconnect()
            self.step_prompt_input.textChanged.disconnect()
            self.step_input_source_combo.currentTextChanged.disconnect()
        except TypeError:
            pass # Signals were not connected yet

        self.step_id_label.textChanged.connect(self.update_current_step)
        self.step_prompt_input.textChanged.connect(self.update_current_step)
        self.step_input_source_combo.currentTextChanged.connect(self.update_current_step)

        self.right_panel.setVisible(True)

    def update_current_step(self):
        current_row = self.steps_list_widget.currentRow()
        if current_row < 0:
            return

        # Update the step data from the form
        self.steps[current_row]['id'] = self.step_id_label.text()
        self.steps[current_row]['prompt'] = self.step_prompt_input.text()
        self.steps[current_row]['input_source'] = self.step_input_source_combo.currentText()
        
        # Refresh the list to show new ID
        self.steps_list_widget.blockSignals(True)
        self.refresh_steps_list()
        self.steps_list_widget.setCurrentRow(current_row)
        self.steps_list_widget.blockSignals(False)

    def save_plugin(self):
        plugin_name = self.plugin_name.text()
        if not plugin_name or not self.steps:
            QMessageBox.warning(self, "Validation Error", "Plugin Name and at least one step are required.")
            return

        plugin_data = {
            "name": plugin_name,
            "description": self.plugin_desc.toPlainText(),
            "author": self.plugin_author.text(),
            "version": self.plugin_version.text(),
            "workflow": self.steps
        }

        # Sanitize filename
        filename = "".join(c for c in plugin_name if c.isalnum() or c in (' ', '_')).rstrip()
        filename = f"{filename.replace(' ', '_')}.json"
        
        plugin_dir = "plugins"
        if not os.path.exists(plugin_dir):
            os.makedirs(plugin_dir)

        filepath, _ = QFileDialog.getSaveFileName(self, "Save Plugin", os.path.join(plugin_dir, filename), "JSON Files (*.json)")

        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(plugin_data, f, indent=2)
                QMessageBox.information(self, "Success", f"Plugin saved successfully to:\n{filepath}")
                self.close()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save plugin: {e}")


class AddStepDialog(QDialog):
    def __init__(self, tool_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Step")
        self.layout = QVBoxLayout(self)
        
        self.tool_list = QListWidget()
        for tool_name in tool_info.keys():
            self.tool_list.addItem(tool_name)
        
        self.layout.addWidget(self.tool_list)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_selected_tool(self):
        selected_item = self.tool_list.currentItem()
        return selected_item.text() if selected_item else None

if __name__ == '__main__':
    # This is for testing the builder independently
    # You would normally import and launch this from your main gui.py
    mock_tool_info = {
        "Check IP": {"func": None, "prompt": "Enter IP:"},
        "Check Domain": {"func": None, "prompt": "Enter Domain:"},
        "Scan Ports": {"func": None, "prompt": "Enter Target:"}
    }
    app = QApplication(sys.argv)
    window = PluginBuilderWindow(mock_tool_info)
    window.show()
    sys.exit(app.exec())