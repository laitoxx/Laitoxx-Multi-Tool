"""Main window responsibility mixin."""

import logging
import os

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QMovie, QResizeEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsBlurEffect,
    QInputDialog,
    QLabel,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.core.settings.app_settings import settings
from laitoxx.core.settings.background import default_background, import_background
from laitoxx.core.settings.paths import DEFAULT_THEME_FILE
from laitoxx.core.settings.theme import (
    load_default_theme,
    load_theme,
    save_theme_to_resources,
)
from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme
from laitoxx.interfaces.gui.theme_editor import ThemeEditorDialog


class MainWindowAppearanceMixin:
    def _apply_performance_mode(self):
        """Toggle visual effects that affect performance."""
        perf = bool(settings.performance_mode)
        # Blur effect is expensive on large video surfaces
        if perf:
            self.background_container.setGraphicsEffect(None)
        else:
            self.background_container.setGraphicsEffect(QGraphicsBlurEffect(blurRadius=10))

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.background_container.setGeometry(self.rect())
        self.ui_container.setGeometry(self.rect())
        self.ui_container.raise_()

    def _set_background(self, path):
        self.player.stop()
        if not path or not os.path.exists(path):
            path = default_background()
        if not path or not os.path.exists(path):
            self._set_output("Background file not found.")
            return
        try:
            bg_dir = os.path.abspath(os.path.dirname(default_background()))
            if not os.path.abspath(path).startswith(bg_dir):
                path = import_background(path)
        except OSError:
            pass
        _, ext = os.path.splitext(path.lower())
        if ext == ".gif":
            movie = QMovie(path)
            movie.setCacheMode(QMovie.CacheMode.CacheNone)
            if movie.isValid():
                self.gif_label.setMovie(movie)
                movie.start()
                self.background_container.setCurrentWidget(self.gif_label)
        elif ext in (".mp4", ".avi"):
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            self.background_container.setCurrentWidget(self.video_widget)
            self.player.play()
        else:
            self._set_output(f"Unsupported file format: {ext}")
            return
        settings.background_path = path

    def _load_and_set_initial_background(self):
        path = settings.background_path or default_background()
        self._set_background(path)

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def load_initial_theme(self, use_last_saved=True):
        self.theme_data = load_default_theme()
        if use_last_saved:
            theme_path = settings.theme_path
            if theme_path:
                saved = load_theme(theme_path)
                if saved:
                    self.theme_data.update(saved)
                else:
                    settings.theme_path = DEFAULT_THEME_FILE
        self._inject_appearance_settings()

    def _inject_appearance_settings(self):
        """Keep presentation preferences separate from color-theme files."""
        self.theme_data["style_mode"] = settings.style_mode
        self.theme_data["font_family"] = settings.font_family
        self.theme_data["code_font_family"] = settings.code_font_family
        self.theme_data["font_size"] = settings.font_size

    def apply_theme(self):
        self._inject_appearance_settings()
        td = resolved_theme(self.theme_data)
        _br = td.get("border_radius", 10)
        workspace_qss = build_workspace_qss(td)
        self.setStyleSheet(workspace_qss)
        if self.unhide_button:
            self.unhide_button.setStyleSheet(workspace_qss)
        scrollbar = (
            "QScrollBar:vertical { border: none; background: transparent; width: 8px;"
            " margin: 0; border-radius: 4px; }"
            "QScrollBar::handle:vertical { background-color: rgba(160,160,160,0.85);"
            " min-height: 24px; border-radius: 4px; }"
            "QScrollBar::handle:vertical:hover { background-color: rgba(200,200,200,0.95); }"
            "QScrollBar::handle:vertical:pressed { background-color: rgba(220,220,220,1.0); }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }"
            "QScrollBar:horizontal { border: none; background: transparent; height: 8px;"
            " margin: 0; border-radius: 4px; }"
            "QScrollBar::handle:horizontal { background-color: rgba(160,160,160,0.85);"
            " min-width: 24px; border-radius: 4px; }"
            "QScrollBar::handle:horizontal:hover { background-color: rgba(200,200,200,0.95); }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }"
            "QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }"
        )
        text_area = (
            f"QPlainTextEdit {{ background-color: {td['text_area_bg_color']};"
            f" border: 1px solid {td['text_area_border_color']};"
            f" border-radius: {_br}px; color: {td['text_area_text_color']}; font-size: 14px; }}"
        )
        self.output_area.setStyleSheet(text_area + scrollbar)
        tooltip_style = (
            f"QToolTip {{ color: {td.get('text_area_text_color', 'white')}; "
            f"background-color: {td.get('text_area_bg_color', 'rgba(20,20,20,255)')}; "
            f"border: 1px solid {td.get('text_area_border_color', 'gray')}; }}"
        )
        # Apply scrollbar and tooltip style globally to the entire application
        QApplication.instance().setStyleSheet(workspace_qss + scrollbar + tooltip_style)
        # Update terminal window theme if open
        if self._terminal_window:
            self._terminal_window.update_theme(td)
        # Update detached windows theme if open
        if self._graph_editor_window and self._graph_editor_window.isVisible():
            self._graph_editor_window.update_theme(td)
        if self._username_osint_window and self._username_osint_window.isVisible():
            self._username_osint_window.update_theme(td)
        if self._image_search_window and self._image_search_window.isVisible():
            self._image_search_window.update_theme(td)
        for attr in (
            "_advanced_web_scanner_window",
            "_network_info_window",
            "_steganography_window",
            "_tongue_window",
            "_cognipass_window",
            "_masscan_window",
        ):
            window = getattr(self, attr, None)
            if window and window.isVisible() and hasattr(window, "update_theme"):
                window.update_theme(td)
        for label in self.findChildren(QLabel):
            try:
                if label.property("is_title"):
                    label.setStyleSheet(f"color: {td['title_text_color']}; padding-top: 10px; background: transparent;")
            except RuntimeError:
                # QLabel was deleted during UI rebuild/retranslate
                continue
        self.stacked_widget.setStyleSheet("background: transparent;")
        for i in range(self.stacked_widget.count()):
            self.stacked_widget.widget(i).setStyleSheet("background: transparent;")

    def _load_theme_from_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, translator.get("change_theme"), "", "JSON Files (*.json)")
        if filepath:
            new_theme = load_theme(filepath)
            if new_theme:
                self.theme_data.update(new_theme)
                self.apply_theme()
                name = os.path.splitext(os.path.basename(filepath))[0]
                saved_path = save_theme_to_resources(name, self.theme_data)
                settings.theme_path = saved_path
            else:
                self._set_output(translator.get("load_theme_error"))

    def _check_theme_schedule(self):
        if not settings.auto_theme_schedule:
            return
        import datetime

        hour = datetime.datetime.now().hour
        if hour == self._last_schedule_hour:
            return
        target = None
        if settings.day_theme and hour == settings.day_start:
            target = settings.day_theme
        elif settings.night_theme and hour == settings.night_start:
            target = settings.night_theme
        if target:
            from laitoxx.core.settings.theme import load_theme

            data = load_theme(target)
            if data:
                self.theme_data.update(data)
                settings.theme_path = target
                self.apply_theme()
                self._last_schedule_hour = hour

    def _create_new_theme(self):
        editor = ThemeEditorDialog(self, self.theme_data)
        if editor.exec():
            self.theme_data = editor.get_theme_data()
            name, ok = QInputDialog.getText(
                self,
                translator.get("theme_name_title"),
                translator.get("theme_name_prompt"),
            )
            if ok and name:
                saved_path = save_theme_to_resources(name, self.theme_data)
                settings.theme_path = saved_path
                logging.info(translator.get("theme_saved_success", path=saved_path))
        self.apply_theme()

    # ------------------------------------------------------------------
    # Settings Window
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Plugins (Lua only)
    # ------------------------------------------------------------------
