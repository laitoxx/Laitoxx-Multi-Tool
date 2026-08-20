from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from laitoxx.core.localization.i18n import translator


class ThemeEditorDialog(QDialog):
    def __init__(self, parent, current_theme):
        super().__init__(parent)
        self.setWindowTitle(translator.get("theme_editor_title"))
        self.setMinimumSize(400, 300)
        self.theme_data = current_theme.copy()
        self.original_theme = current_theme

        layout = QVBoxLayout(self)

        self.element_selector = QComboBox(self)
        theme_map_raw = translator.get("theme_map")
        self.theme_map = theme_map_raw if isinstance(theme_map_raw, dict) else {}
        for display_name in self.theme_map.values():
            self.element_selector.addItem(display_name)
        self.element_selector.currentIndexChanged.connect(self._update_preview)

        self.color_preview = QPushButton(self)
        self.color_preview.clicked.connect(self._open_color_picker)

        layout.addWidget(QLabel(translator.get("select_element_to_edit")))
        layout.addWidget(self.element_selector)
        layout.addWidget(self.color_preview)

        buttons = QDialogButtonBox()
        buttons.addButton(translator.get("reset_theme"), QDialogButtonBox.ButtonRole.ResetRole).clicked.connect(
            self._reset
        )
        buttons.addButton(translator.get("save_theme"), QDialogButtonBox.ButtonRole.AcceptRole).clicked.connect(
            self.accept
        )
        buttons.addButton(translator.get("close"), QDialogButtonBox.ButtonRole.RejectRole).clicked.connect(self.reject)
        layout.addWidget(buttons)

        self._update_preview()

    def _selected_key(self):
        text = self.element_selector.currentText()
        return next((k for k, v in self.theme_map.items() if v == text), None)

    def _update_preview(self):
        key = self._selected_key()
        if key:
            color_val = self.theme_data.get(key, "#ffffff")
            self.color_preview.setStyleSheet(f"background-color: {color_val};")
            self.color_preview.setText(color_val)

    def _open_color_picker(self):
        key = self._selected_key()
        if not key:
            return
        current_str = self.theme_data.get(key, "#ffffff")
        dialog = QColorDialog(self)
        dialog.setCurrentColor(QColor(current_str))
        dialog.setWindowTitle(translator.get("edit_color_title", element=self.element_selector.currentText()))
        if dialog.exec():
            color = dialog.currentColor()
            if color.isValid():
                if "rgba" in current_str:
                    alpha = float(current_str.split(",")[-1].strip()[:-1])
                    self.theme_data[key] = f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"
                else:
                    self.theme_data[key] = color.name()
                self._update_preview()
                self.parent().theme_data = self.theme_data
                self.parent().apply_theme()

    def _reset(self):
        self.parent().load_initial_theme(use_last_saved=False)
        self.theme_data = self.parent().theme_data.copy()
        self._update_preview()
        self.parent().apply_theme()

    def reject(self):
        self.parent().theme_data = self.original_theme
        self.parent().apply_theme()
        super().reject()

    def get_theme_data(self):
        return self.theme_data
