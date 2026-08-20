from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from .dialog_helpers import build_ok_cancel_buttons as _build_ok_cancel_buttons
from .dialog_helpers import open_file as _open_file


class SteganographyDialog(QDialog):
    def __init__(self, parent=None, tool_name="Steganography"):
        super().__init__(parent)
        self.setWindowTitle(f"{tool_name} Configuration")
        self.setMinimumWidth(500)
        self.tool_name = tool_name

        # Root layout
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "This tool allows you to hide or extract secret messages within image files.\n\n"
            "Select 'Hide' to embed a message, or 'Extract' to retrieve one.\n"
            "A cover image is required for both operations."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Hide Message/File", "hide")
        self.mode_combo.addItem("Extract Message/File", "extract")
        self.mode_combo.currentIndexChanged.connect(self._toggle_mode)
        layout.addWidget(self.mode_combo)

        # Inputs layout
        self.form_layout = QFormLayout()
        layout.addLayout(self.form_layout)

        # Image File Input
        self.image_input = QLineEdit()
        self.image_input.setPlaceholderText("Path to cover image file")
        browse_img_btn = QPushButton("Browse")
        browse_img_btn.clicked.connect(self._browse_image)
        img_row = QHBoxLayout()
        img_row.addWidget(self.image_input)
        img_row.addWidget(browse_img_btn)
        self.form_layout.addRow("Cover Image:", img_row)

        # Secret Message (Toggled)
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Enter the secret message to hide...")
        self.message_input.setMinimumHeight(100)
        self._message_label = QLabel("Secret Message:")
        self.form_layout.addRow(self._message_label, self.message_input)

        # Password (Optional)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Optional password for encryption")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.form_layout.addRow("Password:", self.password_input)

        self._toggle_mode()

        # Dialog control buttons
        layout.addWidget(_build_ok_cancel_buttons(self))

    def _browse_image(self):
        # Uses the shared helper defined at the top of dialogs.py
        filepath = _open_file(self, "Select Cover Image", "Images (*.png *.jpg *.bmp);;All Files (*)")
        if filepath:
            self.image_input.setText(filepath)

    def _toggle_mode(self):
        is_hide = self.mode_combo.currentData() == "hide"
        self._message_label.setVisible(is_hide)
        self.message_input.setVisible(is_hide)

    def get_values(self):
        mode = self.mode_combo.currentData()
        image_path = self.image_input.text().strip()
        password = self.password_input.text().strip()

        if not image_path:
            return None

        result = {"mode": mode, "image_path": image_path, "password": password}

        if mode == "hide":
            message = self.message_input.toPlainText().strip()
            if not message:
                return None
            result["message"] = message

        return result
