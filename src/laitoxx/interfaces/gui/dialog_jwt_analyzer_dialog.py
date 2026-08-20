from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .dialog_helpers import build_ok_cancel_buttons as _build_ok_cancel_buttons
from .dialog_helpers import open_file as _open_file


class JwtAnalyzerDialog(QDialog):
    def __init__(self, parent=None, tool_name="JWT Analyzer"):
        super().__init__(parent)
        self.setWindowTitle("JWT Analyzer")
        self.setMinimumWidth(520)
        self.tool_name = tool_name
        layout = QVBoxLayout(self)

        info = QLabel(
            "Paste a JWT token to decode its header and payload,\n"
            "or select 'Crack' mode to brute-force the HMAC secret via a wordlist.\n"
            "Supported: HS256, HS384, HS512."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Analyze (decode & inspect)", "analyze")
        self.mode_combo.addItem("Crack (wordlist brute-force)", "crack")
        self.mode_combo.currentIndexChanged.connect(self._toggle_wordlist)
        layout.addWidget(self.mode_combo)

        form = QFormLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
        form.addRow("JWT Token:", self.token_input)

        self._wordlist_row_label = QLabel("Wordlist:")
        self._wordlist_row_widget = QWidget()
        wl_layout = QHBoxLayout(self._wordlist_row_widget)
        wl_layout.setContentsMargins(0, 0, 0, 0)
        self.wordlist_input = QLineEdit()
        self.wordlist_input.setPlaceholderText("Path to wordlist file")
        browse = QPushButton("Browse")
        browse.clicked.connect(self._browse)
        wl_layout.addWidget(self.wordlist_input)
        wl_layout.addWidget(browse)
        form.addRow(self._wordlist_row_label, self._wordlist_row_widget)

        layout.addLayout(form)
        self._toggle_wordlist()

        layout.addWidget(_build_ok_cancel_buttons(self))

    def _toggle_wordlist(self):
        crack = self.mode_combo.currentData() == "crack"
        self._wordlist_row_label.setVisible(crack)
        self._wordlist_row_widget.setVisible(crack)

    def _browse(self):
        path = _open_file(self, "Select Wordlist", "Text Files (*.txt);;All Files (*)")
        if path:
            self.wordlist_input.setText(path)

    def get_values(self):
        token = self.token_input.text().strip()
        if not token:
            return None
        mode = self.mode_combo.currentData()
        result = {"token": token, "mode": mode}
        if mode == "crack":
            wl = self.wordlist_input.text().strip()
            if not wl:
                return None
            result["wordlist"] = wl
        return result
