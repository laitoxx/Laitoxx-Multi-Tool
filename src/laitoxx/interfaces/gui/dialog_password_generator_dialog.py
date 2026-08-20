from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from .dialog_helpers import build_ok_cancel_buttons as _build_ok_cancel_buttons


class PasswordGeneratorDialog(QDialog):
    def __init__(self, parent=None, tool_name="Password Generator"):
        super().__init__(parent)
        self.setWindowTitle("Password Generator")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.length_input = QLineEdit("16")
        form.addRow("Length:", self.length_input)

        self.count_input = QLineEdit("1")
        form.addRow("Count (max 100):", self.count_input)

        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Leave empty to use checkboxes below")
        self.custom_input.textChanged.connect(self._toggle_presets)
        form.addRow("Custom charset (only these):", self.custom_input)

        self.exclude_input = QLineEdit()
        self.exclude_input.setPlaceholderText("e.g. O0lI1  (applied after pool is built)")
        form.addRow("Exclude chars:", self.exclude_input)

        self._preset_widgets = []
        self.cb_upper = QCheckBox("Uppercase (A-Z)")
        self.cb_lower = QCheckBox("Lowercase (a-z)")
        self.cb_digits = QCheckBox("Digits (0-9)")
        self.cb_symbols = QCheckBox("Symbols (!@#...)")
        for cb in (self.cb_upper, self.cb_lower, self.cb_digits, self.cb_symbols):
            cb.setChecked(True)
            self._preset_widgets.append(cb)
            form.addRow("", cb)

        layout.addLayout(form)

        layout.addWidget(_build_ok_cancel_buttons(self))

    def _toggle_presets(self, text):
        for w in self._preset_widgets:
            w.setEnabled(not bool(text.strip()))

    def get_values(self):
        try:
            length = int(self.length_input.text())
            count = int(self.count_input.text())
        except ValueError:
            return None
        return {
            "length": length,
            "count": count,
            "custom_chars": self.custom_input.text().strip(),
            "exclude_chars": self.exclude_input.text().strip(),
            "use_upper": self.cb_upper.isChecked(),
            "use_lower": self.cb_lower.isChecked(),
            "use_digits": self.cb_digits.isChecked(),
            "use_symbols": self.cb_symbols.isChecked(),
        }
