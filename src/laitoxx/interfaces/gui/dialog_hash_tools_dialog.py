import hashlib

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
from .dialog_helpers import save_file as _save_file


class HashToolsDialog(QDialog):
    _INSTRUCTIONS = {
        "Text Hasher": (
            "This tool hashes text using various cryptographic algorithms.\n\n"
            "Available algorithms: MD5, SHA1, SHA256, SHA512, etc.\n"
            "Note: MD5 and SHA1 are insecure for cryptography.\n"
            "Use SHA256 or stronger for security."
        ),
        "Hash Identifier": (
            "This tool identifies possible types of a given hash string.\n\n"
            "Enter a hash (e.g., a long string of letters/numbers).\n"
            "It provides possible matches, not definitive identification."
        ),
        "Dictionary Cracker": (
            "This tool cracks a hash using a wordlist (dictionary attack).\n\n"
            "Pure Python implementation - may be slow for large wordlists.\n"
            "For better performance, use specialized tools like Hashcat.\n\n"
            "Supported algorithms: md5, sha1, sha256, etc."
        ),
        "Rainbow Table Gen": (
            "This tool generates a rainbow table for password cracking.\n\n"
            "WARNING: Very slow and resource-intensive!\n\n"
            "Parameters:\n"
            "- Charset: Characters to use (e.g., 'abc123')\n"
            "- Chain length: Hash/reduce operations per chain\n"
            "- Chains: Number of starting points\n"
            "- Length: Max password length"
        ),
    }

    def __init__(self, parent=None, tool_name=""):
        super().__init__(parent)
        self.setWindowTitle(f"{tool_name} Configuration")
        self.setMinimumWidth(500)
        self.tool_name = tool_name
        layout = QVBoxLayout(self)

        instructions = QLabel(self._INSTRUCTIONS.get(tool_name, ""))
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self.form_layout = QFormLayout()
        layout.addLayout(self.form_layout)
        self._build_form(tool_name)

        layout.addWidget(_build_ok_cancel_buttons(self))

    def _make_algo_combo(self, default="sha256"):
        combo = QComboBox()
        combo.addItems(sorted(hashlib.algorithms_available))
        combo.setCurrentText(default)
        return combo

    def _build_form(self, tool_name):
        fl = self.form_layout
        if tool_name == "Text Hasher":
            self.text_input = QTextEdit()
            self.text_input.setPlaceholderText("Enter the text to hash (any string)")
            fl.addRow("Text:", self.text_input)
            self.algorithm_combo = self._make_algo_combo("sha256")
            fl.addRow("Algorithm:", self.algorithm_combo)

        elif tool_name == "Hash Identifier":
            self.hash_input = QLineEdit()
            self.hash_input.setPlaceholderText("Enter hash string")
            fl.addRow("Hash:", self.hash_input)

        elif tool_name == "Dictionary Cracker":
            self.hash_input = QLineEdit()
            self.hash_input.setPlaceholderText("Enter hash to crack (lowercase hex)")
            fl.addRow("Hash:", self.hash_input)
            self.algorithm_combo = self._make_algo_combo("md5")
            fl.addRow("Algorithm:", self.algorithm_combo)
            self.wordlist_input = QLineEdit()
            self.wordlist_input.setPlaceholderText("Path to wordlist file")
            browse = QPushButton("Browse")
            browse.clicked.connect(self._browse_wordlist)
            row = QHBoxLayout()
            row.addWidget(self.wordlist_input)
            row.addWidget(browse)
            fl.addRow("Wordlist:", row)

        elif tool_name == "Rainbow Table Gen":
            self.charset_input = QLineEdit("abcdefghijklmnopqrstuvwxyz0123456789")
            fl.addRow("Charset:", self.charset_input)
            self.algorithm_combo = self._make_algo_combo("md5")
            fl.addRow("Algorithm:", self.algorithm_combo)
            self.chain_length_input = QLineEdit("1000")
            fl.addRow("Chain Length:", self.chain_length_input)
            self.num_chains_input = QLineEdit("10000")
            fl.addRow("Number of Chains:", self.num_chains_input)
            self.password_len_input = QLineEdit("6")
            fl.addRow("Password Length:", self.password_len_input)
            self.output_file_input = QLineEdit("rainbow_table.csv")
            browse = QPushButton("Browse")
            browse.clicked.connect(self._browse_output)
            row = QHBoxLayout()
            row.addWidget(self.output_file_input)
            row.addWidget(browse)
            fl.addRow("Output File:", row)

    def _browse_wordlist(self):
        filepath = _open_file(self, "Select Wordlist", "Text Files (*.txt);;All Files (*)")
        if filepath:
            self.wordlist_input.setText(filepath)

    def _browse_output(self):
        filepath = _save_file(self, "Save Rainbow Table", "CSV Files (*.csv);;All Files (*)")
        if filepath:
            self.output_file_input.setText(filepath)

    def get_values(self):
        if self.tool_name == "Text Hasher":
            text = self.text_input.toPlainText().strip()
            return {"text": text, "algorithm": self.algorithm_combo.currentText()} if text else None

        if self.tool_name == "Hash Identifier":
            h = self.hash_input.text().strip()
            return {"hash": h} if h else None

        if self.tool_name == "Dictionary Cracker":
            h = self.hash_input.text().strip()
            alg = self.algorithm_combo.currentText()
            wl = self.wordlist_input.text().strip()
            return {"hash": h, "algorithm": alg, "wordlist": wl} if all([h, alg, wl]) else None

        if self.tool_name == "Rainbow Table Gen":
            charset = self.charset_input.text().strip()
            alg = self.algorithm_combo.currentText()
            out = self.output_file_input.text().strip()
            try:
                return (
                    {
                        "charset": charset,
                        "algorithm": alg,
                        "chain_length": int(self.chain_length_input.text()),
                        "num_chains": int(self.num_chains_input.text()),
                        "password_len": int(self.password_len_input.text()),
                        "output_file": out,
                    }
                    if all([charset, alg, out])
                    else None
                )
            except ValueError:
                return None
        return None
