from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from laitoxx.core.settings.paths import RESOURCES_DIR
from laitoxx.core.settings.tos import mark_accepted


class UserAgreementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Laitoxx Project - User Agreement")
        self.setMinimumSize(700, 600)
        self.setModal(True)
        self.agreed = False

        layout = QVBoxLayout(self)

        title = QLabel("User Agreement for Laitoxx Project")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        self.agreement_text = QTextEdit()
        self.agreement_text.setReadOnly(True)
        try:
            agreement_path = RESOURCES_DIR / "legal" / "user_agreement.txt"
            self.agreement_text.setText(agreement_path.read_text(encoding="utf-8"))
        except Exception as e:
            self.agreement_text.setText(f"Error loading agreement: {e}")
        layout.addWidget(self.agreement_text)

        self.checkbox = QCheckBox("I have read and agree to comply with the User Agreement")
        self.checkbox.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(self.checkbox)

        buttons = QDialogButtonBox()
        self.agree_button = buttons.addButton("I Agree", QDialogButtonBox.ButtonRole.AcceptRole)
        self.agree_button.setEnabled(False)
        buttons.addButton("I Disagree", QDialogButtonBox.ButtonRole.RejectRole).clicked.connect(self._on_disagree)
        self.agree_button.clicked.connect(self._on_agree)
        self.checkbox.stateChanged.connect(lambda: self.agree_button.setEnabled(self.checkbox.isChecked()))
        layout.addWidget(buttons)

    def _on_agree(self):
        if self.checkbox.isChecked():
            self.agreed = True
            mark_accepted()
            self.accept()
        else:
            QMessageBox.warning(self, "Agreement Required", "Please check the checkbox to continue.")

    def _on_disagree(self):
        reply = QMessageBox.question(
            self,
            "Confirm Exit",
            "Are you sure you want to exit? You must agree to use this application.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.agreed = False
            self.reject()
