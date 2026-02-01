import sys
import os
import json
import re
from datetime import datetime
import shutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QDialog, QFormLayout, QLineEdit,
                             QDialogButtonBox, QCheckBox, QTextEdit, QFileDialog,
                             QLabel, QHBoxLayout, QScrollArea, QStackedWidget,
                             QInputDialog, QComboBox)
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPen, QColor, QPainterPath
from PyQt6.QtCore import Qt, QPoint

# --- Draggable Step Widget ---


class DraggableStepWidget(QWidget):
    def __init__(self, parent, step_data, plugin_path, translator):
        super().__init__(parent)
        self.parent_canvas = parent
        self.step_data = step_data
        self.plugin_path = plugin_path
        self.translator = translator
        self.setFixedSize(80, 100)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self.order_label = QLabel("0")
        self.order_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.order_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))

        self.icon_label = QLabel("?")
        self.icon_label.setFixedSize(60, 60)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.desc_label = QLabel()
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.order_label)
        layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.desc_label)
        self.setLayout(layout)

        self.update_visuals()

    def update_visuals(self):
        is_delay = self.step_data.get('type') == 'delay'

        if is_delay:
            self.icon_label.setText("⏱️")
            self.icon_label.setStyleSheet(
                "background-color: #6c5ce7; border-radius: 30px; font-size: 24px;")
            self.desc_label.setText(self.translator.get(
                "delay_duration_seconds", duration=self.step_data.get('duration', 1)))
        else:
            icon_rel_path = self.step_data.get("icon")
            full_icon_path = os.path.join(
                self.plugin_path, icon_rel_path) if self.plugin_path and icon_rel_path else None

            if full_icon_path and os.path.exists(full_icon_path):
                pixmap = QPixmap(full_icon_path)
                path = QPainterPath()
                path.addEllipse(0, 0, 60, 60)
                pixmap = pixmap.scaled(
                    60, 60, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                rounded_pixmap = QPixmap(60, 60)
                rounded_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, pixmap)
                painter.end()
                self.icon_label.setPixmap(rounded_pixmap)
            else:
                self.icon_label.setText("?")
                self.icon_label.setStyleSheet(
                    "background-color: #555555; border-radius: 30px; font-size: 24px;")

            desc = self.step_data.get(
                "description", self.translator.get("step_description_default"))
            self.desc_label.setText(
                desc[:15] + "..." if len(desc) > 15 else desc)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.RightButton:
            self.parent_canvas.open_settings(self)

    def mouseMoveEvent(self, event):
        if hasattr(self, 'drag_start_position') and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(self.mapToParent(event.pos() - self.drag_start_position))
            self.parent_canvas.update()

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if hasattr(self, 'drag_start_position'):
            del self.drag_start_position
            self.parent_canvas.sort_steps()
            self.parent_canvas.update()

# --- Steps Canvas ---


class StepsCanvas(QWidget):
    def __init__(self, parent_builder, translator):
        super().__init__()
        self.builder = parent_builder
        self.translator = translator
        self.steps = []
        self.setMinimumSize(1000, 500)

    def add_step(self, step_data):
        if 'id' not in step_data:
            step_data['id'] = f"step_{datetime.now().timestamp()}"
        widget = DraggableStepWidget(
            self, step_data, self.builder.plugin_path, self.translator)
        widget.move(50 + (len(self.steps) * 120), self.height() // 2 - 50)
        widget.show()
        self.steps.append(widget)
        self.sort_steps()
        self.update()

    def delete_last_step(self):
        if self.steps:
            self.steps.pop().deleteLater()
            self.sort_steps()
            self.update()

    def open_settings(self, step_widget):
        if step_widget.step_data.get('type') == 'delay':
            duration, ok = QInputDialog.getInt(self, self.translator.get("set_delay_title"), self.translator.get(
                "delay_seconds"), step_widget.step_data.get('duration', 1), 1, 3600, 1)
            if ok:
                step_widget.step_data['duration'] = duration
        else:
            dialog = StepSettingsDialog(
                self.builder, step_widget.step_data, self.translator)
            dialog.exec()
        step_widget.update_visuals()

    def sort_steps(self):
        self.steps.sort(key=lambda w: w.x())
        for i, widget in enumerate(self.steps):
            widget.order_label.setText(str(i + 1))
            widget.step_data['order'] = i

    def get_sorted_steps_data(self):
        self.sort_steps()
        return [w.step_data for w in self.steps]

    def load_from_data(self, steps_data):
        for step in self.steps:
            step.deleteLater()
        self.steps = []
        if steps_data:
            steps_data.sort(key=lambda s: s.get('order', 0))
            for data in steps_data:
                self.add_step(data)
        self.sort_steps()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if len(self.steps) < 2:
            return
        painter = QPainter(self)
        painter.setPen(QPen(QColor("#a29bfe"), 2, Qt.PenStyle.SolidLine))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i in range(len(self.steps) - 1):
            p1 = self.steps[i].pos() + QPoint(self.steps[i].width(),
                                              self.steps[i].height() // 2 + 10)
            p2 = self.steps[i+1].pos() + \
                QPoint(0, self.steps[i+1].height() // 2 + 10)
            painter.drawLine(p1, p2)

# --- Main Builder Window ---


class PluginBuilderWindow(QDialog):
    def __init__(self, parent=None, plugin_path=None, translator=None):
        super().__init__(parent)
        self.translator = translator
        self.plugin_data = {}
        self.plugin_path = plugin_path
        self.stacked_widget = QStackedWidget(self)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.stacked_widget)
        self.canvas = StepsCanvas(self, self.translator)
        self._create_meta_page()
        self._create_editor_page()
        self.retranslate_ui()
        if self.plugin_path:
            self._load_existing_plugin()
        else:
            self.stacked_widget.setCurrentIndex(0)

    def retranslate_ui(self):
        self.setWindowTitle(self.translator.get("plugin_builder_title"))
        self.form_layout.labelForField(self.name_entry).setText(
            self.translator.get("plugin_name_label"))
        self.form_layout.labelForField(self.author_entry).setText(
            self.translator.get("author_name_label"))
        self.form_layout.labelForField(self.website_entry).setText(
            self.translator.get("website_label"))
        self.form_layout.labelForField(self.description_textbox).setText(
            self.translator.get("description_label"))
        self.os_label.setText(self.translator.get("supported_os"))
        self.continue_button.setText(self.translator.get("continue"))
        self.cancel_button.setText(self.translator.get("cancel"))
        self.btn_add_step.setText(self.translator.get("add_step"))
        self.btn_add_delay.setText(self.translator.get("add_delay"))
        self.btn_delete_step.setText(self.translator.get("delete_last_step"))
        self.btn_save_plugin.setText(self.translator.get("save_plugin"))
        if self.plugin_data.get("name"):
            self.setWindowTitle(self.translator.get(
                "editing_plugin", name=self.plugin_data["name"]))

    def _load_existing_plugin(self):
        plugin_json_path = os.path.join(self.plugin_path, 'plugin.json')
        if os.path.exists(plugin_json_path):
            try:
                with open(plugin_json_path, 'r', encoding='utf-8') as f:
                    self.plugin_data = json.load(f)
                self.name_entry.setText(self.plugin_data.get("name", ""))
                self.author_entry.setText(self.plugin_data.get("author", ""))
                self.website_entry.setText(self.plugin_data.get("website", ""))
                self.description_textbox.setPlainText(
                    self.plugin_data.get("description", ""))
                for name, cb in self.os_checkboxes.items():
                    cb.setChecked(
                        name in self.plugin_data.get("supported_os", []))
                self.setWindowTitle(self.translator.get(
                    "editing_plugin", name=self.plugin_data['name']))
                self.canvas.load_from_data(self.plugin_data.get('steps', []))
                self.stacked_widget.setCurrentIndex(1)
            except (FileNotFoundError, json.JSONDecodeError):
                self.plugin_path = None
                self.stacked_widget.setCurrentIndex(0)
        else:
            self.plugin_path = None
            self.stacked_widget.setCurrentIndex(0)

    def _create_meta_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.form_layout = QFormLayout()
        self.name_entry = QLineEdit()
        self.author_entry = QLineEdit()
        self.website_entry = QLineEdit()
        self.description_textbox = QTextEdit()
        self.description_textbox.setFixedHeight(100)
        self.form_layout.addRow(self.translator.get(
            "plugin_name_label"), self.name_entry)
        self.form_layout.addRow(self.translator.get(
            "author_name_label"), self.author_entry)
        self.form_layout.addRow(self.translator.get(
            "website_label"), self.website_entry)
        self.form_layout.addRow(self.translator.get(
            "description_label"), self.description_textbox)
        os_group = QWidget()
        os_layout = QHBoxLayout(os_group)
        self.os_checkboxes = {}
        for os_name in ["Windows", "Debian", "Ubuntu", "Kali", "Arch"]:
            cb = QCheckBox(os_name)
            self.os_checkboxes[os_name.lower()] = cb
            os_layout.addWidget(cb)
        self.os_label = QLabel()
        self.form_layout.addRow(self.os_label, os_group)
        layout.addLayout(self.form_layout)
        button_box = QDialogButtonBox()
        self.continue_button = button_box.addButton(
            QDialogButtonBox.StandardButton.Ok)
        self.cancel_button = button_box.addButton(
            QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._process_meta_and_switch_to_editor)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        self.stacked_widget.addWidget(page)

    def _process_meta_and_switch_to_editor(self):
        plugin_name = self.name_entry.text()
        if not plugin_name:
            return
        supported_os = [name for name,
                        cb in self.os_checkboxes.items() if cb.isChecked()]
        if not supported_os:
            return
        if not self.plugin_path:
            plugin_folder_name = re.sub(r'[<>:"/\\|?*]', '_', plugin_name)
            self.plugin_path = os.path.join("plugins", plugin_folder_name)
            os.makedirs(self.plugin_path, exist_ok=True)
            self.plugin_data['steps'] = []
        self.plugin_data.update({"author": self.author_entry.text(), "name": plugin_name, "website": self.website_entry.text(
        ), "description": self.description_textbox.toPlainText(), "supported_os": supported_os})
        self.setWindowTitle(self.translator.get(
            "editing_plugin", name=self.plugin_data['name']))
        self.canvas.load_from_data(self.plugin_data.get('steps', []))
        self.stacked_widget.setCurrentIndex(1)

    def _create_editor_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        toolbar = QHBoxLayout()
        self.btn_add_step = QPushButton()
        self.btn_add_delay = QPushButton()
        self.btn_delete_step = QPushButton()
        self.btn_save_plugin = QPushButton()
        self.btn_add_step.clicked.connect(lambda: self.canvas.add_step(
            {"description": self.translator.get("new_step_default_description")}))
        self.btn_add_delay.clicked.connect(
            lambda: self.canvas.add_step({"type": "delay", "duration": 1}))
        self.btn_delete_step.clicked.connect(self.canvas.delete_last_step)
        self.btn_save_plugin.clicked.connect(self._save_plugin)
        toolbar.addWidget(self.btn_add_step)
        toolbar.addWidget(self.btn_add_delay)
        toolbar.addWidget(self.btn_delete_step)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_save_plugin)
        layout.addLayout(toolbar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.canvas)
        scroll.setStyleSheet("background-color: #2d3436;")
        layout.addWidget(scroll)
        self.stacked_widget.addWidget(page)

    def _save_plugin(self):
        self.plugin_data['steps'] = self.canvas.get_sorted_steps_data()
        try:
            with open(os.path.join(self.plugin_path, "plugin.json"), 'w', encoding='utf-8') as f:
                json.dump(self.plugin_data, f, indent=4, ensure_ascii=False)
            self.accept()
        except Exception as e:
            print(f"Failed to save plugin: {e}")

# --- Step Settings Dialog ---


class StepSettingsDialog(QDialog):
    def __init__(self, parent, step_data, translator):
        super().__init__(parent)
        self.step_data = step_data
        self.builder_window = parent
        self.plugin_path = self.builder_window.plugin_path
        self.translator = translator
        self.setWindowTitle(self.translator.get("step_settings_title"))
        self.setMinimumWidth(500)

        layout = QFormLayout(self)
        self.form_layout = layout

        # --- Basic Info ---
        self.desc_entry = QLineEdit(step_data.get("description", ""))
        icon_btn = QPushButton(self.translator.get("select_icon"))
        icon_btn.clicked.connect(self._select_icon)

        layout.addRow(self.translator.get("step_description"), self.desc_entry)
        layout.addRow(icon_btn)

        # --- Input Source ---
        self.input_source_combo = QComboBox()
        self.input_source_combo.addItem(
            self.translator.get("input_source_user"), "user")
        self.input_source_combo.addItem(
            self.translator.get("input_source_none"), "none")

        current_step_order = step_data.get('order', -1)
        self.previous_steps = [s.step_data for s in self.builder_window.canvas.steps if s.step_data.get(
            'order', -1) < current_step_order]
        for prev_step in self.previous_steps:
            desc = prev_step.get('description', self.translator.get(
                "step_default_name", order=prev_step.get('order', 0)+1))
            step_id = prev_step.get('id', f"step_{prev_step.get('order', 0)}")
            self.input_source_combo.addItem(self.translator.get(
                "input_source_previous", description=desc), f"previous_step:{step_id}")

        self.input_source_combo.currentIndexChanged.connect(
            self._update_ui_visibility)
        layout.addRow(self.translator.get(
            "input_source"), self.input_source_combo)

        # --- REGEX Filtering ---
        self.regex_widget = QWidget()
        regex_main_layout = QVBoxLayout(self.regex_widget)
        regex_main_layout.setContentsMargins(0, 0, 0, 0)

        self.regex_fields_layout = QVBoxLayout()
        regex_main_layout.addLayout(self.regex_fields_layout)

        regex_buttons_layout = QHBoxLayout()
        self.add_regex_btn = QPushButton(self.translator.get("add_regex"))
        self.add_regex_btn.clicked.connect(lambda: self._add_regex_field())
        self.remove_regex_btn = QPushButton(
            self.translator.get("remove_regex"))
        self.remove_regex_btn.clicked.connect(self._remove_regex_field)
        regex_buttons_layout.addWidget(self.add_regex_btn)
        regex_buttons_layout.addWidget(self.remove_regex_btn)
        regex_main_layout.addLayout(regex_buttons_layout)

        self.regex_label = QLabel(self.translator.get("input_filter_regex"))
        layout.addRow(self.regex_label, self.regex_widget)

        # --- Action Type ---
        self.action_type_combo = QComboBox()
        self.action_type_combo.addItem(
            self.translator.get("action_type_command"), "command")
        self.action_type_combo.addItem(self.translator.get(
            "action_type_batch_script"), "batch_script")
        self.action_type_combo.addItem(self.translator.get(
            "action_type_shell_script"), "shell_script")
        self.action_type_combo.addItem(
            self.translator.get("action_type_function"), "function")
        self.action_type_combo.currentIndexChanged.connect(
            self._update_ui_visibility)

        self.action_stack = QStackedWidget()
        self.command_entry = QLineEdit(step_data.get("command", ""))
        self.function_combo = QComboBox()

        main_window = self.builder_window.parent()
        if hasattr(main_window, 'tool_info'):
            for tool_name in main_window.tool_info.keys():
                self.function_combo.addItem(tool_name)

        self.action_stack.addWidget(self.command_entry)
        self.action_stack.addWidget(self.function_combo)

        layout.addRow(self.translator.get(
            "action_type"), self.action_type_combo)
        layout.addRow(self.translator.get("action_value"), self.action_stack)

        # --- API Key ---
        self.api_key_check = QCheckBox()
        self.api_key_entry = QLineEdit(step_data.get("api_key", ""))
        self.api_key_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_check.toggled.connect(self.api_key_entry.setVisible)

        layout.addRow(self.translator.get(
            "requires_api_key"), self.api_key_check)
        layout.addRow(self.translator.get("api_key"), self.api_key_entry)

        # --- Buttons ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # --- Initial State ---
        self._load_initial_state()
        self._update_ui_visibility()

    def _add_regex_field(self, text=""):
        regex_input = QLineEdit(text)
        self.regex_fields_layout.addWidget(regex_input)
        self._update_ui_visibility()

    def _remove_regex_field(self):
        if self.regex_fields_layout.count() > 1:
            item = self.regex_fields_layout.takeAt(
                self.regex_fields_layout.count() - 1)
            if item.widget():
                item.widget().deleteLater()
        self._update_ui_visibility()

    def _load_initial_state(self):
        # Load Input Source
        input_source = self.step_data.get("input_source", "user")
        idx = self.input_source_combo.findData(input_source)
        if idx != -1:
            self.input_source_combo.setCurrentIndex(idx)

        # Load REGEX fields
        regexes = self.step_data.get("input_filter_regexes", [])
        if not regexes and "input_filter_regex" in self.step_data:  # Backward compatibility
            regexes = [self.step_data["input_filter_regex"]]

        if regexes:
            for r in regexes:
                self._add_regex_field(r)
        else:
            self._add_regex_field()

        # Load Action Type
        action_type = self.step_data.get("action_type", "command")
        if action_type == "function":
            self.action_type_combo.setCurrentIndex(
                3)  # function is now at index 3
            func_name = self.step_data.get("action_value")
            if func_name:
                idx = self.function_combo.findText(func_name)
                if idx != -1:
                    self.function_combo.setCurrentIndex(idx)
        else:
            # For command, batch_script, shell_script, they all use command_entry
            idx = self.action_type_combo.findData(action_type)
            if idx != -1:
                self.action_type_combo.setCurrentIndex(idx)
            else:
                self.action_type_combo.setCurrentIndex(0)  # default to command
            self.command_entry.setText(self.step_data.get("action_value", ""))

        # Load API Key
        self.api_key_check.setChecked(
            bool(self.step_data.get("requires_api_key")))
        self.api_key_entry.setVisible(self.api_key_check.isChecked())

    def _update_ui_visibility(self):
        # Regex visibility
        is_previous_step = self.input_source_combo.currentData().startswith("previous_step")
        self.regex_widget.setVisible(is_previous_step)
        self.regex_label.setVisible(is_previous_step)
        self.remove_regex_btn.setEnabled(self.regex_fields_layout.count() > 1)

        # Action stack visibility
        action_type = self.action_type_combo.currentData()
        is_function = action_type == "function"
        # 0 for command/script types, 1 for function
        self.action_stack.setCurrentIndex(1 if is_function else 0)

        # API Key visibility
        self.api_key_check.setVisible(not is_function)
        self.api_key_entry.setVisible(
            not is_function and self.api_key_check.isChecked())

        # Hide the QFormLayout rows by hiding the labels associated with the widgets
        api_check_label = self.form_layout.labelForField(self.api_key_check)
        if api_check_label:
            api_check_label.setVisible(not is_function)

        api_entry_label = self.form_layout.labelForField(self.api_key_entry)
        if api_entry_label:
            api_entry_label.setVisible(not is_function)

    def _select_icon(self):
        filepath, _ = QFileDialog.getOpenFileName(self, self.translator.get(
            "select_icon"), "", self.translator.get("image_files_filter"))
        if filepath:
            icons_dir = os.path.join(self.plugin_path, "icons")
            os.makedirs(icons_dir, exist_ok=True)
            filename = os.path.basename(filepath)
            new_path = os.path.join(icons_dir, filename)
            shutil.copy(filepath, new_path)
            self.step_data["icon"] = os.path.join(
                "icons", filename).replace("\\", "/")

    def accept(self):
        self.step_data["description"] = self.desc_entry.text()
        self.step_data["input_source"] = self.input_source_combo.currentData()

        if self.regex_widget.isVisible():
            regexes = []
            for i in range(self.regex_fields_layout.count()):
                widget = self.regex_fields_layout.itemAt(i).widget()
                if isinstance(widget, QLineEdit) and widget.text():
                    regexes.append(widget.text())
            self.step_data["input_filter_regexes"] = regexes
        elif "input_filter_regexes" in self.step_data:
            del self.step_data["input_filter_regexes"]

        if "input_filter_regex" in self.step_data:  # Clean up old key
            del self.step_data["input_filter_regex"]

        action_type = self.action_type_combo.currentData()
        self.step_data["action_type"] = action_type
        if action_type == "function":
            self.step_data["action_value"] = self.function_combo.currentText()
        else:
            # For command, batch_script, shell_script
            self.step_data["action_value"] = self.command_entry.text()

        if "command" in self.step_data and action_type != "command":
            del self.step_data["command"]

        if not self.api_key_check.isVisible():
            self.step_data["requires_api_key"] = False
            self.step_data["api_key"] = ""
        else:
            self.step_data["requires_api_key"] = self.api_key_check.isChecked()
            self.step_data["api_key"] = self.api_key_entry.text()

        if 'id' not in self.step_data:
            self.step_data['id'] = f"step_{datetime.now().timestamp()}"

        super().accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    from i18n import TRANSLATIONS

    class FakeTranslator:
        def get(
            self, key, **kwargs): return TRANSLATIONS['en'].get(key, key).format(**kwargs)
    main_win = QMainWindow()
    builder = PluginBuilderWindow(main_win, translator=FakeTranslator())
    builder.show()
    sys.exit(app.exec())
