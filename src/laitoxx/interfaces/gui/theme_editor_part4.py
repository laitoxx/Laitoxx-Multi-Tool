"""Focused behavior slice for ThemeEditorDialog."""
# ruff: noqa: F405

from .theme_editor_context import *  # noqa: F403


class ThemeEditorDialogMixin4:
    def _copy_color(self):
        if not self._current_key or self._current_key == "border_radius":
            return
        css = self.theme_data.get(self._current_key, "#ffffff")
        color = _parse_color(css)
        QApplication.clipboard().setText(color.name())

    def _paste_color(self):
        if not self._current_key or self._current_key == "border_radius":
            return
        text = QApplication.clipboard().text().strip()
        color = _parse_color(text)
        if color.isValid():
            self._apply_css_string(text)

    def _start_eyedropper(self):
        self._eyedropper = _EyedropperOverlay()
        self._eyedropper.color_picked.connect(self._on_eyedropper_color)

    def _on_eyedropper_color(self, color: QColor):
        if self._current_key and self._current_key != "border_radius":
            self._apply_css_string(color.name())

    def _wcag_autofix_selected(self):
        if not self._current_key or self._current_key == "border_radius":
            return
        fg_css = self.theme_data.get(self._current_key, "#ffffff")
        fg = _parse_color(fg_css)
        bg_css = self.theme_data.get("text_area_bg_color", "#000000")
        bg = _parse_color(bg_css)
        bg.setAlpha(255)
        fg.setAlpha(255)
        fixed = _wcag_autofix(fg, bg)
        self._apply_css_string(fixed.name())

    def _on_border_radius_changed(self, value: int):
        self.theme_data["border_radius"] = value
        if hasattr(self, "_br_label"):
            self._br_label.setText(f"{value}px")
        if self.parent() and hasattr(self.parent(), "theme_data"):
            self.parent().theme_data = self.theme_data
            self.parent().apply_theme()
        self._update_preview()

    def _invert_theme(self):
        for key in list(self.theme_data.keys()):
            if key == "border_radius":
                continue
            css = self.theme_data.get(key, "")
            if not css:
                continue
            color = _parse_color(css)
            if not color.isValid():
                continue
            r, g, b = color.redF(), color.greenF(), color.blueF()
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            r2, g2, b2 = colorsys.hsv_to_rgb(h, s, 1.0 - v)
            inverted = QColor.fromRgbF(r2, g2, b2, color.alphaF())
            self.theme_data[key] = _to_css(inverted, css)
        if self._current_key and self._current_key != "border_radius":
            css = self.theme_data.get(self._current_key, "#ffffff")
            self._load_color(_parse_color(css), css)
        self._update_preview()
        if self.parent() and hasattr(self.parent(), "theme_data"):
            self.parent().theme_data = self.theme_data
            self.parent().apply_theme()

    def _on_colorblind_changed(self, idx: int):
        mode = self._combo_colorblind.itemData(idx) or "none"
        self._colorblind_mode = mode
        self._update_preview()

    def _populate_library(self, search: str = ""):
        from laitoxx.core.settings.app_settings import settings
        from laitoxx.core.settings.theme import list_themes

        self._lib_list.setUpdatesEnabled(False)
        self._lib_list.clear()
        search = search.lower()
        themes = list_themes()
        favs = settings.favorite_themes

        for name, path in themes:
            if search and search not in name.lower():
                continue
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, path)

            # Build row widget with name + star button
            row_w = QWidget()
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(4, 2, 4, 2)
            row_lay.setSpacing(4)

            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(f"color: {_TEXT}; font-size: 12px; background: transparent;")
            row_lay.addWidget(name_lbl, 1)

            is_fav = path in favs
            star_btn = QPushButton("★" if is_fav else "☆")
            star_btn.setFixedSize(24, 24)
            star_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; color: {'#f9c74f' if is_fav else _TEXT_DIM}; font-size: 14px; }}"
                f"QPushButton:hover {{ color: #f9c74f; }}"
            )
            star_btn.clicked.connect(lambda _, p=path: self._toggle_favorite(p))
            row_lay.addWidget(star_btn)

            self._lib_list.addItem(item)
            item.setSizeHint(row_w.sizeHint())
            self._lib_list.setItemWidget(item, row_w)
        self._lib_list.setUpdatesEnabled(True)

    def _apply_library_theme(self):
        item = self._lib_list.currentItem()
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        from laitoxx.core.settings.theme import load_theme

        data = load_theme(path)
        if data:
            self.theme_data.update(data)
            if self._current_key and self._current_key != "border_radius":
                css = self.theme_data.get(self._current_key, "#ffffff")
                self._load_color(_parse_color(css), css)
            if self.parent() and hasattr(self.parent(), "theme_data"):
                self.parent().theme_data = self.theme_data
                self.parent().apply_theme()
            self._update_preview()
            # Update border radius slider
            if hasattr(self, "_br_slider"):
                self._br_slider.setValue(int(self.theme_data.get("border_radius", 10)))

    def _toggle_favorite(self, path: str):
        from laitoxx.core.settings.app_settings import settings

        favs = list(settings.favorite_themes)
        if path in favs:
            favs.remove(path)
        else:
            favs.append(path)
        settings.favorite_themes = favs
        self._populate_library(self._lib_search.text())

    def _reset(self):
        if self.parent() and hasattr(self.parent(), "load_initial_theme"):
            self.parent().load_initial_theme(use_last_saved=False)
            self.theme_data = self.parent().theme_data.copy()
        else:
            self.theme_data = self.original_theme.copy()
        if self._current_key:
            css = self.theme_data.get(self._current_key, "#ffffff")
            self._load_color(_parse_color(css), css)
        if self.parent() and hasattr(self.parent(), "apply_theme"):
            self.parent().apply_theme()

    def _save_and_close(self):
        self.accept()

    def _cancel(self):
        # Restore original theme
        if self.parent() and hasattr(self.parent(), "theme_data"):
            self.parent().theme_data = self.original_theme
            self.parent().apply_theme()
        self.reject()

    def get_theme_data(self) -> dict:
        return self.theme_data
