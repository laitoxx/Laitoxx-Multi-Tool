import os
import hashlib
import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QTextEdit, QComboBox, QCheckBox, QPushButton, QDialogButtonBox,
    QFileDialog, QMessageBox, QColorDialog, QScrollArea, QWidget, QGridLayout,
)
from PyQt6.QtGui import QColor

from gui.translator import translator
from settings.tos import mark_accepted
from plugin_builder import PluginBuilderWindow


def _build_ok_cancel_buttons(parent: QDialog) -> QDialogButtonBox:
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(parent.accept)
    buttons.rejected.connect(parent.reject)
    return buttons


def _open_file(parent: QDialog, title: str, file_filter: str) -> str | None:
    filepath, _ = QFileDialog.getOpenFileName(parent, title, "", file_filter)
    return filepath or None


def _save_file(parent: QDialog, title: str, file_filter: str) -> str | None:
    filepath, _ = QFileDialog.getSaveFileName(parent, title, "", file_filter)
    return filepath or None


class CustomInputDialog(QDialog):
    def __init__(self, parent=None, title='Input Required', prompt='Enter value:'):
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


class TelegramSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Telegram Search")
        layout = QVBoxLayout(self)
        self.result = None

        self._search_map = {
            'Search by Username': 'TelegramUsername',
            'Search by TG ID': 'TelegramID',
            'Search by Channel': 'TelegramChannel',
            'Search by Chat': 'TelegramChat',
            'Parse Channel': 'TelegramCParser',
        }

        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("Enter query (e.g., @username or numeric ID)")
        layout.addWidget(self.input_text)

        button_row = QHBoxLayout()
        for display_text, method_name in self._search_map.items():
            btn = QPushButton(display_text)
            btn.clicked.connect(lambda _, m=method_name, d=display_text: self._set_result(m, d))
            button_row.addWidget(btn)
        layout.addLayout(button_row)

    def _set_result(self, method_name, display_text):
        query = self.input_text.text()
        if query:
            self.result = {"method": method_name, "query": query, "prompt": display_text}
            self.accept()

    def get_values(self):
        return self.result


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
            "Pure Python implementation — may be slow for large wordlists.\n"
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
                return {
                    "charset": charset,
                    "algorithm": alg,
                    "chain_length": int(self.chain_length_input.text()),
                    "num_chains": int(self.num_chains_input.text()),
                    "password_len": int(self.password_len_input.text()),
                    "output_file": out,
                } if all([charset, alg, out]) else None
            except ValueError:
                return None
        return None


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


class WebSecurityDialog(QDialog):
    _CHECKS = [
        ("SSL/TLS Checker",        "ssl"),
        ("CORS Checker",           "cors"),
        ("Open Redirect Scanner",  "redirect"),
        ("Security Headers",       "headers"),
        ("Run All Checks",         "all"),
    ]

    def __init__(self, parent=None, tool_name="Web Security Tools"):
        super().__init__(parent)
        self.setWindowTitle("Web Security Tools")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)

        info = QLabel(
            "Passive web security checks — no payloads injected.\n"
            "Enter the target URL and select which check to run."
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


class TextTransformerDialog(QDialog):
    _MODES = [
        ("Leet speak",      "leet"),
        ("Morse code",      "morse"),
        ("Binary",          "binary"),
        ("Hex",             "hex"),
        ("ROT-13",          "rot13"),
        ("Caesar cipher",   "caesar"),
        ("Base64",          "base64"),
        ("URL encode",      "url"),
        ("Reverse",         "reverse"),
        ("UPPERCASE",       "upper"),
        ("lowercase",       "lower"),
    ]
    _HAS_ACTION = {"leet", "morse", "binary", "hex", "caesar", "base64", "url"}

    def __init__(self, parent=None, tool_name="Text Transformer"):
        super().__init__(parent)
        self.setWindowTitle("Text Transformer")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.mode_combo = QComboBox()
        for label, value in self._MODES:
            self.mode_combo.addItem(label, value)
        self.mode_combo.currentIndexChanged.connect(self._toggle_action)
        form.addRow("Mode:", self.mode_combo)

        self.action_combo = QComboBox()
        self.action_combo.addItem("Encode", "encode")
        self.action_combo.addItem("Decode", "decode")
        self._action_label = QLabel("Action:")
        form.addRow(self._action_label, self.action_combo)

        self._shift_label = QLabel("Caesar shift (1-25):")
        self.shift_input = QLineEdit("3")
        form.addRow(self._shift_label, self.shift_input)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter text to transform...")
        self.text_input.setMinimumHeight(100)
        form.addRow("Text:", self.text_input)

        layout.addLayout(form)
        self._toggle_action()

        layout.addWidget(_build_ok_cancel_buttons(self))

    def _toggle_action(self):
        mode = self.mode_combo.currentData()
        has_action = mode in self._HAS_ACTION
        self._action_label.setVisible(has_action)
        self.action_combo.setVisible(has_action)
        self._shift_label.setVisible(mode == "caesar")
        self.shift_input.setVisible(mode == "caesar")

    def get_values(self):
        text = self.text_input.toPlainText()
        if not text:
            return None
        mode = self.mode_combo.currentData()
        result = {"mode": mode, "action": self.action_combo.currentData(), "text": text}
        if mode == "caesar":
            try:
                result["shift"] = int(self.shift_input.text())
            except ValueError:
                result["shift"] = 3
        return result


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
        self.cb_upper   = QCheckBox("Uppercase (A-Z)")
        self.cb_lower   = QCheckBox("Lowercase (a-z)")
        self.cb_digits  = QCheckBox("Digits (0-9)")
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
            count  = int(self.count_input.text())
        except ValueError:
            return None
        return {
            "length":        length,
            "count":         count,
            "custom_chars":  self.custom_input.text().strip(),
            "exclude_chars": self.exclude_input.text().strip(),
            "use_upper":     self.cb_upper.isChecked(),
            "use_lower":     self.cb_lower.isChecked(),
            "use_digits":    self.cb_digits.isChecked(),
            "use_symbols":   self.cb_symbols.isChecked(),
        }


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
        text    = self.text_input.toPlainText()
        if not pattern or not text:
            return None
        flags = [name for name, cb in self.flag_checks.items() if cb.isChecked()]
        return {"pattern": pattern, "text": text, "flags": flags}


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
        self.check_ip_input.setPlaceholderText("Optional — check if this IP is in range")
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
            "cidr":         cidr,
            "check_ip":     self.check_ip_input.text().strip(),
            "subnet_count": subnets,
        }


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
        buttons.addButton(translator.get("reset_theme"), QDialogButtonBox.ButtonRole.ResetRole).clicked.connect(self._reset)
        buttons.addButton(translator.get("save_theme"), QDialogButtonBox.ButtonRole.AcceptRole).clicked.connect(self.accept)
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
                if 'rgba' in current_str:
                    alpha = float(current_str.split(',')[-1].strip()[:-1])
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
            with open("User Agreement.txt", "r", encoding="utf-8") as f:
                self.agreement_text.setText(f.read())
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
            self, "Confirm Exit",
            "Are you sure you want to exit? You must agree to use this application.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.agreed = False
            self.reject()


class LuaPluginInputDialog(QDialog):
    """Dialog to collect input for a Lua plugin execution."""

    def __init__(self, parent=None, plugin_meta=None):
        super().__init__(parent)
        self.plugin_meta = plugin_meta
        self.setWindowTitle(plugin_meta.name if plugin_meta else "Lua Plugin")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        if plugin_meta:
            info = QLabel(f"{plugin_meta.name} v{plugin_meta.version}\n"
                          f"by {plugin_meta.author}\n\n"
                          f"{plugin_meta.description}")
            info.setWordWrap(True)
            layout.addWidget(info)

        form = QFormLayout()
        self.query_input = QLineEdit()
        prompt_map = {
            "search": "Enter search query:",
            "processor": "Paste text to process:",
            "formatter": "Paste data to format:",
            "passive_scanner": "Enter target:",
        }
        ptype = plugin_meta.plugin_type if plugin_meta else "search"
        prompt = prompt_map.get(ptype, "Enter input:")
        self.query_input.setPlaceholderText(prompt)
        form.addRow(prompt, self.query_input)
        layout.addLayout(form)

        layout.addWidget(_build_ok_cancel_buttons(self))

    def get_query(self):
        return self.query_input.text().strip()


class LuaPluginConfigDialog(QDialog):
    """Dialog to edit config values for a Lua plugin based on its config_schema."""

    def __init__(self, parent=None, plugin_meta=None):
        super().__init__(parent)
        self.plugin_meta = plugin_meta
        self.setWindowTitle(
            translator.get("lua_plugin_settings_title",
                           name=plugin_meta.name if plugin_meta else "Plugin")
        )
        self.setMinimumWidth(450)
        layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        layout.addLayout(self.form_layout)

        self._widgets = {}
        schema = []
        if plugin_meta and plugin_meta.config_schema:
            raw = plugin_meta.config_schema
            if hasattr(raw, 'values'):
                # Lua table (1-based array)
                try:
                    schema = [_lua_config_entry(raw[i]) for i in range(1, 100)
                              if raw[i] is not None]
                except (KeyError, IndexError, TypeError):
                    try:
                        from lua_engine import _lua_table_to_python
                        schema = _lua_table_to_python(raw)
                        if not isinstance(schema, list):
                            schema = []
                    except Exception:
                        schema = []
            elif isinstance(raw, list):
                schema = raw

        for entry in schema:
            if not isinstance(entry, dict):
                continue
            key = entry.get("key", "")
            label = entry.get("label", key)
            field_type = entry.get("type", "string")
            default = entry.get("default", "")
            current = plugin_meta.config_values.get(key, default) if plugin_meta else default

            if field_type == "boolean":
                widget = QCheckBox()
                widget.setChecked(bool(current))
            elif field_type == "number":
                widget = QLineEdit(str(current))
            else:
                widget = QLineEdit(str(current) if current else "")

            self.form_layout.addRow(label + ":", widget)
            self._widgets[key] = (widget, field_type)

        if not schema:
            layout.addWidget(QLabel(translator.get("lua_no_config_schema")))

        layout.addWidget(_build_ok_cancel_buttons(self))

    def get_config(self) -> dict:
        result = {}
        for key, (widget, field_type) in self._widgets.items():
            if field_type == "boolean":
                result[key] = widget.isChecked()
            elif field_type == "number":
                try:
                    result[key] = float(widget.text())
                except ValueError:
                    result[key] = 0
            else:
                result[key] = widget.text()
        return result


def _lua_config_entry(tbl) -> dict:
    """Convert a single Lua config_schema entry to a Python dict."""
    if isinstance(tbl, dict):
        return tbl
    if hasattr(tbl, '__getitem__'):
        return {
            "key": tbl.get("key", "") if hasattr(tbl, 'get') else tbl["key"],
            "label": tbl.get("label", "") if hasattr(tbl, 'get') else tbl["label"],
            "type": tbl.get("type", "string") if hasattr(tbl, 'get') else tbl["type"],
            "default": tbl.get("default", "") if hasattr(tbl, 'get') else tbl.get("default", ""),
        }
    return {}


class PluginExecutionWindow(QDialog):
    def __init__(self, plugin_data, parent=None):
        super().__init__(parent)
        self.plugin_data = plugin_data
        self.parent_window = parent
        self.setWindowTitle(translator.get("running_plugin", name=plugin_data.get('name')))
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        self.button_box = QDialogButtonBox()
        self.button_box.addButton(translator.get("edit_plugin"), QDialogButtonBox.ButtonRole.ActionRole).clicked.connect(self._edit_plugin)
        self.button_box.addButton(translator.get("save_log"), QDialogButtonBox.ButtonRole.ActionRole).clicked.connect(self._save_log)
        self.button_box.addButton(translator.get("close"), QDialogButtonBox.ButtonRole.RejectRole).clicked.connect(self.accept)
        self.button_box.setVisible(False)
        layout.addWidget(self.button_box)

    def append_log(self, text):
        self.log_area.append(text)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def execution_finished(self):
        self.append_log(translator.get("execution_finished"))
        self.button_box.setVisible(True)

    def _edit_plugin(self):
        plugin_path = self.plugin_data.get('plugin_path')
        if plugin_path and os.path.isdir(plugin_path):
            builder = PluginBuilderWindow(self.parent_window, plugin_path=plugin_path, translator=translator)
            if builder.exec():
                self.parent_window.reload_plugins_and_ui()
        else:
            logging.error(translator.get("plugin_path_error", name=self.plugin_data.get('name')))

    def _save_log(self):
        content = self.log_area.toPlainText()
        filepath = _save_file(self, translator.get("save_log"), "Text Files (*.txt);;All Files (*)")
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                logging.error(translator.get("log_save_error", e=e))
