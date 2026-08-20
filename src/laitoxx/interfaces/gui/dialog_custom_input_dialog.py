from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from .dialog_helpers import build_ok_cancel_buttons as _build_ok_cancel_buttons


class CustomInputDialog(QDialog):
    def __init__(self, parent=None, title="Input Required", prompt="Enter value:"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(prompt))
        self.input_text = QLineEdit(self)
        layout.addWidget(self.input_text)
        layout.addWidget(_build_ok_cancel_buttons(self))

    def get_text(self):
        return self.input_text.text()
