"""Dialog routing for tool inputs, separated from MainWindow."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QLabel, QTextEdit, QVBoxLayout

from laitoxx.interfaces.gui.dialogs import (
    CidrCalculatorDialog,
    CustomInputDialog,
    HashToolsDialog,
    JwtAnalyzerDialog,
    PasswordGeneratorDialog,
    RegexTesterDialog,
    TextCipherDialog,
    WebSecurityDialog,
)


class MultilineInputDialog(QDialog):
    def __init__(self, parent, title: str, prompt: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(560, 380)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(prompt))
        self.editor = QTextEdit()
        layout.addWidget(self.editor)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_text(self):
        return self.editor.toPlainText().strip()


class ToolInputController:
    OPENED_WINDOW = object()

    def __init__(self, host):
        self.host = host

    @staticmethod
    def _accepted(dialog):
        if dialog.exec():
            value = dialog.get_values()
            if value:
                return value, True
        return None, False

    def _show_modeless(self, window, attribute: str, activity_name: str):
        existing = getattr(self.host, attribute, None)
        if existing and existing.isVisible():
            existing.raise_()
            existing.activateWindow()
            return self.OPENED_WINDOW, True
        window.setWindowModality(Qt.WindowModality.NonModal)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        window.finished.connect(lambda: setattr(self.host, attribute, None))
        setattr(self.host, attribute, window)
        if hasattr(self.host, "_add_open_window"):
            self.host._add_open_window(activity_name, window)
        window.show()
        return self.OPENED_WINDOW, True

    def collect(self, tool_name, info):
        input_type = info.input_type
        if input_type is None:
            return None, True
        dialog_types = {
            "hash": HashToolsDialog,
            "jwt": JwtAnalyzerDialog,
            "web_security": WebSecurityDialog,
            "text_cipher": TextCipherDialog,
            "password_gen": PasswordGeneratorDialog,
            "regex": RegexTesterDialog,
            "cidr": CidrCalculatorDialog,
        }
        if input_type == "text":
            dialog = CustomInputDialog(self.host, title=tool_name, prompt=info.prompt or "Enter value:")
            if dialog.exec() and dialog.get_text():
                return dialog.get_text(), True
            return None, False
        if input_type == "multiline":
            dialog = MultilineInputDialog(self.host, tool_name, info.prompt or "Enter values:")
            if dialog.exec() and dialog.get_text():
                return dialog.get_text(), True
            return None, False
        if input_type == "file_path":
            path, _ = QFileDialog.getOpenFileName(self.host, tool_name, "", "All Files (*)")
            return (path, True) if path else (None, False)
        if input_type == "two_files":
            first, _ = QFileDialog.getOpenFileName(
                self.host, "Select first avatar", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
            )
            if not first:
                return None, False
            second, _ = QFileDialog.getOpenFileName(
                self.host, "Select second avatar", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
            )
            return (f"{first}|{second}", True) if second else (None, False)
        if input_type in dialog_types:
            dialog_type = dialog_types[input_type]
            dialog = dialog_type(self.host, tool_name)
            return self._accepted(dialog)
        return self._open_special(input_type)

    def _open_special(self, input_type):
        if input_type == "masscan":
            from laitoxx.interfaces.gui.masscan_window import MasscanWindow

            return self._show_modeless(
                MasscanWindow(self.host, theme_data=self.host.theme_data),
                "_masscan_window",
                "Masscan Scanner",
            )
        if input_type == "google_osint":
            from laitoxx.features.osint.google_osint import GoogleOsintDialog

            return self._show_modeless(GoogleOsintDialog(self.host), "_google_osint_window", "Google OSINT")
        if input_type == "username_osint_dialog":
            self.host._open_username_osint()
            return self.OPENED_WINDOW, True
        if input_type == "web_crawler":
            from laitoxx.interfaces.gui.web_crawler_window import WebCrawlerWindow

            return self._show_modeless(
                WebCrawlerWindow(self.host, theme_data=self.host.theme_data),
                "_web_crawler_window",
                "Web Crawler",
            )
        elif input_type == "image_search":
            from laitoxx.interfaces.gui.image_search_window import ImageSearchWindow

            return self._show_modeless(ImageSearchWindow(self.host), "_image_search_window", "Image Search")
        elif input_type == "metadata_viewer":
            from laitoxx.features.utilities.metadata_viewer import metadata_viewer_tool

            metadata_viewer_tool(self.host, self.host.theme_data)
            return self.OPENED_WINDOW, True
        elif input_type == "advanced_web_scanner":
            from laitoxx.interfaces.gui.advanced_web_scanner_window import AdvancedWebScannerWindow

            return self._show_modeless(
                AdvancedWebScannerWindow(self.host, theme_data=self.host.theme_data),
                "_advanced_web_scanner_window",
                "Advanced Web Scanner",
            )
        elif input_type == "tongue":
            from laitoxx.interfaces.gui.tongue_window import TongueWindow

            return self._show_modeless(
                TongueWindow(self.host, theme_data=self.host.theme_data),
                "_tongue_window",
                "Tongue",
            )
        elif input_type == "cognipass":
            from laitoxx.interfaces.gui.cognipass_window import CogniPassWindow

            return self._show_modeless(
                CogniPassWindow(self.host, theme_data=self.host.theme_data),
                "_cognipass_window",
                "CogniPass",
            )
        elif input_type.startswith("network_info_"):
            from laitoxx.interfaces.gui.network_info_window import NetworkInfoWindow

            mode = input_type.removeprefix("network_info_")
            return self._show_modeless(
                NetworkInfoWindow(self.host, mode=mode, theme_data=self.host.theme_data),
                "_network_info_window",
                "Network Info",
            )
        elif input_type == "steganography":
            from laitoxx.interfaces.gui.steganography_window import SteganographyWindow

            return self._show_modeless(
                SteganographyWindow(self.host, theme_data=self.host.theme_data),
                "_steganography_window",
                "Steganography",
            )
        return None, False
