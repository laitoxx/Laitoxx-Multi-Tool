import sys
import io
import contextlib
import builtins
import os
import requests
import json
import re
import asyncio
import threading
import logging
import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QStackedWidget, QLabel, QGraphicsBlurEffect,
                             QTextEdit, QGridLayout, QInputDialog, QSplitter,
                             QHBoxLayout, QSpacerItem, QSizePolicy, QColorDialog,
                             QFileDialog, QDialog, QFormLayout, QLineEdit,
                             QDialogButtonBox, QScrollArea)
from PyQt6.QtGui import QMovie, QResizeEvent, QColor, QFont, QPixmap
from PyQt6.QtCore import Qt, QUrl, QObject, pyqtSignal, QThread
from PyQt6.QtMultimedia import QMediaPlayer, QVideoSink, QVideoFrame

# --- Local Imports ---
from plugin_builder import PluginBuilderWindow

# --- Logging Setup ---
LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
log_filename = os.path.join(LOG_DIR, f"gui_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
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
from script.tools.user_search_by_phone import search_by_number
from script.tools.ip_info import get_ip
from script.tools.email_validator import check_email_address
from script.tools.website_info import get_website_info
from script.tools.text_transformer import transform_text
from script.tools.password_generator import password_generator_tool
from script.tools.port_scanner import port_scanner_tool
from script.tools.temp_mail import temp_mail
from script.tools.gmail_osint import gmail_osint
from script.tools.db_searcher import search_database
from script.tools.proxy_fetcher import get_proxy_list
from script.tools.site_checker import check_site
from script.tools.url_checker import check_url
from script.tools.xss_scanner import xss_scan
from script.tools.mac_lookup import search_mac_address
from script.tools.admin_finder import find_admin_panel
from script.tools.sql_scanner import sql_injection_scanner_tool
from script.tools.subdomain_finder import find_subdomains
from script.tools.ip_logger import logger_ip
from script.tools.google_osint import google_osint
from script.tools.telegram_search import telegram_search
from script.tools.user_checker import check_username
from script.tools.obfuscator import obfuscate_tool
from script.tools.web_crawler import web_crawler
from script.tools.phishing_bot import phishing
from ddos_module.main import run_ddos_attack
from ddos_module.attacks import layer4, layer7


CONFIG_FILE = "background_config.txt"
DEFAULT_THEME_FILE = "theme.json"
LAST_THEME_CONFIG_FILE = "last_theme.txt"
PLUGIN_DIR = "plugins"

def remove_ansi_codes(text):
    ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

def save_config(filepath, value):
    with open(filepath, "w") as f:
        f.write(value)

def load_config(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return f.read().strip()
    return None

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

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_text(self):
        return self.input_text.text()

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
        self.populate_buttons(self.l7_methods, "Layer 7 Methods", (len(self.l4_methods) + 3) // 4 + 1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
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
                is_selected = widget.text() == method
                widget.setStyleSheet("background-color: rgba(0, 255, 0, 0.3)" if is_selected else "")

    def get_values(self):
        if not self.selected_method: return None
        return {
            "method": self.selected_method, "target": self.target_input.text(),
            "threads": int(self.threads_input.text() or "100"), "duration": int(self.duration_input.text() or "60"),
            "port": int(self.port_input.text()) if self.port_input.text() and self.selected_method in self.l4_methods else None
        }

class TelegramSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Telegram Search")
        self.layout = QVBoxLayout(self)
        self.result = None

        self.search_map = {'Search by Username': 'TelegramUsername', 'Search by Channel': 'TelegramChannel', 'Search by Chat': 'TelegramChat', 'Parse Channel': 'TelegramCParser'}

        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("Enter query (e.g., @username)")
        self.layout.addWidget(self.input_text)

        button_layout = QHBoxLayout()
        for display_text, method_name in self.search_map.items():
            button = QPushButton(display_text)
            button.clicked.connect(lambda ch, m=method_name, dt=display_text: self.set_result(m, dt))
            button_layout.addWidget(button)
        self.layout.addLayout(button_layout)

    def set_result(self, method_name, display_text):
        query = self.input_text.text()
        if query:
            self.result = {"method": method_name, "query": query, "prompt": display_text}
            self.accept()

    def get_values(self):
        return self.result

# Worker for running tools/plugins in a separate thread
class Worker(QObject):
    finished = pyqtSignal()
    result = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, func, input_data=None, is_plugin=False, tool_info=None):
        super().__init__()
        self.func = func
        self.input_data = input_data
        self.is_plugin = is_plugin
        self.tool_info = tool_info

    def run(self):
        if self.is_plugin:
            self.run_plugin()
        else:
            self.run_tool()

    def run_tool(self):
        original_input = builtins.input
        builtins.input = lambda prompt="": self.input_data or ""
        
        output_stream = io.StringIO()
        try:
            with contextlib.redirect_stdout(output_stream):
                self.func()
            output_text = output_stream.getvalue()
            self.result.emit(remove_ansi_codes(output_text))
        except Exception as e:
            logging.error(f"Error in worker thread for {self.func.__name__}: {e}", exc_info=True)
            self.error.emit(f"An error occurred: {e}")
        finally:
            builtins.input = original_input
            self.finished.emit()

    def run_plugin(self):
        plugin_data = self.func
        context = {}
        output_stream = io.StringIO()
        original_input = builtins.input

        try:
            with contextlib.redirect_stdout(output_stream):
                for step in plugin_data.get('workflow', []):
                    tool_name = step.get('tool')
                    tool_func = self.tool_info.get(tool_name, {}).get('func')
                    if not tool_func:
                        raise ValueError(f"Tool '{tool_name}' not found in plugin.")

                    input_source = step.get('input_source')
                    if input_source == 'user':
                        current_input = self.input_data
                    elif input_source in context:
                        current_input = context[input_source]
                    else:
                        current_input = None
                    
                    builtins.input = lambda prompt="": current_input or ""
                    
                    print(f"--- Running Step: {step.get('id')} ({tool_name}) ---")
                    tool_func()
                    
                    step_output = output_stream.getvalue().split("---")[-1].strip()
                    context[step.get('id')] = step_output

            final_output = output_stream.getvalue()
            self.result.emit(remove_ansi_codes(final_output))

        except Exception as e:
            logging.error(f"Error executing plugin {plugin_data.get('name')}: {e}", exc_info=True)
            self.error.emit(f"Plugin Error: {e}")
        finally:
            builtins.input = original_input
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logging.info("MainWindow.__init__ started.")
        self.setWindowTitle("Laitoxx")
        self.resize(1200, 700)
        self.load_initial_theme()
        self.plugin_builder_window = None

        self.main_container = QWidget()
        self.setCentralWidget(self.main_container)

        self.background_container = QStackedWidget(self.main_container)
        self.gif_label = QLabel()
        self.gif_label.setScaledContents(True)
        
        self.video_frame_label = QLabel()
        self.video_frame_label.setScaledContents(True)
        self.video_frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.background_container.addWidget(self.gif_label)
        self.background_container.addWidget(self.video_frame_label)

        self.player = QMediaPlayer()
        self.video_sink = QVideoSink()
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

        btn_change_bg = GlassButton("Change Background")
        btn_change_bg.clicked.connect(self.change_background)
        sidebar_layout.addWidget(btn_change_bg)
        btn_load_theme = GlassButton("Change Theme")
        btn_load_theme.clicked.connect(self.load_theme_from_file)
        sidebar_layout.addWidget(btn_load_theme)
        btn_create_theme = GlassButton("Create Color Theme")
        btn_create_theme.clicked.connect(self.create_new_theme)
        sidebar_layout.addWidget(btn_create_theme)
        
        btn_plugin_builder = GlassButton("Plugin Builder")
        btn_plugin_builder.clicked.connect(self.open_plugin_builder)
        sidebar_layout.addWidget(btn_plugin_builder);

        btn_hide_ui = GlassButton("Hide UI")
        btn_hide_ui.clicked.connect(self.toggle_ui_visibility)
        sidebar_layout.addWidget(btn_hide_ui)
        sidebar_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        btn_exit = GlassButton("Exit")
        btn_exit.clicked.connect(self.close)
        sidebar_layout.addWidget(btn_exit)

        main_content_widget = QWidget()
        main_content_layout = QVBoxLayout(main_content_widget)
        self.stacked_widget = QStackedWidget()
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        main_content_layout.addWidget(self.stacked_widget)
        main_content_layout.addWidget(self.output_area)
        main_content_layout.setStretch(0, 2)
        main_content_layout.setStretch(1, 1)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.sidebar_widget)
        self.splitter.addWidget(main_content_widget)
        self.splitter.setSizes([150, 1050])
        self.splitter.setStyleSheet("QSplitter::handle { background-color: transparent; }")

        ui_layout = QHBoxLayout(self.ui_container)
        ui_layout.addWidget(self.splitter)
        ui_layout.setContentsMargins(0, 0, 0, 0)

        self.define_tools()
        self.load_plugins()
        self.create_categorized_menu()
        self.apply_theme()
        self.load_and_set_initial_background()
        
        logging.info("MainWindow.__init__ finished.")

    def open_plugin_builder(self):
        if self.plugin_builder_window is None:
            self.plugin_builder_window = PluginBuilderWindow(self.tool_info)
        self.plugin_builder_window.show()

    def update_video_frame(self, frame: QVideoFrame):
        if frame.isValid():
            image = frame.toImage()
            self.video_frame_label.setPixmap(QPixmap.fromImage(image))

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
            "Info Website": {"func": get_website_info, "input_type": "text", "prompt": "Enter website URL:", "desc": "Gather information about a website (Whois, etc.).", "threaded": True},
            "Gmail Osint": {"func": gmail_osint, "input_type": "text", "prompt": "Enter Gmail address:", "desc": "Find information associated with a Gmail account.", "threaded": True},
            "Database search": {"func": search_database, "input_type": "text", "prompt": "Enter search query (e.g., email, name):", "desc": "Search for leaks in local databases.", "threaded": True},
            "Check MAC-address": {"func": search_mac_address, "input_type": "text", "prompt": "Enter MAC address:", "desc": "Lookup the vendor of a MAC address.", "threaded": True},
            "Subdomain finder": {"func": find_subdomains, "input_type": "text", "prompt": "Enter domain (e.g., example.com):", "desc": "Find subdomains for a given domain.", "threaded": True},
            "Google Osint": {"func": google_osint, "input_type": "text", "prompt": "Enter Google search query:", "desc": "Perform a Google search to find information.", "threaded": True},
            "Search Nick": {"func": check_username, "input_type": "text", "prompt": "Enter username:", "desc": "Check for a username's presence on various platforms.", "threaded": True},
            "Web-crawler": {"func": web_crawler, "input_type": "text", "prompt": "Enter starting URL:", "desc": "Crawl a website to discover links and pages.", "threaded": True},
            "Port Scanner": {"func": port_scanner_tool, "input_type": "text", "prompt": "Enter target IP or domain:", "desc": "Scan a target for open ports.", "threaded": True},
            "Check site": {"func": check_site, "input_type": "text", "prompt": "Enter website URL:", "desc": "Check the status and headers of a website.", "threaded": True},
            "Check url": {"func": check_url, "input_type": "text", "prompt": "Enter URL to check:", "desc": "Analyze a URL for safety and redirects.", "threaded": True},
            "Xss scan": {"func": xss_scan, "input_type": "text", "prompt": "Enter URL to scan for XSS:", "desc": "Scan a URL for Cross-Site Scripting vulnerabilities.", "threaded": True},
            "Find admin panel": {"func": find_admin_panel, "input_type": "text", "prompt": "Enter website URL:", "desc": "Try to find the admin login page of a website.", "threaded": True},
            "Sql scan": {"func": sql_injection_scanner_tool, "input_type": "text", "prompt": "Enter URL with parameters to scan:", "desc": "Scan a URL for SQL Injection vulnerabilities.", "threaded": True},
            "Ip logger": {"func": logger_ip, "input_type": None, "desc": "Create a link to log IP addresses of visitors.", "threaded": True},
            "Temp Mail": {"func": temp_mail, "input_type": None, "desc": "Get a temporary email address.", "threaded": True},
            "Get proxy": {"func": get_proxy_list, "input_type": None, "desc": "Fetch a list of free proxy servers.", "threaded": True},
            "Obfuscate python": {"func": obfuscate_tool, "input_type": "text", "prompt": "Enter path to Python file to obfuscate:", "desc": "Obfuscate a Python script to make it harder to read.", "threaded": True},
            "Phish Bot(lamer)": {"func": phishing, "input_type": None, "desc": "Start a simple phishing bot (for educational purposes).", "threaded": True},
            "Strange Text": {"func": transform_text, "input_type": "text", "prompt": "Enter text to transform:", "desc": "Apply various transformations to text (e.g., Zalgo).", "threaded": False},
            "Password Generator": {"func": password_generator_tool, "input_type": None, "desc": "Generate a strong, random password.", "threaded": False},
            "DDoS Attack": {"func": run_ddos_attack, "input_type": "ddos", "desc": "Launch a DDoS attack (for educational purposes only)."},
            "Telegram (paketlib)": {"func": telegram_search, "input_type": "telegram", "desc": "Search for users, channels, and chats on Telegram."},
        }

    def load_plugins(self):
        self.plugins = []
        if not os.path.exists(PLUGIN_DIR):
            os.makedirs(PLUGIN_DIR)
            logging.info(f"Created plugin directory: {PLUGIN_DIR}")
            return

        for filename in os.listdir(PLUGIN_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(PLUGIN_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        plugin_data = json.load(f)
                        if 'name' in plugin_data and 'workflow' in plugin_data:
                            self.plugins.append(plugin_data)
                            logging.info(f"Successfully loaded plugin: {plugin_data['name']}")
                        else:
                            logging.warning(f"Skipping invalid plugin file: {filename}")
                except Exception as e:
                    logging.error(f"Failed to load or parse plugin {filename}: {e}")

    def load_initial_theme(self):
        last_theme_path = load_config(LAST_THEME_CONFIG_FILE)
        theme = load_theme(last_theme_path) if last_theme_path else None
        default_theme = {
            "button_bg_color": "rgba(255, 0, 0, 0.1)", "button_hover_bg_color": "rgba(255, 0, 0, 0.2)",
            "button_pressed_bg_color": "rgba(255, 0, 0, 0.3)", "button_border_color": "rgba(255, 255, 255, 0.2)",
            "button_text_color": "white", "text_area_bg_color": "rgba(0, 0, 0, 0.5)",
            "text_area_border_color": "rgba(255, 255, 255, 0.2)", "text_area_text_color": "white",
            "sidebar_bg_color": "rgba(0, 0, 0, 0.2)",
            "title_text_color": "white", "scrollbar_handle_color": "rgba(255, 255, 255, 0.4)",
            "scrollbar_handle_hover_color": "rgba(255, 255, 255, 0.6)"
        }
        self.theme_data = default_theme
        if theme: self.theme_data.update(theme)
        logging.info("Theme loaded.")

    def apply_theme(self):
        td = self.theme_data
        button_style = f"""
            QPushButton {{
                background-color: {td['button_bg_color']}; border: 1px solid {td['button_border_color']};
                border-radius: 10px; color: {td['button_text_color']}; padding: 10px; font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {td['button_hover_bg_color']}; }}
            QPushButton:pressed {{ background-color: {td['button_pressed_bg_color']}; }}
        """
        self.setStyleSheet(button_style)
        self.sidebar_widget.setStyleSheet(f"background-color: {td['sidebar_bg_color']}; border-radius: 10px;")
        
        scrollbar_style = f"""
            QScrollBar:vertical {{
                border: none; background: transparent; width: 12px; margin: 15px 0 15px 0; border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{ background-color: {td['scrollbar_handle_color']}; min-height: 30px; border-radius: 6px; }}
            QScrollBar::handle:vertical:hover {{ background-color: {td['scrollbar_handle_hover_color']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """
        text_area_style = f"""
            QTextEdit {{
                background-color: {td['text_area_bg_color']}; border: 1px solid {td['text_area_border_color']};
                border-radius: 10px; color: {td['text_area_text_color']}; font-size: 14px;
            }}
        """
        self.output_area.setStyleSheet(text_area_style + scrollbar_style)

        for title_label in self.findChildren(QLabel):
            if title_label.property("is_title"):
                title_label.setStyleSheet(f"color: {td['title_text_color']}; padding-top: 10px; background: transparent;")
        
        self.stacked_widget.setStyleSheet("background: transparent;")
        for i in range(self.stacked_widget.count()):
            self.stacked_widget.widget(i).setStyleSheet("background: transparent;")
        logging.info("Theme applied.")


    def load_theme_from_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Load Theme", "", "JSON Files (*.json)")
        if filepath:
            new_theme = load_theme(filepath)
            if new_theme:
                self.theme_data.update(new_theme)
                self.apply_theme()
                save_config(LAST_THEME_CONFIG_FILE, filepath)
                logging.info(f"Loaded theme from {filepath}")
            else:
                self.output_area.setText("Error: Could not load or parse the theme file.")
                logging.error(f"Failed to load theme from {filepath}")

    def create_new_theme(self):
        temp_theme = self.theme_data.copy()
        original_theme = self.theme_data.copy()
        for key, value in temp_theme.items():
            if 'color' in key:
                color_name = key.replace('_', ' ').title()
                initial_color = QColor(value) if not 'rgba' in str(value) else QColor(value.replace('rgba', 'rgb').rsplit(',', 1)[0] + ')')
                dialog = QColorDialog(self)
                dialog.setCurrentColor(initial_color)
                dialog.setWindowTitle(f"Select {color_name}")
                
                def preview_color(color, key_to_update=key):
                    if color.isValid():
                        if 'rgba' in str(self.theme_data[key_to_update]):
                            alpha = float(str(self.theme_data[key_to_update]).split(',')[-1].strip()[:-1])
                            temp_theme[key_to_update] = f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"
                        else:
                            temp_theme[key_to_update] = color.name()
                        self.theme_data.update(temp_theme)
                        self.apply_theme()
                dialog.currentColorChanged.connect(lambda c, k=key: preview_color(c, k))
                if not dialog.exec():
                    self.theme_data = original_theme
                    self.apply_theme()
                    return
        filepath, _ = QFileDialog.getSaveFileName(self, "Save New Theme", "", "JSON Files (*.json)")
        if filepath:
            save_theme(filepath, self.theme_data)
            save_config(LAST_THEME_CONFIG_FILE, filepath)
            logging.info(f"New theme saved to {filepath}")
        else:
            self.theme_data = original_theme
            self.apply_theme()
            logging.info("New theme creation cancelled.")

    def toggle_ui_visibility(self):
        is_visible = self.ui_container.isVisible()
        self.ui_container.setVisible(not is_visible)
        logging.debug(f"UI visibility toggled to {not is_visible}.")
        if is_visible:
            self.unhide_button = QPushButton("Show UI", self)
            self.unhide_button.setStyleSheet(self.styleSheet())
            self.unhide_button.setFixedSize(100, 40)
            self.unhide_button.move(10, 10)
            self.unhide_button.clicked.connect(self.toggle_ui_visibility)
            self.unhide_button.show()
        elif hasattr(self, 'unhide_button'):
            self.unhide_button.hide()

    def set_background(self, path):
        logging.info(f"Setting background to: {path}")
        self.player.stop()
        if not path or not os.path.exists(path): 
            path = "background0.gif"
            logging.warning(f"Path not found, falling back to {path}")
        
        _, extension = os.path.splitext(path.lower())
        if extension == ".gif":
            logging.debug("Background type: GIF")
            movie = QMovie(path)
            if movie.isValid():
                self.gif_label.setMovie(movie)
                movie.start()
                self.background_container.setCurrentWidget(self.gif_label)
                logging.info("GIF background set successfully.")
            else:
                logging.error(f"Failed to load GIF: {path}")
                self.output_area.setText(f"Failed to load GIF: {path}")
        elif extension in [".mp4", ".avi"]:
            logging.debug("Background type: Video")
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            self.background_container.setCurrentWidget(self.video_frame_label)
            self.player.play()
            logging.info("Video background set successfully.")
        else:
            logging.error(f"Unsupported background file format: {extension}")
            self.output_area.setText(f"Unsupported file format: {extension}")
            return
        save_config(CONFIG_FILE, path)

    def load_and_set_initial_background(self):
        path = load_config(CONFIG_FILE)
        logging.info(f"Loading initial background from config: {path}")
        self.set_background(path or "background0.gif")

    def change_background(self):
        text, ok = QInputDialog.getText(self, 'Change Background', 'Enter local file path or URL:')
        if ok and text:
            path_or_url = text.strip()
            logging.info(f"Attempting to change background to: {path_or_url}")
            if path_or_url.startswith(('http://', 'https://')):
                self.download_and_set_background(path_or_url)
            elif os.path.exists(path_or_url):
                self.set_background(path_or_url)
            else:
                logging.error(f"Background file not found: {path_or_url}")
                self.output_area.setText(f"File not found: {path_or_url}")

    def download_and_set_background(self, url):
        try:
            logging.info(f"Downloading background from {url}")
            self.output_area.setText(f"Downloading from {url}...")
            QApplication.processEvents()
            response = requests.get(url, stream=True, timeout=15)
            response.raise_for_status()
            filename = url.split('/')[-1]
            _, extension = os.path.splitext(filename)
            if not extension:
                 content_type = response.headers.get('content-type')
                 if content_type:
                     if 'gif' in content_type: extension = '.gif'
                     elif 'mp4' in content_type: extension = '.mp4'
            local_filename = "downloaded_background" + (extension or ".tmp")
            with open(local_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
            logging.info(f"Download complete. Saved as {local_filename}")
            self.output_area.setText("Download complete. Applying background...")
            self.set_background(local_filename)
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to download background: {e}")
            self.output_area.setText(f"Failed to download: {e}")

    def create_categorized_menu(self):
        menu_widget = QWidget()
        main_layout = QHBoxLayout(menu_widget)
        categories = {
            "Information Gathering (OSINT)": ["Check Phone Number", "Check IP", "Validate Email", "Info Website", "Gmail Osint", "Database search", "Check MAC-address", "Subdomain finder", "Google Osint", "Telegram (paketlib)", "Search Nick", "Web-crawler"],
            "Web & Network Security": ["Port Scanner", "Check site", "Check url", "Xss scan", "Find admin panel", "Sql scan", "DDoS Attack"],
            "Tools & Utilities": ["Strange Text", "Password Generator", "Temp Mail", "Get proxy", "Ip logger", "Obfuscate python", "Phish Bot(lamer)"]
        }
        
        if self.plugins:
            categories["Plugins"] = [p['name'] for p in self.plugins]

        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        for title, buttons in categories.items():
            col_widget = QWidget()
            col_layout = QVBoxLayout(col_widget)
            title_label = QLabel(title)
            title_label.setFont(title_font)
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_label.setProperty("is_title", True)
            col_layout.addWidget(title_label)
            for text in buttons:
                button = GlassButton(text)
                if title == "Plugins":
                    plugin_data = next((p for p in self.plugins if p['name'] == text), None)
                    if plugin_data:
                        button.setToolTip(plugin_data.get("description", "No description"))
                        button.clicked.connect(lambda checked, p=plugin_data: self.run_plugin_dispatcher(p))
                elif text in self.tool_info:
                    info = self.tool_info[text]
                    button.setToolTip(info.get("desc", ""))
                    button.clicked.connect(lambda checked, t=text: self.run_tool_dispatcher(t))
                col_layout.addWidget(button)
            col_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
            main_layout.addWidget(col_widget)
        self.stacked_widget.addWidget(menu_widget)
        logging.info("Categorized menu created.")

    def set_output_text(self, text):
        self.output_area.setText(text)

    def run_plugin_dispatcher(self, plugin_data):
        logging.info(f"Dispatching plugin: {plugin_data['name']}")
        self.output_area.clear()
        
        first_step = plugin_data['workflow'][0]
        if first_step.get("input_source") == "user":
            dialog = CustomInputDialog(self, title=plugin_data['name'], prompt=first_step.get("prompt", "Enter value:"))
            if dialog.exec():
                input_data = dialog.get_text()
                if input_data:
                    self.thread = QThread()
                    self.worker = Worker(plugin_data, input_data, is_plugin=True, tool_info=self.tool_info)
                    self.worker.moveToThread(self.thread)
                    self.thread.started.connect(self.worker.run)
                    self.worker.finished.connect(self.thread.quit)
                    self.worker.finished.connect(self.worker.deleteLater)
                    self.thread.finished.connect(self.thread.deleteLater)
                    self.worker.result.connect(self.set_output_text)
                    self.worker.error.connect(self.set_output_text)
                    self.thread.start()
                    self.output_area.setText(f"Running plugin '{plugin_data['name']}' in the background...")
                else:
                    self.output_area.setText("Operation cancelled: input was empty.")
            else:
                self.output_area.setText("Operation cancelled.")
        else:
            # Handle plugins with no user input needed
            pass

    def run_tool_dispatcher(self, tool_name):
        logging.info(f"Dispatching tool: {tool_name}")
        self.output_area.clear()
        if tool_name not in self.tool_info:
            logging.error(f"Tool '{tool_name}' not found in tool_info.")
            self.output_area.setText(f"Error: Tool '{tool_name}' not defined.")
            return
        
        info = self.tool_info[tool_name]
        tool_func, input_type = info["func"], info["input_type"]
        input_data, ok = None, False

        if input_type is None: ok = True
        elif input_type == "text":
            dialog = CustomInputDialog(self, title=tool_name, prompt=info.get("prompt", "Enter value:"))
            if dialog.exec():
                input_data = dialog.get_text()
                if input_data: ok = True
        elif input_type == "ddos":
            dialog = DDoSAttackDialog(self)
            if dialog.exec():
                input_data = dialog.get_values()
                if input_data: ok = True
        elif input_type == "telegram":
            dialog = TelegramSearchDialog(self)
            if dialog.exec():
                input_data = dialog.get_values()
                if input_data: ok = True
        
        if not ok:
            logging.warning(f"Tool '{tool_name}' cancelled or input was empty.")
            self.output_area.setText("Operation cancelled or input was empty.")
            return
        
        logging.debug(f"Input received for {tool_name}: {input_data}")

        if info.get("threaded", False):
            self.thread = QThread()
            self.worker = Worker(tool_func, input_data)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.result.connect(self.set_output_text)
            self.worker.error.connect(self.set_output_text)
            self.thread.start()
            self.output_area.setText(f"Running {tool_name} in the background...")
        elif isinstance(input_data, dict):
            self.execute_special_tool(tool_func, input_data)
        else:
            self.execute_tool(tool_func, input_data)

    def execute_tool(self, tool_function, input_data):
        logging.info(f"Executing standard tool: {tool_function.__name__}")
        output_stream = io.StringIO()
        original_input = builtins.input
        builtins.input = lambda prompt="": input_data or ""
        try:
            with contextlib.redirect_stdout(output_stream):
                tool_function()
            self.output_area.setText(remove_ansi_codes(output_stream.getvalue()))
        except Exception as e:
            logging.error(f"Error executing tool {tool_function.__name__}: {e}", exc_info=True)
            self.output_area.setText(f"An error occurred: {e}")
        finally:
            builtins.input = original_input

    def execute_special_tool(self, tool_function, data):
        logging.info(f"Executing special tool in a thread: {tool_function.__name__}")
        self.output_area.clear()
        QApplication.processEvents()
        if tool_function == run_ddos_attack:
            thread = threading.Thread(target=self.run_ddos_thread, args=(data,))
            thread.start()
        elif tool_function == telegram_search:
            thread = threading.Thread(target=self.run_telegram_thread, args=(data,))
            thread.start()

    def run_ddos_thread(self, data):
        logging.info(f"DDoS thread started with data: {data}")
        self.output_area.append(f"Starting DDoS attack: {data['method']} on {data['target']}\n")
        try:
            run_ddos_attack(data)
            self.output_area.append("\nAttack finished.")
            logging.info("DDoS thread finished.")
        except Exception as e:
            logging.error(f"Error in DDoS thread: {e}", exc_info=True)
            self.output_area.append(f"\nAn error occurred during the attack: {e}")

    def run_telegram_thread(self, data):
        logging.info(f"Telegram thread started with data: {data}")
        output_stream = io.StringIO()
        try:
            with contextlib.redirect_stdout(output_stream):
                telegram_search(data)
            self.output_area.setText(remove_ansi_codes(output_stream.getvalue()))
            logging.info("Telegram thread finished.")
        except Exception as e:
            logging.error(f"Error in Telegram thread: {e}", exc_info=True)
            self.output_area.setText(f"An error occurred during Telegram search: {e}")

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        main_win = MainWindow()
        main_win.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.critical(f"Unhandled exception at top level: {e}", exc_info=True)
        sys.exit(1)