"""Main window responsibility mixin."""

from PyQt6.QtWidgets import (
    QPushButton,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.core.settings.app_settings import settings
from laitoxx.core.settings.network_manager import NetworkManager
from laitoxx.core.settings.settings_window import SettingsWindow


class MainWindowPreferencesMixin:
    def _open_settings(self):
        dlg = SettingsWindow(self, theme_data=self.theme_data, translator=translator)
        dlg.theme_changed.connect(self._on_settings_theme_changed)
        dlg.background_changed.connect(self._on_settings_background_changed)
        dlg.language_changed.connect(self._on_settings_language_changed)
        dlg.proxy_changed.connect(self._on_settings_proxy_changed)
        dlg.application_reset.connect(self._on_application_reset)
        dlg.exec()
        self._apply_performance_mode()

    def _on_settings_theme_changed(self, theme_data: dict, _path: str):
        self.theme_data = theme_data
        self._inject_appearance_settings()
        self.apply_theme()

    def _on_settings_background_changed(self, path: str):
        self._set_background(path)

    def _on_settings_language_changed(self, lang: str):
        translator.set_language(lang)
        self.retranslate_ui()

    def _on_settings_proxy_changed(self):
        NetworkManager.apply(settings.proxy)

    def _on_application_reset(self):
        translator.set_language(settings.language)
        NetworkManager.apply(settings.proxy)
        self.load_initial_theme()
        self._load_and_set_initial_background()
        self.retranslate_ui()

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------

    def _on_combo_lang_changed(self, index: int):
        lang_codes = ["en", "ru", "uk", "tr"]
        if 0 <= index < len(lang_codes):
            new_lang = lang_codes[index]
            translator.set_language(new_lang)
            settings.language = new_lang
            self.retranslate_ui()

    def retranslate_ui(self):
        self.setWindowTitle(translator.get("app_title"))
        self.search_bar.setPlaceholderText(translator.get("search"))
        self.btn_settings.setText(translator.get("settings"))
        self.btn_plugin_builder.setText(translator.get("plugin_builder"))
        self.btn_graph_editor.setText(translator.get("graph_editor"))
        self.btn_create_theme.setText(translator.get("create_color_theme"))
        self.btn_hide_ui.setText(translator.get("hide_ui"))
        self.btn_exit.setText(translator.get("exit"))
        self._btn_popout.setText("⧉ " + translator.get("terminal"))
        self._btn_popout.setToolTip(translator.get("terminal_tooltip"))
        self.smart_paste_btn.setText(translator.get("Smart Paste"))
        self.palette_btn.setToolTip(translator.get("Command Palette"))
        self._btn_add_graph.setText(translator.get("Add results to graph"))
        if self.unhide_button:
            self.unhide_button.setText(translator.get("show_ui"))
        if self.plugin_builder_window:
            self.plugin_builder_window.retranslate_ui()
        self.reload_plugins_and_ui()

    # ------------------------------------------------------------------
    # UI visibility
    # ------------------------------------------------------------------

    def _toggle_ui_visibility(self):
        if self.ui_container.isVisible():
            self.ui_container.hide()
            self._show_unhide_button()
        else:
            self.ui_container.show()
            self._hide_unhide_button()

    def _show_unhide_button(self):
        if not self.unhide_button:
            self.unhide_button = QPushButton(translator.get("show_ui"), self)
            self.unhide_button.setFixedSize(100, 40)
            self.unhide_button.move(10, 10)
            self.unhide_button.clicked.connect(self._toggle_ui_visibility)
        else:
            self.unhide_button.setText(translator.get("show_ui"))
        self.unhide_button.setStyleSheet(self.styleSheet())
        self.unhide_button.show()
        self.unhide_button.raise_()

    def _hide_unhide_button(self):
        if self.unhide_button:
            self.unhide_button.hide()
