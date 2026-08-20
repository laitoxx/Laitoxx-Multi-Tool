from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from .dialog_helpers import build_ok_cancel_buttons as _build_ok_cancel_buttons


class CidrCalculatorDialog(QDialog):
    def __init__(self, parent=None, tool_name="CIDR Calculator"):
        super().__init__(parent)
        self.setWindowTitle("CIDR Calculator")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.cidr_input = QLineEdit()
        self.cidr_input.setPlaceholderText("e.g. 192.168.1.0/24 or 2001:db8::/32")
        form.addRow("CIDR notation:", self.cidr_input)

        self.check_ip_input = QLineEdit()
        self.check_ip_input.setPlaceholderText("Optional - check if this IP is in range")
        form.addRow("Check IP:", self.check_ip_input)

        self.subnet_input = QLineEdit("0")
        self.subnet_input.setPlaceholderText("0 = skip")
        form.addRow("Split into N subnets:", self.subnet_input)

        layout.addLayout(form)

        layout.addWidget(_build_ok_cancel_buttons(self))

    def get_values(self):
        cidr = self.cidr_input.text().strip()
        if not cidr:
            return None
        try:
            subnets = int(self.subnet_input.text().strip() or 0)
        except ValueError:
            subnets = 0
        return {
            "cidr": cidr,
            "check_ip": self.check_ip_input.text().strip(),
            "subnet_count": subnets,
        }
