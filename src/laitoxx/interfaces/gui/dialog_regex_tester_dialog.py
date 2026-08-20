from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .dialog_helpers import build_ok_cancel_buttons as _build_ok_cancel_buttons


class RegexTesterDialog(QDialog):
    _FLAGS = ["IGNORECASE", "MULTILINE", "DOTALL", "VERBOSE", "ASCII"]

    def __init__(self, parent=None, tool_name="Regex Tester"):
        super().__init__(parent)
        self.setWindowTitle("Regex Tester")
        self.setMinimumWidth(540)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText(r"e.g.  \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
        form.addRow("Pattern:", self.pattern_input)

        flags_widget = QWidget()
        flags_layout = QHBoxLayout(flags_widget)
        flags_layout.setContentsMargins(0, 0, 0, 0)
        self.flag_checks = {}
        for name in self._FLAGS:
            cb = QCheckBox(name)
            self.flag_checks[name] = cb
            flags_layout.addWidget(cb)
        form.addRow("Flags:", flags_widget)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Paste the text to test against...")
        self.text_input.setMinimumHeight(140)
        form.addRow("Test text:", self.text_input)

        layout.addLayout(form)

        layout.addWidget(_build_ok_cancel_buttons(self))

    def get_values(self):
        pattern = self.pattern_input.text()
        text = self.text_input.toPlainText()
        if not pattern or not text:
            return None
        flags = [name for name, cb in self.flag_checks.items() if cb.isChecked()]
        return {"pattern": pattern, "text": text, "flags": flags}
