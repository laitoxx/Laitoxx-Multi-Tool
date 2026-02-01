from script.tools.temp_mail import (temp_mail)
from script.tools.data_search import data_search_tool
from script.tools.nmap_scanner.nmap_scanner import nmap_scanner_tool
from script.tools.hash_tools.rainbow_table_generator import rainbow_table_tool
from script.tools.hash_tools.dictionary_cracker import dictionary_cracker_tool
from script.tools.hash_tools.hash_identifier import hash_identifier_tool
from script.tools.hash_tools.text_hasher import text_hasher_tool
from ddos_module.attacks import layer4, layer7
from ddos_module.main import run_ddos_attack
from script.tools.phishing_bot import phishing
from script.tools.web_crawler import web_crawler
from script.tools.obfuscator import obfuscate_tool
from script.tools.user_checker import check_username
from script.tools.telegram_search import telegram_search
from script.tools.google_osint import google_osint
from script.tools.ip_logger import logger_ip
from script.tools.subdomain_finder import find_subdomains
from script.tools.sql_scanner import sql_injection_scanner_tool
from script.tools.admin_finder import find_admin_panel
from script.tools.mac_lookup import search_mac_address
from script.tools.xss_scanner import xss_scan
from script.tools.url_checker import check_url
from script.tools.site_checker import check_site
from script.tools.proxy_fetcher import get_proxy_list
from script.tools.db_searcher import search_database
from script.tools.gmail_osint import gmail_osint
from script.tools.port_scanner import port_scanner_tool
from script.tools.password_generator import password_generator_tool
from script.tools.text_transformer import transform_text
from script.tools.website_info import get_website_info
from script.tools.email_validator import check_email_address
from script.tools.ip_info import get_ip
from script.tools.user_search_by_phone import search_by_number
import sys
import io
import contextlib
import builtins
import os
import requests
import json
import re
import threading
import time
import platform
import logging
import datetime
import subprocess
import hashlib
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QStackedWidget, QLabel, QGraphicsBlurEffect,
                             QTextEdit, QGridLayout, QInputDialog, QSplitter,
                             QHBoxLayout, QSpacerItem, QSizePolicy, QColorDialog,
                             QFileDialog, QDialog, QFormLayout, QLineEdit,
                             QDialogButtonBox, QScrollArea, QComboBox, QCheckBox,
                             QMessageBox)
from PyQt6.QtGui import QMovie, QResizeEvent, QColor, QFont, QPixmap, QIcon
from PyQt6.QtCore import Qt, QUrl, QObject, pyqtSignal, QThread
from PyQt6.QtMultimedia import QMediaPlayer, QVideoSink, QVideoFrame

# --- Local Imports ---
from plugin_builder import PluginBuilderWindow
from i18n import TRANSLATIONS

# --- Translator Setup ---


class Translator:
    def __init__(self):
        self.lang = 'en'
        self.translations = TRANSLATIONS

    def set_language(self, lang):
        if lang in self.translations:
            self.lang = lang

    def get(self, key, **kwargs):
        translation = self.translations.get(self.lang, {}).get(key, key)
        if isinstance(translation, str):
            return translation.format(**kwargs)
        return translation


translator = Translator()

# --- Logging Setup ---
LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
log_filename = os.path.join(
    LOG_DIR, f"gui_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)

logging.info("Application starting...")

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import tool functions
# Hashing and Nmap tools


class PluginExecutionWindow(QDialog):
    def __init__(self, plugin_data, parent=None):
        super().__init__(parent)
        self.plugin_data = plugin_data
        self.parent_window = parent
        self.setWindowTitle(translator.get(
            "running_plugin", name=plugin_data.get('name')))
        self.setMinimumSize(700, 500)

        self.layout = QVBoxLayout(self)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.layout.addWidget(self.log_area)

        self.button_box = QDialogButtonBox()
        self.edit_button = self.button_box.addButton(translator.get(
            "edit_plugin"), QDialogButtonBox.ButtonRole.ActionRole)
        self.save_log_button = self.button_box.addButton(
            translator.get("save_log"), QDialogButtonBox.ButtonRole.ActionRole)
        self.close_button = self.button_box.addButton(
            translator.get("close"), QDialogButtonBox.ButtonRole.RejectRole)

        self.edit_button.clicked.connect(self.edit_plugin)
        self.save_log_button.clicked.connect(self.save_log)
        self.close_button.clicked.connect(self.accept)

        self.button_box.setVisible(False)
        self.layout.addWidget(self.button_box)

    def append_log(self, text):
        self.log_area.append(text)
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum())

    def execution_finished(self):
        self.append_log(translator.get("execution_finished"))
        self.button_box.setVisible(True)

    def edit_plugin(self):
        plugin_path = self.plugin_data.get('plugin_path')
        if plugin_path and os.path.isdir(plugin_path):
            builder = PluginBuilderWindow(
                self.parent_window, plugin_path=plugin_path, translator=translator)
            if builder.exec():
                self.parent_window.reload_plugins_and_ui()
        else:
            logging.error(translator.get("plugin_path_error",
                          name=self.plugin_data.get('name')))

    def save_log(self):
        log_content = self.log_area.toPlainText()
        filepath, _ = QFileDialog.getSaveFileName(self, translator.get(
            "save_log"), "", "Text Files (*.txt);;All Files (*)")
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(log_content)
            except Exception as e:
                logging.error(translator.get("log_save_error", e=e))


CONFIG_FILE = "background_config.txt"
DEFAULT_THEME_FILE = "theme.json"
LAST_THEME_CONFIG_FILE = "last_theme.txt"
PLUGIN_DIR = "plugins"
AGREEMENT_CONFIG_FILE = "user_agreement_accepted.txt"


def remove_ansi_codes(text):
    return re.sub(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]', '', text)


def save_config(filepath, value):
    with open(filepath, "w") as f:
        f.write(value)


def load_config(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return f.read().strip()
    return None


def check_user_agreement():
    """Check if user has already agreed to the terms."""
    agreement_file = load_config(AGREEMENT_CONFIG_FILE)
    return agreement_file == "agreed"


def save_user_agreement():
    """Save that user has agreed to the terms."""
    save_config(AGREEMENT_CONFIG_FILE, "agreed")


def load_theme(filepath):
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None
    return None


def save_theme(filepath, theme_data):
    with open(filepath, "w") as f:
        json.dump(theme_data, f, indent=4)


class GlassButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)


class CustomInputDialog(QDialog):
    def __init__(self, parent=None, title='Input Required', prompt='Enter value:'):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.layout = QVBoxLayout(self)
        self.prompt_label = QLabel(prompt)
        self.layout.addWidget(self.prompt_label)
        self.input_text = QLineEdit(self)
        self.layout.addWidget(self.input_text)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_text(self):
        return self.input_text.text()


class DataSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translator.get("data_search_title"))
        self.setMinimumWidth(420)
        self.layout = QFormLayout(self)

        self.mode_combo = QComboBox(self)
        self.mode_combo.addItem(translator.get(
            "data_search_phone_option"), "phone")
        self.mode_combo.addItem(translator.get(
            "data_search_email_option"), "email")
        self.mode_combo.addItem(translator.get(
            "data_search_telegram_option"), "telegram")
        self.layout.addRow(translator.get(
            "data_search_mode_label"), self.mode_combo)

        self.value_input = QLineEdit(self)
        self.layout.addRow(translator.get(
            "data_search_value_label"), self.value_input)

        self.mode_combo.currentIndexChanged.connect(self.update_placeholder)
        self.update_placeholder()

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout.addRow(button_box)

    def update_placeholder(self):
        mode = self.mode_combo.currentData()
        if mode == "phone":
            placeholder = translator.get("data_search_phone_placeholder")
        elif mode == "email":
            placeholder = translator.get("data_search_email_placeholder")
        else:
            placeholder = translator.get("data_search_telegram_placeholder")
        self.value_input.setPlaceholderText(placeholder)

    def get_values(self):
        value = self.value_input.text().strip()
        if not value:
            return None
        return {"mode": self.mode_combo.currentData(), "value": value}


class ThemeEditorDialog(QDialog):
    def __init__(self, parent, current_theme):
        super().__init__(parent)
        self.setWindowTitle(translator.get("theme_editor_title"))
        self.setMinimumSize(400, 300)
        self.theme_data = current_theme.copy()
        self.original_theme = current_theme

        self.layout = QVBoxLayout(self)

        self.element_selector = QComboBox(self)
        self.theme_map = translator.get("theme_map")
        for display_name in self.theme_map.values():
            self.element_selector.addItem(display_name)
        self.element_selector.currentIndexChanged.connect(
            self.update_color_preview)

        self.color_preview = QPushButton(self)
        self.color_preview.clicked.connect(self.open_color_picker)

        self.layout.addWidget(QLabel(translator.get("select_element_to_edit")))
        self.layout.addWidget(self.element_selector)
        self.layout.addWidget(self.color_preview)

        button_box = QDialogButtonBox()
        reset_button = button_box.addButton(translator.get(
            "reset_theme"), QDialogButtonBox.ButtonRole.ResetRole)
        save_button = button_box.addButton(translator.get(
            "save_theme"), QDialogButtonBox.ButtonRole.AcceptRole)
        close_button = button_box.addButton(translator.get(
            "close"), QDialogButtonBox.ButtonRole.RejectRole)

        reset_button.clicked.connect(self.reset_to_default)
        save_button.clicked.connect(self.accept)
        close_button.clicked.connect(self.reject)

        self.layout.addWidget(button_box)
        self.update_color_preview()

    def get_selected_key(self):
        selected_text = self.element_selector.currentText()
        for key, value in self.theme_map.items():
            if value == selected_text:
                return key
        return None

    def update_color_preview(self):
        key = self.get_selected_key()
        if key:
            color_val = self.theme_data.get(key, "#ffffff")
            self.color_preview.setStyleSheet(f"background-color: {color_val};")
            self.color_preview.setText(color_val)

    def open_color_picker(self):
        key = self.get_selected_key()
        if not key:
            return

        current_color_str = self.theme_data.get(key, "#ffffff")
        initial_color = QColor(current_color_str)

        dialog = QColorDialog(self)
        dialog.setCurrentColor(initial_color)
        dialog.setWindowTitle(translator.get(
            "edit_color_title", element=self.element_selector.currentText()))

        if dialog.exec():
            new_color = dialog.currentColor()
            if new_color.isValid():
                # Preserve alpha for rgba values
                if 'rgba' in current_color_str:
                    alpha = float(current_color_str.split(',')
                                  [-1].strip()[:-1])
                    self.theme_data[key] = f"rgba({new_color.red()}, {new_color.green()}, {new_color.blue()}, {alpha})"
                else:
                    self.theme_data[key] = new_color.name()

                self.update_color_preview()
                # Live preview on main window
                self.parent().theme_data = self.theme_data
                self.parent().apply_theme()

    def reset_to_default(self):
        self.parent().load_initial_theme(use_last_saved=False)  # Reload default
        self.theme_data = self.parent().theme_data.copy()
        self.update_color_preview()
        self.parent().apply_theme()

    def reject(self):
        # Restore original theme on cancel
        self.parent().theme_data = self.original_theme
        self.parent().apply_theme()
        super().reject()

    def get_theme_data(self):
        return self.theme_data

# ... (rest of the file)


class DDoSAttackDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DDoS Attack Configuration")
        self.setMinimumWidth(500)
        self.selected_method = None
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.target_input = QLineEdit()
        self.threads_input = QLineEdit("100")
        self.duration_input = QLineEdit("60")
        self.port_input = QLineEdit()
        form_layout.addRow("Target (IP/URL):", self.target_input)
        form_layout.addRow("Threads:", self.threads_input)
        form_layout.addRow("Duration (s):", self.duration_input)
        form_layout.addRow("Port (for L4):", self.port_input)
        main_layout.addLayout(form_layout)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.grid_layout = QGridLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        self.l4_methods = list(layer4.L4_CLASSES.keys())
        self.l7_methods = list(layer7.L7_CLASSES.keys())
        self.populate_buttons(self.l4_methods, "Layer 4 Methods", 0)
        self.populate_buttons(self.l7_methods, "Layer 7 Methods",
                              (len(self.l4_methods) + 3) // 4 + 1)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def populate_buttons(self, methods, title, start_row):
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.grid_layout.addWidget(title_label, start_row, 0, 1, 4)
        row, col = start_row + 1, 0
        for method in methods:
            button = QPushButton(method)
            button.clicked.connect(lambda ch, m=method: self.set_method(m))
            self.grid_layout.addWidget(button, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

    def set_method(self, method):
        self.selected_method = method
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                widget.setStyleSheet(
                    "background-color: rgba(0, 255, 0, 0.3)" if widget.text() == method else "")

    def get_values(self):
        if not self.selected_method:
            return None
        return {"method": self.selected_method, "target": self.target_input.text(), "threads": int(self.threads_input.text() or "100"), "duration": int(self.duration_input.text() or "60"), "port": int(self.port_input.text()) if self.port_input.text() and self.selected_method in self.l4_methods else None}


class TelegramSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Telegram Search")
        self.layout = QVBoxLayout(self)
        self.result = None
        self.search_map = {'Search by Username': 'TelegramUsername', 'Search by Channel': 'TelegramChannel',
                           'Search by Chat': 'TelegramChat', 'Parse Channel': 'TelegramCParser'}
        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("Enter query (e.g., @username)")
        self.layout.addWidget(self.input_text)
        button_layout = QHBoxLayout()
        for display_text, method_name in self.search_map.items():
            button = QPushButton(display_text)
            button.clicked.connect(
                lambda ch, m=method_name, dt=display_text: self.set_result(m, dt))
            button_layout.addWidget(button)
        self.layout.addLayout(button_layout)

    def set_result(self, method_name, display_text):
        query = self.input_text.text()
        if query:
            self.result = {"method": method_name,
                           "query": query, "prompt": display_text}
            self.accept()

    def get_values(self): return self.result


class HashToolsDialog(QDialog):
    def __init__(self, parent=None, tool_name=""):
        super().__init__(parent)
        self.setWindowTitle(f"{tool_name} Configuration")
        self.setMinimumWidth(500)
        self.layout = QVBoxLayout(self)
        self.result = None
        self.tool_name = tool_name

        # Instructions
        instructions = QLabel()
        instructions.setWordWrap(True)
        if tool_name == "Text Hasher":
            instructions.setText(
                "This tool hashes text using various cryptographic algorithms.\n\nAvailable algorithms: MD5, SHA1, SHA256, SHA512, etc.\nNote: MD5 and SHA1 are insecure for cryptography.\nUse SHA256 or stronger for security.")
        elif tool_name == "Hash Identifier":
            instructions.setText(
                "This tool identifies possible types of a given hash string.\n\nEnter a hash (e.g., a long string of letters/numbers).\nIt provides possible matches, not definitive identification.")
        elif tool_name == "Dictionary Cracker":
            instructions.setText("This tool cracks a hash using a wordlist (dictionary attack).\n\nPure Python implementation - may be slow for large wordlists.\nFor better performance, use specialized tools like Hashcat.\n\nSupported algorithms: md5, sha1, sha256, etc.")
        elif tool_name == "Rainbow Table Gen":
            instructions.setText("This tool generates a rainbow table for password cracking.\n\nA rainbow table precomputes hash chains.\nWARNING: Very slow and resource-intensive!\n\nParameters:\n- Charset: Characters to use (e.g., 'abc123')\n- Chain length: Hash/reduce operations per chain (higher = better coverage but slower)\n- Chains: Number of starting points (higher = better coverage but larger file)\n- Length: Max password length")
        self.layout.addWidget(instructions)

        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)

        if tool_name == "Text Hasher":
            self.text_input = QTextEdit()
            self.text_input.setPlaceholderText(
                "Enter the text to hash (any string)")
            self.form_layout.addRow("Text:", self.text_input)
            self.algorithm_combo = QComboBox()
            self.algorithm_combo.addItems(sorted(hashlib.algorithms_available))
            self.algorithm_combo.setCurrentText("sha256")
            self.form_layout.addRow("Algorithm:", self.algorithm_combo)
        elif tool_name == "Hash Identifier":
            self.hash_input = QLineEdit()
            self.hash_input.setPlaceholderText(
                "Enter hash string (e.g., e99a18c428cb38d5f260853678922e03)")
            self.form_layout.addRow("Hash:", self.hash_input)
        elif tool_name == "Dictionary Cracker":
            self.hash_input = QLineEdit()
            self.hash_input.setPlaceholderText(
                "Enter hash to crack (lowercase hex)")
            self.form_layout.addRow("Hash:", self.hash_input)
            self.algorithm_combo = QComboBox()
            self.algorithm_combo.addItems(sorted(hashlib.algorithms_available))
            self.algorithm_combo.setCurrentText("md5")
            self.form_layout.addRow("Algorithm:", self.algorithm_combo)
            self.wordlist_input = QLineEdit()
            self.wordlist_input.setPlaceholderText(
                "Path to wordlist file (e.g., C:\\wordlists\\rockyou.txt)")
            browse_button = QPushButton("Browse")
            browse_button.clicked.connect(self.browse_wordlist)
            wordlist_layout = QHBoxLayout()
            wordlist_layout.addWidget(self.wordlist_input)
            wordlist_layout.addWidget(browse_button)
            self.form_layout.addRow("Wordlist:", wordlist_layout)
        elif tool_name == "Rainbow Table Gen":
            self.charset_input = QLineEdit()
            self.charset_input.setText("abcdefghijklmnopqrstuvwxyz0123456789")
            self.form_layout.addRow("Charset:", self.charset_input)
            self.algorithm_combo = QComboBox()
            self.algorithm_combo.addItems(sorted(hashlib.algorithms_available))
            self.algorithm_combo.setCurrentText("md5")
            self.form_layout.addRow("Algorithm:", self.algorithm_combo)
            self.chain_length_input = QLineEdit("1000")
            self.form_layout.addRow("Chain Length:", self.chain_length_input)
            self.num_chains_input = QLineEdit("10000")
            self.form_layout.addRow("Number of Chains:", self.num_chains_input)
            self.password_len_input = QLineEdit("6")
            self.form_layout.addRow(
                "Password Length:", self.password_len_input)
            self.output_file_input = QLineEdit("rainbow_table.csv")
            browse_button = QPushButton("Browse")
            browse_button.clicked.connect(self.browse_output)
            output_layout = QHBoxLayout()
            output_layout.addWidget(self.output_file_input)
            output_layout.addWidget(browse_button)
            self.form_layout.addRow("Output File:", output_layout)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def browse_wordlist(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Wordlist", "", "Text Files (*.txt);;All Files (*)")
        if filepath:
            self.wordlist_input.setText(filepath)

    def browse_output(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Rainbow Table", "", "CSV Files (*.csv);;All Files (*)")
        if filepath:
            self.output_file_input.setText(filepath)

    def get_values(self):
        if self.tool_name == "Text Hasher":
            text = self.text_input.toPlainText().strip()
            algorithm = self.algorithm_combo.currentText()
            if not text:
                return None
            return {"text": text, "algorithm": algorithm}
        elif self.tool_name == "Hash Identifier":
            hash_str = self.hash_input.text().strip()
            if not hash_str:
                return None
            return {"hash": hash_str}
        elif self.tool_name == "Dictionary Cracker":
            hash_str = self.hash_input.text().strip()
            algorithm = self.algorithm_combo.currentText()
            wordlist = self.wordlist_input.text().strip()
            if not all([hash_str, algorithm, wordlist]):
                return None
            return {"hash": hash_str, "algorithm": algorithm, "wordlist": wordlist}
        elif self.tool_name == "Rainbow Table Gen":
            charset = self.charset_input.text().strip()
            algorithm = self.algorithm_combo.currentText()
            try:
                chain_length = int(self.chain_length_input.text())
                num_chains = int(self.num_chains_input.text())
                password_len = int(self.password_len_input.text())
            except ValueError:
                return None
            output_file = self.output_file_input.text().strip()
            if not all([charset, algorithm, output_file]):
                return None
            return {"charset": charset, "algorithm": algorithm, "chain_length": chain_length, "num_chains": num_chains, "password_len": password_len, "output_file": output_file}
        return None


class UserAgreementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Laitoxx Project - User Agreement")
        self.setMinimumSize(700, 600)
        self.setModal(True)
        self.agreed = False

        self.layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("User Agreement for Laitoxx Project")
        title_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        self.layout.addWidget(title_label)

        # Agreement text area
        self.agreement_text = QTextEdit()
        self.agreement_text.setReadOnly(True)

        # Load agreement text
        try:
            with open("User Agreement.txt", "r", encoding="utf-8") as f:
                agreement_content = f.read()
            self.agreement_text.setText(agreement_content)
        except Exception as e:
            self.agreement_text.setText(f"Error loading agreement: {e}")

        self.layout.addWidget(self.agreement_text)

        # Agreement checkbox
        self.agreement_checkbox = QCheckBox(
            "I have read and agree to comply with the User Agreement")
        self.agreement_checkbox.setStyleSheet(
            "font-weight: bold; margin-top: 10px;")
        self.layout.addWidget(self.agreement_checkbox)

        # Buttons
        self.button_box = QDialogButtonBox()
        self.agree_button = self.button_box.addButton(
            "I Agree", QDialogButtonBox.ButtonRole.AcceptRole)
        self.disagree_button = self.button_box.addButton(
            "I Disagree", QDialogButtonBox.ButtonRole.RejectRole)

        self.agree_button.clicked.connect(self.accept_agreement)
        self.disagree_button.clicked.connect(self.reject_agreement)

        # Initially disable agree button
        self.agree_button.setEnabled(False)

        # Connect checkbox to enable/disable agree button
        self.agreement_checkbox.stateChanged.connect(self.toggle_agree_button)

        self.layout.addWidget(self.button_box)

    def toggle_agree_button(self):
        self.agree_button.setEnabled(self.agreement_checkbox.isChecked())

    def accept_agreement(self):
        if self.agreement_checkbox.isChecked():
            self.agreed = True
            save_user_agreement()  # Save agreement status
            self.accept()
        else:
            QMessageBox.warning(self, "Agreement Required",
                                "Please check the agreement checkbox to continue.")

    def reject_agreement(self):
        reply = QMessageBox.question(self, "Confirm Exit",
                                     "Are you sure you want to exit? You must agree to the User Agreement to use this application.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.agreed = False
            self.reject()


class Worker(QObject):
    finished = pyqtSignal()
    update = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, func, input_data=None, is_plugin=False, tool_info=None):
        super().__init__()
        self.func, self.input_data, self.is_plugin, self.tool_info = func, input_data, is_plugin, tool_info

    def run(self):
        if self.is_plugin:
            self.run_plugin()
        else:
            self.run_tool()

    def run_tool(self):
        output_stream = io.StringIO()
        if isinstance(self.input_data, dict):
            try:
                with contextlib.redirect_stdout(output_stream):
                    self.func(self.input_data)
                self.update.emit(remove_ansi_codes(output_stream.getvalue()))
            except Exception as e:
                logging.error(
                    f"Error in worker thread for {self.func.__name__}: {e}", exc_info=True)
                self.error.emit(f"An error occurred: {e}")
            finally:
                self.finished.emit()
        else:
            original_input = builtins.input
            builtins.input = lambda prompt="": self.input_data or ""
            try:
                with contextlib.redirect_stdout(output_stream):
                    self.func()
                self.update.emit(remove_ansi_codes(output_stream.getvalue()))
            except Exception as e:
                logging.error(
                    f"Error in worker thread for {self.func.__name__}: {e}", exc_info=True)
                self.error.emit(f"An error occurred: {e}")
            finally:
                builtins.input = original_input
                self.finished.emit()

    def run_plugin(self):
        plugin_data = self.func
        outputs = {}
        try:
            # --- OS Check ---
            system = platform.system().lower()
            supported_os_list = [os_name.lower()
                                 for os_name in plugin_data.get("supported_os", [])]
            if supported_os_list and not any(os_name in system for os_name in supported_os_list):
                self.error.emit(
                    f"Plugin Error: OS Not Supported. Supports {supported_os_list}, but you are on {system}.")
                return

            # --- Step Preparation ---
            steps = plugin_data.get('steps', [])
            steps_by_id = {
                step.get('id'): step for step in steps if 'id' in step}
            sorted_steps = sorted(steps, key=lambda x: x.get('order', 0))

            step_index = 0
            while step_index < len(sorted_steps):
                step = sorted_steps[step_index]
                step_id = step.get('id', f'step_{step_index+1}')
                description = step.get('description', 'Unnamed Step')
                self.update.emit(
                    f"--- Running Step {step_index + 1}: {description} ---")

                step_successful = False
                step_output = ""

                # --- Handle Delays ---
                if step.get('type') == 'delay':
                    duration = step.get('duration', 1)
                    self.update.emit(f"Delaying for {duration} second(s)...")
                    time.sleep(duration)
                    step_output = f"Delayed for {duration}s"
                    step_successful = True
                else:
                    # --- Determine Input ---
                    current_input = ""
                    input_source = step.get('input_source', 'none')

                    if input_source == 'user':
                        current_input = self.input_data or ""
                    elif input_source.startswith('previous_step:'):
                        source_step_id = input_source.split(':', 1)[1]
                        previous_output = outputs.get(source_step_id, "")

                        all_matches = []
                        regex_filters = step.get('input_filter_regexes', [])
                        if not regex_filters and 'input_filter_regex' in step:
                            regex_filters = [step['input_filter_regex']]

                        if regex_filters:
                            for regex_filter in regex_filters:
                                if not regex_filter:
                                    continue
                                try:
                                    matches = re.findall(
                                        regex_filter, previous_output)
                                    all_matches.extend(matches)
                                    self.update.emit(
                                        f"Applied REGEX '{regex_filter}'. Found {len(matches)} match(es).")
                                except re.error as e:
                                    self.error.emit(
                                        f"Error in REGEX pattern '{regex_filter}': {e}")
                                    break
                            else:  # only if loop completed without break
                                current_input = "\n".join(all_matches)
                        else:
                            current_input = previous_output

                    # --- Execute Action ---
                    action_type = step.get('action_type', 'command')
                    action_value = step.get('action_value', '')

                    if action_type in ['command', 'batch_script', 'shell_script']:
                        script_path = os.path.join(plugin_data.get(
                            'plugin_path', '.'), action_value)
                        if action_type == 'command':
                            command = action_value.replace(
                                '{input}', current_input)
                        else:
                            # For scripts, action_value is the script filename
                            if not os.path.isfile(script_path):
                                self.error.emit(
                                    f"Error: {action_type.replace('_', ' ').title()} '{action_value}' not found in plugin directory.")
                                break
                            command = script_path.replace(
                                '{input}', current_input)

                        sanitized_command = command
                        if step.get('requires_api_key'):
                            api_key = step.get('api_key', '')
                            command = command.replace('{AKEY}', api_key)
                            sanitized_command = sanitized_command.replace(
                                '{AKEY}', '********')

                        self.update.emit(
                            f"Executing {action_type.replace('_', ' ')}: {sanitized_command}")

                        # Determine shell based on action_type
                        use_shell = True
                        if action_type == 'batch_script':
                            # On Windows, use cmd /c for .bat/.cmd files
                            if platform.system() == 'Windows':
                                command = f'cmd /c "{command}"'
                        elif action_type == 'shell_script':
                            # On Unix-like systems, use sh/bash
                            if platform.system() != 'Windows':
                                command = f'sh "{command}"'

                        result = subprocess.run(
                            command, shell=use_shell, capture_output=True, text=True, encoding='utf-8', errors='ignore')

                        stdout = result.stdout.strip()
                        stderr = result.stderr.strip()
                        step_output = stdout

                        if stdout:
                            self.update.emit(f"STDOUT:\n{stdout}")
                        if result.returncode == 0:
                            step_successful = True
                        else:
                            if stderr:
                                self.update.emit(f"STDERR:\n{stderr}")
                            self.error.emit(
                                f"Error: Step failed with exit code {result.returncode}.")

                    elif action_type == 'python_script':
                        script_path = os.path.join(plugin_data.get(
                            'plugin_path', '.'), action_value)
                        if not os.path.isfile(script_path):
                            self.error.emit(
                                f"Error: Python script '{action_value}' not found in plugin directory.")
                        else:
                            self.update.emit(
                                f"Executing Python script: {action_value}")
                            command = [sys.executable, script_path]

                            # Pass input via stdin
                            result = subprocess.run(
                                command, input=current_input, capture_output=True, text=True, encoding='utf-8', errors='ignore')

                            stdout = result.stdout.strip()
                            stderr = result.stderr.strip()
                            step_output = stdout

                            if stdout:
                                self.update.emit(f"STDOUT:\n{stdout}")
                            if result.returncode == 0:
                                step_successful = True
                            else:
                                if stderr:
                                    self.update.emit(f"STDERR:\n{stderr}")
                                self.error.emit(
                                    f"Error: Script failed with exit code {result.returncode}.")

                    elif action_type == 'function':
                        if self.tool_info and action_value in self.tool_info:
                            tool = self.tool_info[action_value]
                            tool_func = tool.get('func')

                            self.update.emit(
                                f"Executing function: {action_value} with input: '{current_input[:50]}...'")

                            original_input = builtins.input
                            builtins.input = lambda prompt="": current_input or ""
                            output_stream = io.StringIO()
                            try:
                                with contextlib.redirect_stdout(output_stream):
                                    tool_func()
                                step_output = remove_ansi_codes(
                                    output_stream.getvalue().strip())
                                self.update.emit(f"Output:\n{step_output}")
                                step_successful = True
                            except Exception as e:
                                self.error.emit(
                                    f"Error executing function '{action_value}': {e}")
                                logging.error(
                                    f"Error in plugin function {action_value}: {e}", exc_info=True)
                            finally:
                                builtins.input = original_input
                        else:
                            self.error.emit(
                                f"Error: Built-in function '{action_value}' not found.")

                outputs[step_id] = step_output

                # --- Handle Conditional Jumps ---
                next_step_id = None
                if step_successful:
                    if 'on_success' in step:
                        next_step_id = step['on_success']
                        self.update.emit(
                            f"Step successful. Jumping to step '{next_step_id}'.")
                else:  # Step failed
                    if 'on_failure' in step:
                        next_step_id = step['on_failure']
                        self.update.emit(
                            f"Step failed. Jumping to step '{next_step_id}'.")
                    else:
                        # If a step fails and has no on_failure, stop execution.
                        self.error.emit(
                            f"Execution halted due to failed step: {description}")
                        return

                if next_step_id:
                    if next_step_id in steps_by_id:
                        target_step = steps_by_id[next_step_id]
                        try:
                            # Find the index of the next step to jump to
                            step_index = sorted_steps.index(target_step)
                        except ValueError:
                            self.error.emit(
                                f"FATAL: Could not find jump target step '{next_step_id}' in the ordered list. This should not happen.")
                            return
                    else:
                        self.error.emit(
                            f"Error: Jump target step ID '{next_step_id}' not found.")
                        return
                else:
                    step_index += 1

        except Exception as e:
            logging.error(
                f"Error executing plugin {plugin_data.get('name')}: {e}", exc_info=True)
            self.error.emit(
                f"A critical error occurred in the plugin executor: {e}")
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logging.info("MainWindow.__init__ started.")
        self.load_initial_theme()
        self.main_container = QWidget()
        self.setCentralWidget(self.main_container)
        self.background_container = QStackedWidget(self.main_container)
        self.gif_label, self.video_frame_label = QLabel(), QLabel()
        self.gif_label.setScaledContents(True)
        self.video_frame_label.setScaledContents(True)
        self.video_frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.background_container.addWidget(self.gif_label)
        self.background_container.addWidget(self.video_frame_label)
        self.player, self.video_sink = QMediaPlayer(), QVideoSink()
        self.player.setVideoSink(self.video_sink)
        self.video_sink.videoFrameChanged.connect(self.update_video_frame)
        self.player.setLoops(-1)
        self.blur_effect = QGraphicsBlurEffect(blurRadius=10)
        self.background_container.setGraphicsEffect(self.blur_effect)
        self.ui_container = QWidget(self.main_container)
        self.ui_container.setStyleSheet("background:transparent;")
        self.sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        self.sidebar_widget.setMaximumWidth(200)
        self.btn_change_bg = GlassButton("")
        self.btn_load_theme = GlassButton("")
        self.btn_create_theme = GlassButton("")
        self.btn_plugin_builder = GlassButton("")
        self.btn_lang_switch = GlassButton("RU/EN")
        self.btn_hide_ui = GlassButton("")
        self.btn_exit = GlassButton("")
        sidebar_layout.addWidget(self.btn_change_bg)
        sidebar_layout.addWidget(self.btn_load_theme)
        sidebar_layout.addWidget(self.btn_create_theme)
        sidebar_layout.addWidget(self.btn_plugin_builder)
        sidebar_layout.addWidget(self.btn_lang_switch)
        sidebar_layout.addWidget(self.btn_hide_ui)
        sidebar_layout.addSpacerItem(QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        sidebar_layout.addWidget(self.btn_exit)
        self.btn_change_bg.clicked.connect(self.change_background)
        self.btn_load_theme.clicked.connect(self.load_theme_from_file)
        self.btn_create_theme.clicked.connect(self.create_new_theme)
        self.btn_plugin_builder.clicked.connect(self.open_plugin_builder)
        self.btn_lang_switch.clicked.connect(self.switch_language)
        self.btn_hide_ui.clicked.connect(self.toggle_ui_visibility)
        self.btn_exit.clicked.connect(self.close)
        main_content_widget = QWidget()
        main_content_layout = QVBoxLayout(main_content_widget)

        # --- Search Bar ---
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(translator.get("search"))
        self.search_bar.textChanged.connect(self.filter_tools)
        main_content_layout.addWidget(self.search_bar)

        self.stacked_widget = QStackedWidget()
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        main_content_layout.addWidget(self.stacked_widget)
        main_content_layout.addWidget(self.output_area)
        # Give more space to the tool area
        main_content_layout.setStretch(1, 2)
        main_content_layout.setStretch(2, 1)
        self.active_tools_widget = QWidget()
        self.active_tools_widget.setMaximumWidth(200)
        active_layout = QVBoxLayout(self.active_tools_widget)
        active_layout.addWidget(QLabel("Active Tools"))
        active_layout.addSpacerItem(QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        # tool_name: {'thread': thread, 'label': label, 'stop_button': button}
        self.running_tools = {}
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.sidebar_widget)
        self.splitter.addWidget(main_content_widget)
        self.splitter.addWidget(self.active_tools_widget)
        self.splitter.setSizes([150, 1050, 150])
        self.splitter.setStyleSheet(
            "QSplitter::handle { background-color: transparent; }")
        ui_layout = QHBoxLayout(self.ui_container)
        ui_layout.addWidget(self.splitter)
        ui_layout.setContentsMargins(0, 0, 0, 0)
        self.tool_widgets = {}  # To store references to tool widgets for filtering
        self.define_tools()
        self.load_plugins()
        self.retranslate_ui()
        self.load_and_set_initial_background()
        logging.info("MainWindow.__init__ finished.")

    def switch_language(self):
        new_lang = 'ru' if translator.lang == 'en' else 'en'
        translator.set_language(new_lang)
        self.retranslate_ui()

    def retranslate_ui(self):
        self.setWindowTitle(translator.get("app_title"))
        self.btn_change_bg.setText(translator.get("change_background"))
        self.btn_load_theme.setText(translator.get("change_theme"))
        self.btn_create_theme.setText(translator.get("create_color_theme"))
        self.btn_plugin_builder.setText(translator.get("plugin_builder"))
        self.btn_hide_ui.setText(translator.get("hide_ui"))
        self.btn_exit.setText(translator.get("exit"))

        # Find the plugin builder if it exists and re-translate it
        if hasattr(self, 'plugin_builder_window') and self.plugin_builder_window:
            self.plugin_builder_window.retranslate_ui()

        self.reload_plugins_and_ui()

    def open_plugin_builder(self):
        # Store a reference to the builder window
        self.plugin_builder_window = PluginBuilderWindow(
            self, translator=translator)
        if self.plugin_builder_window.exec():
            self.reload_plugins_and_ui()
        # Clear the reference after it's closed
        self.plugin_builder_window = None

    def reload_plugins_and_ui(self):
        self.load_plugins()
        # Clear the stacked widget
        for i in reversed(range(self.stacked_widget.count())):
            widget = self.stacked_widget.widget(i)
            self.stacked_widget.removeWidget(widget)
            if widget:
                widget.deleteLater()
        self.create_categorized_menu()
        self.apply_theme()

    def update_video_frame(self, frame: QVideoFrame):
        if frame.isValid():
            self.video_frame_label.setPixmap(
                QPixmap.fromImage(frame.toImage()))

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.background_container.setGeometry(self.rect())
        self.ui_container.setGeometry(self.rect())
        self.ui_container.raise_()

    def define_tools(self):
        self.tool_info = {
            "Check Phone Number": {"func": search_by_number, "input_type": "text", "prompt": "Enter phone number:", "desc": "Get information about a phone number.", "threaded": True},
            "Check IP": {"func": get_ip, "input_type": "text", "prompt": "Enter IP address:", "desc": "Get geolocation data for an IP address.", "threaded": True},
            "Validate Email": {"func": check_email_address, "input_type": "text", "prompt": "Enter email address:", "desc": "Check if an email address is valid and exists.", "threaded": True},
            "Data Search": {"func": data_search_tool, "input_type": "data_search", "prompt": "Choose search type and value.", "desc": "Multi-source search by phone, email, or Telegram username.", "threaded": True},
            "Info Website": {"func": get_website_info, "input_type": "text", "prompt": "Enter website URL:", "desc": "Gather information about a website (Whois, etc.).", "threaded": True},
            "Gmail Osint": {"func": gmail_osint, "input_type": "text", "prompt": "Enter Gmail address:", "desc": "Find information associated with a Gmail account.", "threaded": True},
            "Database search": {"func": search_database, "input_type": "text", "prompt": "Enter search query (e.g., email, name):", "desc": "Search for leaks in local databases.", "threaded": True},
            "Check MAC-address": {"func": search_mac_address, "input_type": "text", "prompt": "Enter MAC address:", "desc": "Lookup the vendor of a MAC address.", "threaded": True},
            "Subdomain finder": {"func": find_subdomains, "input_type": "text", "prompt": "Enter domain (e.g., example.com):", "desc": "Find subdomains for a given domain.", "threaded": True},
            "Google Osint": {"func": google_osint, "input_type": "google_osint", "desc": "Build advanced Google dorks with multiple operators and search engines.", "threaded": False},
            "Search Nick": {"func": check_username, "input_type": "text", "prompt": "Enter username:", "desc": "Check for a username's presence on various platforms.", "threaded": True},
            "Web-crawler": {"func": web_crawler, "input_type": "text", "prompt": "Enter starting URL:", "desc": "Crawl a website to discover links and pages.", "threaded": True},
            "Port Scanner": {"func": port_scanner_tool, "input_type": "text", "prompt": "Enter target IP or domain:", "desc": "Scan a target for open ports.", "threaded": True},
            "Check site": {"func": check_site, "input_type": "text", "prompt": "Enter website URL:", "desc": "Check the status and headers of a website.", "threaded": True},
            "Check url": {"func": check_url, "input_type": "text", "prompt": "Enter URL to check:", "desc": "Analyze a URL for safety and redirects.", "threaded": True},
            "Xss scan": {"func": xss_scan, "input_type": "text", "prompt": "Enter URL to scan for XSS:", "desc": "Scan a URL for Cross-Site Scripting vulnerabilities.", "threaded": True},
            "Find admin panel": {"func": find_admin_panel, "input_type": "text", "prompt": "Enter website URL:", "desc": "Try to find the admin login page of a website.", "threaded": True},
            "Sql scan": {"func": sql_injection_scanner_tool, "input_type": "text", "prompt": "Enter URL with parameters to scan:", "desc": "Scan a URL for SQL Injection vulnerabilities.", "threaded": True},
            "Ip logger": {"func": logger_ip, "input_type": None, "desc": "Create a link to log IP addresses of visitors.", "threaded": True},
            "Temp Mail": {"func": temp_mail, "input_type": "text", "prompt": "Enter username for email [random]:", "desc": "Temporarily Unavailable", "threaded": True, "disabled": True},
            "Get proxy": {"func": get_proxy_list, "input_type": None, "desc": "Fetch a list of free proxy servers.", "threaded": True},
            "Obfuscate python": {"func": obfuscate_tool, "input_type": "text", "prompt": "Enter path to Python file to obfuscate:", "desc": "Obfuscate a Python script to make it harder to read.", "threaded": True},
            "Phish Bot(lamer)": {"func": phishing, "input_type": "text", "prompt": "Enter Bot token:", "desc": "Start a simple phishing bot (for educational purposes).", "threaded": True},
            "Strange Text": {"func": transform_text, "input_type": "text", "prompt": "Enter text to transform:", "desc": "Apply various transformations to text (e.g., Zalgo).", "threaded": False},
            "Password Generator": {"func": password_generator_tool, "input_type": "text", "prompt": "Enter password length and complexity (e.g., 12 medium):", "desc": "Generate a strong, random password.", "threaded": False},
            "DDoS Attack": {"func": run_ddos_attack, "input_type": "ddos", "desc": "Launch a DDoS attack (for educational purposes only).", "threaded": True},
            "Telegram (paketlib)": {"func": telegram_search, "input_type": "telegram", "desc": "Search for users, channels, and chats on Telegram.", "threaded": True},

            # Hashing Tools
            "Text Hasher": {"func": text_hasher_tool, "input_type": "hash", "prompt": "This tool will guide you through hashing text.", "desc": "Hash text using various algorithms (MD5, SHA256, etc.).", "threaded": True},
            "Hash Identifier": {"func": hash_identifier_tool, "input_type": "hash", "prompt": "Enter hash to identify:", "desc": "Identify the type of a given hash.", "threaded": True},
            "Dictionary Cracker": {"func": dictionary_cracker_tool, "input_type": "hash", "prompt": "This tool will guide you through using the dictionary cracker.", "desc": "Crack a hash against a wordlist (pure Python).", "threaded": True},
            "Rainbow Table Gen": {"func": rainbow_table_tool, "input_type": "hash", "prompt": "This tool will guide you through generating a rainbow table.", "desc": "Generate a rainbow table for a given charset and hash.", "threaded": True},

            # Nmap Scanner
            "Nmap": {"func": nmap_scanner_tool, "input_type": None, "desc": "Perform an Nmap scan with progress updates.", "threaded": True},
        }

    def load_plugins(self):
        self.plugins = []
        if not os.path.exists(PLUGIN_DIR):
            os.makedirs(PLUGIN_DIR)
        for plugin_name in os.listdir(PLUGIN_DIR):
            plugin_dir = os.path.join(PLUGIN_DIR, plugin_name)
            if os.path.isdir(plugin_dir):
                filepath = os.path.join(plugin_dir, "plugin.json")
                if os.path.exists(filepath):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            plugin_data = json.load(f)
                        if 'name' in plugin_data and 'steps' in plugin_data:
                            plugin_data['plugin_path'] = plugin_dir
                            self.plugins.append(plugin_data)
                    except Exception as e:
                        logging.error(
                            f"Failed to load plugin from {plugin_name}: {e}")

    def load_initial_theme(self):
        last_theme_path = load_config(LAST_THEME_CONFIG_FILE)
        theme = load_theme(last_theme_path) if last_theme_path else None
        default_theme = {
            "button_bg_color": "rgba(255, 0, 0, 0.1)", "button_hover_bg_color": "rgba(255, 0, 0, 0.2)",
            "button_pressed_bg_color": "rgba(255, 0, 0, 0.3)", "button_border_color": "rgba(255, 255, 255, 0.2)",
            "button_text_color": "white", "text_area_bg_color": "rgba(0, 0, 0, 0.5)",
            "text_area_border_color": "rgba(255, 255, 255, 0.2)", "text_area_text_color": "white",
            "sidebar_bg_color": "rgba(0, 0, 0, 0.2)", "title_text_color": "white",
            "scrollbar_handle_color": "rgba(255, 255, 255, 0.4)", "scrollbar_handle_hover_color": "rgba(255, 255, 255, 0.6)",
            "plugin_canvas_bg_color": "#2d3436"
        }
        self.theme_data = default_theme
        if theme:
            self.theme_data.update(theme)

    def apply_theme(self):
        td = self.theme_data
        button_style = f"""QPushButton {{ background-color: {td['button_bg_color']}; border: 1px solid {td['button_border_color']}; border-radius: 10px; color: {td['button_text_color']}; padding: 10px; font-size: 14px; }} QPushButton:hover {{ background-color: {td['button_hover_bg_color']}; }} QPushButton:pressed {{ background-color: {td['button_pressed_bg_color']}; }}"""
        self.setStyleSheet(button_style)
        self.sidebar_widget.setStyleSheet(
            f"background-color: {td['sidebar_bg_color']}; border-radius: 10px;")
        self.active_tools_widget.setStyleSheet(
            f"background-color: {td['sidebar_bg_color']}; border-radius: 10px;")
        scrollbar_style = f"""QScrollBar:vertical {{ border: none; background: transparent; width: 12px; margin: 15px 0 15px 0; border-radius: 6px; }} QScrollBar::handle:vertical {{ background-color: {td['scrollbar_handle_color']}; min-height: 30px; border-radius: 6px; }} QScrollBar::handle:vertical:hover {{ background-color: {td['scrollbar_handle_hover_color']}; }} QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }} QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}"""
        text_area_style = f"""QTextEdit {{ background-color: {td['text_area_bg_color']}; border: 1px solid {td['text_area_border_color']}; border-radius: 10px; color: {td['text_area_text_color']}; font-size: 14px; }}"""
        self.output_area.setStyleSheet(text_area_style + scrollbar_style)
        for title_label in self.findChildren(QLabel):
            if title_label.property("is_title"):
                title_label.setStyleSheet(
                    f"color: {td['title_text_color']}; padding-top: 10px; background: transparent;")
        self.stacked_widget.setStyleSheet("background: transparent;")
        for i in range(self.stacked_widget.count()):
            self.stacked_widget.widget(i).setStyleSheet(
                "background: transparent;")
        # Find the plugin builder canvas if it exists and apply theme
        if hasattr(self, 'plugin_builder_window') and self.plugin_builder_window:
            canvas = self.plugin_builder_window.findChild(
                QWidget, "plugin_canvas")
            if canvas:
                canvas.setStyleSheet(
                    f"background-color: {td.get('plugin_canvas_bg_color', '#2d3436')};")

    def load_theme_from_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, translator.get("change_theme"), "", "JSON Files (*.json)")
        if filepath:
            new_theme = load_theme(filepath)
            if new_theme:
                self.theme_data.update(new_theme)
                self.apply_theme()
                save_config(LAST_THEME_CONFIG_FILE, filepath)
            else:
                self.output_area.setText(translator.get("load_theme_error"))

    def create_new_theme(self):
        editor = ThemeEditorDialog(self, self.theme_data)
        if editor.exec():
            self.theme_data = editor.get_theme_data()
            filepath, _ = QFileDialog.getSaveFileName(
                self, translator.get("save_theme"), "", "JSON Files (*.json)")
            if filepath:
                save_theme(filepath, self.theme_data)
                save_config(LAST_THEME_CONFIG_FILE, filepath)
                logging.info(translator.get(
                    "theme_saved_success", path=filepath))
            else:
                logging.info(translator.get("theme_save_cancelled"))
        self.apply_theme()  # Apply final or restored theme

    def toggle_ui_visibility(self):
        is_visible = self.ui_container.isVisible()
        self.ui_container.setVisible(not is_visible)
        if is_visible:
            self.unhide_button = QPushButton(translator.get("show_ui"), self)
            self.unhide_button.setStyleSheet(self.styleSheet())
            self.unhide_button.setFixedSize(100, 40)
            self.unhide_button.move(10, 10)
            self.unhide_button.clicked.connect(self.toggle_ui_visibility)
            self.unhide_button.show()
        elif hasattr(self, 'unhide_button'):
            self.unhide_button.hide()

    def set_background(self, path):
        self.player.stop()
        if not path or not os.path.exists(path):
            path = "background0.gif"
        _, extension = os.path.splitext(path.lower())
        if extension == ".gif":
            movie = QMovie(path)
            if movie.isValid():
                self.gif_label.setMovie(movie)
                movie.start()
                self.background_container.setCurrentWidget(self.gif_label)
        elif extension in [".mp4", ".avi"]:
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            self.background_container.setCurrentWidget(self.video_frame_label)
            self.player.play()
        else:
            self.output_area.setText(f"Unsupported file format: {extension}")
            return
        save_config(CONFIG_FILE, path)

    def load_and_set_initial_background(self):
        self.set_background(load_config(CONFIG_FILE) or "background0.gif")

    def change_background(self):
        text, ok = QInputDialog.getText(
            self, 'Change Background', 'Enter local file path or URL:')
        if ok and text:
            if text.startswith(('http://', 'https://')):
                self.download_and_set_background(text)
            elif os.path.exists(text):
                self.set_background(text)
            else:
                self.output_area.setText(f"File not found: {text}")

    def download_and_set_background(self, url):
        try:
            self.output_area.setText(f"Downloading from {url}...")
            QApplication.processEvents()
            response = requests.get(url, stream=True, timeout=15)
            response.raise_for_status()
            filename, extension = os.path.splitext(url.split('/')[-1])
            if not extension:
                content_type = response.headers.get('content-type', '')
                if 'gif' in content_type:
                    extension = '.gif'
                elif 'mp4' in content_type:
                    extension = '.mp4'
            local_filename = "downloaded_background" + (extension or ".tmp")
            with open(local_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            self.set_background(local_filename)
        except requests.exceptions.RequestException as e:
            self.output_area.setText(f"Failed to download: {e}")

    def create_categorized_menu(self):
        self.tool_widgets = {}  # Reset for UI reloads
        menu_widget = QWidget()
        main_layout = QHBoxLayout(menu_widget)

        categories = {
            "information_gathering": ["Check Phone Number", "Check IP", "Validate Email", "Data Search", "Info Website", "Gmail Osint", "Database search", "Check MAC-address", "Subdomain finder", "Google Osint", "Telegram (paketlib)", "Search Nick", "Web-crawler"],
            "web_security": ["Port Scanner", "Nmap", "Check site", "Check url", "Xss scan", "Find admin panel", "Sql scan", "DDoS Attack"],
            "hashing": ["Text Hasher", "Hash Identifier", "Dictionary Cracker", "Rainbow Table Gen"],
            "tools_utilities": ["Strange Text", "Password Generator", "Temp Mail", "Get proxy", "Ip logger", "Obfuscate python", "Phish Bot(lamer)"]
        }
        if self.plugins:
            categories["plugins"] = [p['name'] for p in self.plugins]

        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)

        for category_key, tool_keys in categories.items():
            col_widget = QWidget()
            col_layout = QVBoxLayout(col_widget)

            title_label = QLabel(translator.get(category_key))
            title_label.setFont(title_font)
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_label.setProperty("is_title", True)
            col_layout.addWidget(title_label)

            self.tool_widgets[category_key] = {
                'title': title_label, 'buttons': [], 'widget': col_widget}

            for tool_key in tool_keys:
                button = None
                if category_key == "plugins":
                    plugin_data = next(
                        (p for p in self.plugins if p['name'] == tool_key), None)
                    if plugin_data:
                        button = GlassButton(plugin_data.get("name"))
                        button.setToolTip(plugin_data.get(
                            "description", translator.get("no_description")))
                        button.clicked.connect(
                            lambda checked, p=plugin_data: self.run_plugin_dispatcher(p))
                elif tool_key in self.tool_info:
                    info = self.tool_info[tool_key]
                    button_text = translator.get(tool_key)
                    if info.get("disabled"):
                        button_text = "Temporarily Unavailable"
                    button = GlassButton(button_text)
                    button.setToolTip(info.get("desc", ""))
                    if info.get("disabled"):
                        button.setEnabled(False)
                    button.clicked.connect(
                        lambda checked, t=tool_key: self.run_tool_dispatcher(t))

                if button:
                    col_layout.addWidget(button)
                    self.tool_widgets[category_key]['buttons'].append(button)

            col_layout.addSpacerItem(QSpacerItem(
                20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
            main_layout.addWidget(col_widget)

        self.stacked_widget.addWidget(menu_widget)

    def filter_tools(self, text):
        search_text = text.lower()
        for category_key, data in self.tool_widgets.items():
            any_button_visible = False
            for button in data['buttons']:
                if search_text in button.text().lower():
                    button.show()
                    any_button_visible = True
                else:
                    button.hide()

            # Hide title and the whole column if no buttons are visible
            data['title'].setVisible(any_button_visible)
            data['widget'].setVisible(any_button_visible)

    def set_output_text(self, text):
        self.output_area.setText(text)

    def run_plugin_dispatcher(self, plugin_data):
        input_data = None
        # Check if the first step requires user input
        if plugin_data.get('steps'):
            first_step = sorted(
                plugin_data['steps'], key=lambda x: x.get('order', 0))[0]
            if first_step.get("input_source") == "user":
                dialog = CustomInputDialog(self, title=plugin_data['name'], prompt=first_step.get(
                    'description', "Enter initial input for plugin:"))
                if dialog.exec():
                    input_data = dialog.get_text()
                    if not input_data:
                        self.output_area.setText(translator.get("input_empty"))
                        return
                else:
                    self.output_area.setText(
                        translator.get("operation_cancelled"))
                    return

        self.exec_window = PluginExecutionWindow(plugin_data, self)
        self.thread = QThread()
        # Pass tool_info to the worker
        self.worker = Worker(plugin_data, input_data,
                             is_plugin=True, tool_info=self.tool_info)
        self.worker.moveToThread(self.thread)
        self.worker.update.connect(self.exec_window.append_log)
        self.worker.error.connect(self.exec_window.append_log)
        self.worker.finished.connect(self.exec_window.execution_finished)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        self.add_running_tool(plugin_data['name'], self.thread)
        self.exec_window.exec()

    def run_tool_dispatcher(self, tool_name):
        self.output_area.clear()
        if tool_name not in self.tool_info:
            return self.output_area.setText(f"Error: Tool '{tool_name}' not defined.")
        info = self.tool_info[tool_name]
        tool_func, input_type = info["func"], info["input_type"]
        input_data, ok = None, False
        if input_type is None:
            ok = True
        elif input_type == "text":
            dialog = CustomInputDialog(
                self, title=tool_name, prompt=info.get("prompt", "Enter value:"))
            if dialog.exec():
                input_data = dialog.get_text()
                if input_data:
                    ok = True
        elif input_type == "data_search":
            dialog = DataSearchDialog(self)
            if dialog.exec():
                input_data = dialog.get_values()
                if input_data:
                    ok = True
        elif input_type == "ddos":
            dialog = DDoSAttackDialog(self)
            if dialog.exec():
                input_data = dialog.get_values()
                if input_data:
                    ok = True
        elif input_type == "telegram":
            dialog = TelegramSearchDialog(self)
            if dialog.exec():
                input_data = dialog.get_values()
                if input_data:
                    ok = True
        elif input_type == "hash":
            dialog = HashToolsDialog(self, tool_name)
            if dialog.exec():
                input_data = dialog.get_values()
                if input_data:
                    ok = True
        elif input_type == "google_osint":
            # Import here to avoid circular import
            from script.tools.google_osint import GoogleOsintDialog
            dialog = GoogleOsintDialog(self)
            if dialog.exec():
                ok = True  # Dialog handles the search directly
        if not ok:
            return self.output_area.setText(translator.get("operation_cancelled"))
        if info.get("threaded", False):
            self.thread = QThread()
            self.worker = Worker(tool_func, input_data)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            # Changed from result to update
            self.worker.update.connect(self.set_output_text)
            self.worker.error.connect(self.set_output_text)
            self.thread.start()
            self.add_running_tool(tool_name, self.thread)
            self.output_area.setText(
                f"Running {tool_name} in the background...")
        elif isinstance(input_data, dict):
            self.execute_special_tool(tool_func, input_data)
        else:
            self.execute_tool(tool_func, input_data)

    def execute_tool(self, tool_function, input_data):
        output_stream = io.StringIO()
        original_input = builtins.input
        builtins.input = lambda prompt="": input_data or ""
        try:
            with contextlib.redirect_stdout(output_stream):
                tool_function()
            self.output_area.setText(
                remove_ansi_codes(output_stream.getvalue()))
        except Exception as e:
            self.output_area.setText(f"An error occurred: {e}")
        finally:
            builtins.input = original_input

    def execute_special_tool(self, tool_function, data):
        self.output_area.clear()
        QApplication.processEvents()
        thread = threading.Thread(target=self.run_ddos_thread if tool_function ==
                                  run_ddos_attack else self.run_telegram_thread, args=(data,))
        thread.start()

    def run_ddos_thread(self, data):
        self.output_area.append(
            f"Starting DDoS attack: {data['method']} on {data['target']}\n")
        try:
            run_ddos_attack(data)
            self.output_area.append("\nAttack finished.")
        except Exception as e:
            self.output_area.append(
                f"\nAn error occurred during the attack: {e}")

    def run_telegram_thread(self, data):
        output_stream = io.StringIO()
        try:
            with contextlib.redirect_stdout(output_stream):
                telegram_search(data)
            self.output_area.setText(
                remove_ansi_codes(output_stream.getvalue()))
        except Exception as e:
            self.output_area.setText(
                f"An error occurred during Telegram search: {e}")

    def add_running_tool(self, tool_name, thread):
        if tool_name not in self.running_tools:
            label = QLabel(tool_name)
            stop_button = QPushButton("Stop")
            stop_button.clicked.connect(lambda: self.stop_tool(tool_name))
            active_layout = self.active_tools_widget.layout()
            active_layout.insertWidget(active_layout.count() - 1, label)
            active_layout.insertWidget(active_layout.count() - 1, stop_button)
            self.running_tools[tool_name] = {
                'thread': thread, 'label': label, 'stop_button': stop_button}
            thread.finished.connect(
                lambda: self.remove_running_tool(tool_name))

    def remove_running_tool(self, tool_name):
        if tool_name in self.running_tools:
            active_layout = self.active_tools_widget.layout()
            active_layout.removeWidget(self.running_tools[tool_name]['label'])
            active_layout.removeWidget(
                self.running_tools[tool_name]['stop_button'])
            self.running_tools[tool_name]['label'].deleteLater()
            self.running_tools[tool_name]['stop_button'].deleteLater()
            del self.running_tools[tool_name]

    def stop_tool(self, tool_name):
        if tool_name in self.running_tools:
            self.running_tools[tool_name]['thread'].quit()
            self.remove_running_tool(tool_name)


if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)

        # Set application icon
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "ico.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))

        # Check if user has already agreed to terms
        if check_user_agreement():
            # User has already agreed, show main window directly
            main_win = MainWindow()
            main_win.show()
            sys.exit(app.exec())
        else:
            # Show user agreement dialog first
            agreement_dialog = UserAgreementDialog()
            if agreement_dialog.exec() and agreement_dialog.agreed:
                # User agreed, show main window
                main_win = MainWindow()
                main_win.show()
                sys.exit(app.exec())
            else:
                # User disagreed or closed dialog, exit application
                sys.exit(0)
    except Exception as e:
        logging.critical(
            f"Unhandled exception at top level: {e}", exc_info=True)
        sys.exit(1)
