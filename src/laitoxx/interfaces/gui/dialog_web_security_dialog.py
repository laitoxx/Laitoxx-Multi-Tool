from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from .dialog_helpers import build_ok_cancel_buttons as _build_ok_cancel_buttons


class WebSecurityDialog(QDialog):
    _CHECKS = [
        ("SSL/TLS Checker", "ssl"),
        ("CORS Checker", "cors"),
        ("Open Redirect Scanner", "redirect"),
        ("Security Headers", "headers"),
        ("Run All Checks", "all"),
    ]

    def __init__(self, parent=None, tool_name="Web Security Tools"):
        super().__init__(parent)
        self.setWindowTitle("Web Security Tools")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)

        info = QLabel(
            "Passive web security checks - no payloads injected.\nEnter the target URL and select which check to run."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        form.addRow("Target URL:", self.url_input)

        self.check_combo = QComboBox()
        for label, value in self._CHECKS:
            self.check_combo.addItem(label, value)
        form.addRow("Check:", self.check_combo)
        layout.addLayout(form)

        layout.addWidget(_build_ok_cancel_buttons(self))

    def get_values(self):
        url = self.url_input.text().strip()
        if not url:
            return None
        return {"url": url, "check": self.check_combo.currentData()}
