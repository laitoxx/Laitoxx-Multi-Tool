import logging

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QMainWindow,
)

from laitoxx.app.tool_registry import CATEGORIES, TOOL_REGISTRY
from laitoxx.core.localization.i18n import translator
from laitoxx.core.settings.app_settings import settings
from laitoxx.core.settings.network_manager import NetworkManager
from laitoxx.core.settings.paths import ensure_runtime_dirs
from laitoxx.interfaces.gui.main_window_appearance import MainWindowAppearanceMixin
from laitoxx.interfaces.gui.main_window_execution import MainWindowExecutionMixin
from laitoxx.interfaces.gui.main_window_graph import MainWindowGraphMixin
from laitoxx.interfaces.gui.main_window_preferences import MainWindowPreferencesMixin
from laitoxx.interfaces.gui.main_window_tasks import MainWindowTasksMixin
from laitoxx.interfaces.gui.main_window_tools import MainWindowToolsMixin
from laitoxx.interfaces.gui.main_window_ui import MainWindowUiMixin
from laitoxx.interfaces.gui.terminal_window import TerminalWindow
from laitoxx.interfaces.gui.tool_execution_controller import ToolExecutionController
from laitoxx.interfaces.gui.tool_input_controller import ToolInputController


class MainWindow(
    MainWindowUiMixin,
    MainWindowAppearanceMixin,
    MainWindowPreferencesMixin,
    MainWindowToolsMixin,
    MainWindowExecutionMixin,
    MainWindowGraphMixin,
    MainWindowTasksMixin,
    QMainWindow,
):
    def __init__(self):
        super().__init__()
        logging.info("MainWindow.__init__ started.")
        self.tool_registry = TOOL_REGISTRY
        self.categories = CATEGORIES
        self.running_tools = {}
        self._zombie_threads = set()
        self.plugin_builder_window = None
        self.unhide_button = None
        self.lua_plugins: list = []
        self._terminal_window: TerminalWindow | None = None
        self._graph_editor_window = None
        self._username_osint_window = None
        self._image_search_window = None
        self.input_controller = ToolInputController(self)
        self.execution_controller = ToolExecutionController(self)

        ensure_runtime_dirs()
        NetworkManager.apply(settings.proxy)
        translator.set_language(settings.language)

        self.load_initial_theme()
        self._build_ui()
        self._command_palette_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        self._command_palette_shortcut.activated.connect(self._open_command_palette)
        self.load_lua_plugins()
        self.retranslate_ui()
        self._load_and_set_initial_background()
        self._last_schedule_hour: int = -1
        self._schedule_timer = QTimer(self)
        self._schedule_timer.timeout.connect(self._check_theme_schedule)
        self._schedule_timer.start(60_000)
        logging.info("MainWindow.__init__ finished.")

    def closeEvent(self, event):
        """Close owned top-level helpers before the main window disappears."""
        terminal = self._terminal_window
        if terminal is not None:
            terminal.close()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
