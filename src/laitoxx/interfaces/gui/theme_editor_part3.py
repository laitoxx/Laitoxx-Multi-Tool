"""Focused behavior slice for ThemeEditorDialog."""
# ruff: noqa: F405

from .theme_editor_context import *  # noqa: F403


class ThemeEditorDialogMixin3:
    def _populate_list(self, search: str = ""):
        self._list.clear()
        search = search.lower()
        for group_key, keys in _GROUPS.items():
            group_label = translator.get(group_key)
            group_added = False
            for key in keys:
                display = self._theme_map.get(key, key)
                if search and search not in display.lower():
                    continue
                if not group_added:
                    header = QListWidgetItem(f"── {group_label} ──")
                    header.setFlags(Qt.ItemFlag.NoItemFlags)
                    header.setForeground(QColor(_TEXT_DIM))
                    font = header.font()
                    font.setPointSize(9)
                    font.setBold(True)
                    header.setFont(font)
                    self._list.addItem(header)
                    group_added = True
                item = QListWidgetItem(f"  {display}")
                item.setData(Qt.ItemDataRole.UserRole, key)
                item.setToolTip(key)
                # Color swatch in item
                color = _parse_color(self.theme_data.get(key, "#ffffff"))
                px = QPixmap(12, 12)
                px.fill(color)
                item.setIcon(px if False else item.icon())  # skip icon to keep it clean
                self._list.addItem(item)

        # also add keys not in any group (future-proofing)
        ungrouped_added = False
        all_grouped = [k for keys in _GROUPS.values() for k in keys]
        for key in self.theme_data:
            if key not in all_grouped and key not in _NON_COLOR_KEYS:
                display = self._theme_map.get(key, key)
                if search and search not in display.lower():
                    continue
                if not ungrouped_added:
                    header = QListWidgetItem(f"── {translator.get('te_other')} ──")
                    header.setFlags(Qt.ItemFlag.NoItemFlags)
                    header.setForeground(QColor(_TEXT_DIM))
                    self._list.addItem(header)
                    ungrouped_added = True
                item = QListWidgetItem(f"  {display}")
                item.setData(Qt.ItemDataRole.UserRole, key)
                item.setToolTip(key)
                self._list.addItem(item)

    def _filter_list(self, text: str):
        current_key = self._current_key
        self._populate_list(text)
        # try to restore selection
        if current_key:
            for i in range(self._list.count()):
                it = self._list.item(i)
                if it and it.data(Qt.ItemDataRole.UserRole) == current_key:
                    self._list.setCurrentItem(it)
                    break

    def _on_item_selected(self, current, _previous):
        if not current:
            return
        key = current.data(Qt.ItemDataRole.UserRole)
        if not key:
            return
        self._current_key = key
        display = self._theme_map.get(key, key)
        self._element_lbl.setText(display)
        self._element_key_lbl.setText(key)
        if key == "border_radius":
            return  # handled by slider in Tools tab
        css = self.theme_data.get(key, "#ffffff")
        color = _parse_color(css)
        self._load_color(color, css)
        if hasattr(self, "_palette_base_lbl"):
            self._palette_base_lbl.setText(f"{translator.get('te_base')}: {display}")

    def _load_color(self, color: QColor, css: str):
        self._wheel.set_color(color)
        self._alpha_bar.set_color(color)
        self._update_alpha_label(color.alphaF())
        self._updating_hex = True
        self._hex_input.setText(css)
        self._updating_hex = False
        self._update_swatch(color)
        self._update_contrast(color)

    def _on_wheel_changed(self, color: QColor):
        color.setAlphaF(self._alpha_bar.alpha())
        if not self._current_key:
            return
        original = self.theme_data.get(self._current_key, "#ffffff")
        css = _to_css(color, original)
        self._commit(css, color)

    def _on_alpha_changed(self, alpha: float):
        self._update_alpha_label(alpha)
        color = self._wheel.color()
        color.setAlphaF(alpha)
        self._alpha_bar.set_color(color)
        if not self._current_key:
            return
        original = self.theme_data.get(self._current_key, "#ffffff")
        # If original didn't have rgba, switch it now that alpha changed
        if alpha < 0.999:
            css = f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha:.3f})"
        else:
            css = _to_css(color, original)
        self._commit(css, color)

    def _on_hex_edited(self, text: str):
        if self._updating_hex or not self._current_key:
            return
        color = _parse_color(text)
        if color.isValid():
            self._load_color(color, text)
            self._commit(text, color)

    def _apply_css_string(self, css: str):
        """Apply a CSS string (from history or preset)."""
        if not self._current_key:
            return
        color = _parse_color(css)
        self._load_color(color, css)
        self._commit(css, color)

    def _commit(self, css: str, color: QColor):
        """Write to theme_data, update hex box, live-preview."""
        if not self._current_key:
            return
        self.theme_data[self._current_key] = css
        if hasattr(self, "_header_state"):
            self._header_state.setText(translator.get("te_unsaved_changes"))
        self._updating_hex = True
        self._hex_input.setText(css)
        self._updating_hex = False
        self._update_swatch(color)
        self._update_contrast(color)
        self._wheel.set_color(color)
        self._alpha_bar.set_color(color)
        self._update_alpha_label(color.alphaF())
        # Live preview
        if self.parent() and hasattr(self.parent(), "theme_data"):
            self.parent().theme_data = self.theme_data
            self.parent().apply_theme()
        # Update preview pane if visible
        if hasattr(self, "_center_tabs") and self._center_tabs.currentIndex() == 2:
            self._update_preview()

    def _update_swatch(self, color: QColor):
        px = QPixmap(36, 24)
        px.fill(color)
        self._swatch.setPixmap(px)
        self._history.push(self._hex_input.text())

    def _update_contrast(self, color: QColor):
        # Use the color as foreground against current bg
        bg_css = self.theme_data.get("text_area_bg_color", "rgba(0,0,0,0.5)")
        bg = _parse_color(bg_css)
        bg.setAlpha(255)  # ignore alpha for contrast calculation
        fg = QColor(color)
        fg.setAlpha(255)
        self._contrast.update_colors(fg, bg)

    def _update_alpha_label(self, alpha: float):
        self._alpha_val_lbl.setText(f"{int(alpha * 100)}%")

    def _apply_preset(self, name: str):
        preset = PRESETS.get(name, {})
        self.theme_data.update(preset)
        # Reload current key picker
        if self._current_key:
            css = self.theme_data.get(self._current_key, "#ffffff")
            self._load_color(_parse_color(css), css)
        # Live preview
        if self.parent() and hasattr(self.parent(), "theme_data"):
            self.parent().theme_data = self.theme_data
            self.parent().apply_theme()

    def _export_json(self):
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            translator.get("theme_name_title"),
            translator.get("theme_name_prompt"),
        )
        if ok and name:
            path = save_theme_to_resources(name, self.theme_data)
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                translator.get("te_export_ok"),
                f"{path}",
            )

    def _import_json(self):
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self, translator.get("te_import_json"), "", "JSON (*.json)")
        if path:
            from laitoxx.core.settings.theme import load_theme

            data = load_theme(path)
            if data:
                self.theme_data.update(data)
                if self._current_key:
                    css = self.theme_data.get(self._current_key, "#ffffff")
                    self._load_color(_parse_color(css), css)
                if self.parent() and hasattr(self.parent(), "theme_data"):
                    self.parent().theme_data = self.theme_data
                    self.parent().apply_theme()

    def _show_palette(self, mode: str):
        if not self._current_key or self._current_key == "border_radius":
            return
        css = self.theme_data.get(self._current_key, "#ffffff")
        base = _parse_color(css)
        palette = _generate_palette(base)
        colors = palette.get(mode, [])
        self._last_palette = colors
        # Pad to 5 swatches
        for i, sw in enumerate(self._palette_swatches):
            if i < len(colors):
                sw.set_color(colors[i])
            else:
                sw.set_color(QColor("transparent"))

    def _on_palette_swatch_clicked(self, color: QColor):
        if self._current_key and self._current_key != "border_radius":
            self._apply_css_string(color.name())

    def _apply_palette_to_all(self):
        if not self._last_palette:
            return
        result = _palette_to_theme(self._last_palette, self.theme_data)
        self.theme_data.update(result)
        if self._current_key and self._current_key != "border_radius":
            css = self.theme_data.get(self._current_key, "#ffffff")
            self._load_color(_parse_color(css), css)
        if self.parent() and hasattr(self.parent(), "theme_data"):
            self.parent().theme_data = self.theme_data
            self.parent().apply_theme()
        self._update_preview()

    def _extract_from_image(self):
        try:
            from PIL import Image
        except ImportError:
            QMessageBox.warning(self, "Error", "Pillow not installed.")
            return
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self, translator.get("te_extract_image"), "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        try:
            img = Image.open(path).convert("RGB").resize((150, 150))
            quantized = img.quantize(colors=6)
            palette_rgb = quantized.getpalette()[:18]
            colors = [QColor(palette_rgb[i * 3], palette_rgb[i * 3 + 1], palette_rgb[i * 3 + 2]) for i in range(6)]
            self._last_palette = colors
            for i, sw in enumerate(self._image_swatches):
                sw.set_color(colors[i])
            self._img_swatch_container.show()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _update_preview(self):
        if hasattr(self, "_preview_pane"):
            self._preview_pane.apply_theme(self.theme_data, self._colorblind_mode, self._preview_dark)

    def _toggle_preview_bg(self):
        self._preview_dark = not self._preview_dark
        if self._preview_dark:
            self._btn_bg_toggle.setText(translator.get("te_preview_light_bg"))
        else:
            self._btn_bg_toggle.setText(translator.get("te_preview_dark_bg"))
        self._update_preview()
