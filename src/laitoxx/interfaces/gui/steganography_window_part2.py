"""Focused behavior slice for SteganographyWindow."""
# ruff: noqa: F405

from .steganography_window_context import *  # noqa: F403


class SteganographyWindowMixin2:
    def _on_mode_changed(self):
        is_hide = self.mode_combo.currentIndex() == 0
        is_analyze = self.mode_combo.currentIndex() == 2
        is_inject = self.mode_combo.currentIndex() == 3
        accepts_payload = is_hide or is_inject
        self.payload_input.setVisible(accepts_payload)
        self.payload_label.setVisible(accepts_payload)
        self.payload_file_input.setVisible(is_hide)
        self.payload_file_btn.setVisible(is_hide)
        self.capacity_container.setVisible(is_hide)
        self.password_container.setVisible(not is_inject)
        self.encryption_check.setVisible(is_hide)
        if is_hide:
            self._update_encryption_fields()
        else:
            self.password_label.show()
            self.password_input.show()
        self._populate_methods()

        if is_hide:
            self.process_btn.setText(translator.get("Hide Data"))
        elif not is_analyze:
            self.process_btn.setText(translator.get("Extract Data"))
        elif is_analyze:
            self.process_btn.setText(translator.get("Analyze"))
        else:
            self.process_btn.setText(translator.get("Inject metadata"))
        self.process_btn.setStyleSheet("")
        self.process_btn.setProperty("variant", "primary")
        if hasattr(self, "hide_mode_btn"):
            self.hide_mode_btn.setChecked(self.mode_combo.currentIndex() == 0)
            self.extract_mode_btn.setChecked(self.mode_combo.currentIndex() == 1)

        self._update_capacity()
        self._update_process_state()
        self._update_recommendation()

    def _select_mode(self, index):
        self.mode_combo.setCurrentIndex(index)

    def _on_method_changed(self):
        method_id = self._method_id()
        method = METHOD_BY_ID.get(method_id)
        if method:
            availability = f"\n{method.unavailable_reason}" if not method.available else ""
            password = "\nPassword required." if method.requires_password else ""
            self.constraints_lbl.setText(method.description + password + availability)
            if method.requires_password:
                self.password_label.show()
                self.password_input.show()
            if self.mode_combo.currentIndex() == 0:
                self.encryption_check.setEnabled(not method.requires_password)
                if method.requires_password:
                    self.encryption_check.setChecked(True)
        else:
            self.constraints_lbl.setText(translator.get("Tries every safe method and parameter combination."))
            self.encryption_check.setEnabled(True)
        self._update_method_control_visibility()
        self._update_capacity()
        self._update_recommendation()

    def _update_encryption_fields(self):
        enabled = self.encryption_check.isChecked()
        self.password_label.setVisible(enabled)
        self.password_input.setVisible(enabled)

    def _browse_payload_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, translator.get("Select File"), "", translator.get("All Files (*)")
        )
        if filepath:
            self.payload_file_input.setText(filepath)
            self.payload_input.clear()
            self._update_capacity()

    def _browse_image(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, translator.get("Select Cover Image"), "", translator.get("Images (*.png *.bmp *.jpg *.jpeg)")
        )
        if filepath:
            self._load_image(filepath)

    def _load_image(self, filepath):
        if not filepath or not os.path.isfile(filepath):
            return
        pixmap = QPixmap(filepath)
        if pixmap.isNull():
            QMessageBox.warning(self, translator.get("Error"), translator.get("Please select a valid cover image."))
            return
        self.image_input.setText(filepath)
        self.current_image_path = filepath
        self._original_pixmap = pixmap
        self._set_preview_pixmap(self.original_lbl, pixmap)
        self.original_lbl.setText("")
        self.preview_tabs.setCurrentWidget(self.original_lbl)
        self._update_capacity()
        self._update_recommendation()

    def _recommended_method(self):
        path = self.image_input.text().strip()
        if not path:
            return None, ""
        payload_size = len(self.payload_input.toPlainText().encode("utf-8"))
        if payload_size > 32_000:
            return "SPREAD", translator.get("Spreads a large payload across the carrier.")
        return "LSB", translator.get("Balanced capacity and visual quality.")

    def _update_recommendation(self):
        if not hasattr(self, "recommendation_container"):
            return
        method, reason = self._recommended_method()
        self._recommended_method_name = method
        visible = bool(method) and self.mode_combo.currentIndex() == 0
        self.recommendation_container.setVisible(visible)
        if visible:
            self.recommendation_lbl.setText(translator.get("Recommended") + f": {method}\n" + reason)
            self.apply_recommendation_btn.setEnabled(self._method_id() != method)

    def _apply_recommended_method(self):
        method = getattr(self, "_recommended_method_name", None)
        if method:
            index = self.method_combo.findData(method)
            if index >= 0:
                self.method_combo.setCurrentIndex(index)
            self.apply_recommendation_btn.setEnabled(False)

    def _update_process_state(self):
        has_image = bool(self.image_input.text().strip())
        self.process_btn.setEnabled(has_image)
        self.process_btn.setToolTip("" if has_image else translator.get("Select cover image..."))

    def _set_preview_pixmap(self, label, pixmap):
        if pixmap and not pixmap.isNull():
            target = label.size() - QSize(24, 24)
            label.setPixmap(
                pixmap.scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_original_pixmap"):
            self._set_preview_pixmap(self.original_lbl, self._original_pixmap)
        if hasattr(self, "_result_pixmap"):
            self._set_preview_pixmap(self.result_lbl, self._result_pixmap)

    def _update_capacity(self):
        is_hide = self.mode_combo.currentIndex() == 0
        if not is_hide:
            return

        payload = self._payload_bytes()
        used_bytes = len(payload)
        max_bytes = 0
        img_path = self.image_input.text().strip()
        if os.path.isfile(img_path):
            try:
                max_bytes = steganography_service.capacity(img_path, self._service_options())
            except (OSError, ValueError, KeyError):
                max_bytes = 0
        self.capacity_bar.setMaximum(max(max_bytes, 1))
        self.capacity_bar.setValue(min(used_bytes, max(max_bytes, 1)))
        self.capacity_bar.setFormat(f"{used_bytes} / {max_bytes} bytes")
        self.capacity_bar.setProperty("overflow", bool(max_bytes and used_bytes > max_bytes))
        self.capacity_bar.style().unpolish(self.capacity_bar)
        self.capacity_bar.style().polish(self.capacity_bar)

    def _process_stego(self):
        self._process_st3gg()
        return

    def _payload_bytes(self):
        payload_file = self.payload_file_input.text().strip() if hasattr(self, "payload_file_input") else ""
        if payload_file and os.path.isfile(payload_file):
            with open(payload_file, "rb") as stream:
                return stream.read()
        return self.payload_input.toPlainText().encode("utf-8")

    def _st3gg_config(self):
        return create_config(
            channels=self.channel_combo.currentText(),
            bits=self.bits_spin.value(),
            compress=self.compression_check.isChecked(),
            strategy=self.strategy_combo.currentText(),
        )

    def _service_options(self):
        return StegOptions(
            method=self._method_id(),
            channels=self.channel_combo.currentText(),
            bits=self.bits_spin.value(),
            compress=self.compression_check.isChecked(),
            strategy=self.strategy_combo.currentText(),
            robustness=self.robustness_combo.currentText(),
            pvd_direction=self.pvd_direction_combo.currentText(),
            pvd_range=self.pvd_range_combo.currentText(),
            palette_colors=int(self.palette_colors_combo.currentData()),
            png_keyword=self.png_keyword_input.text().strip() or "stEg",
        )
