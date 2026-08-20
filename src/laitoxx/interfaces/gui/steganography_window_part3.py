"""Focused behavior slice for SteganographyWindow."""
# ruff: noqa: F405

from .steganography_window_context import *  # noqa: F403


class SteganographyWindowMixin3:
    def _process_st3gg(self):
        img_path = self.image_input.text().strip()
        mode = self.mode_combo.currentIndex()
        if not img_path or not os.path.isfile(img_path):
            QMessageBox.warning(self, translator.get("Error"), translator.get("Please select a valid cover image."))
            return
        password = self.password_input.text()
        if self.encryption_check.isChecked() and not password:
            QMessageBox.warning(self, translator.get("Error"), translator.get("Enter encryption password"))
            return
        try:
            if mode == 0:
                payload = self._payload_bytes()
                if not payload:
                    QMessageBox.warning(
                        self, translator.get("Error"), translator.get("Please enter a payload to hide.")
                    )
                    return
                save_path, _ = QFileDialog.getSaveFileName(
                    self, translator.get("Save Encoded Image"), "", translator.get("PNG Image (*.png)")
                )
                if not save_path:
                    return
                save_path = steganography_service.encode(
                    img_path,
                    save_path,
                    payload,
                    self._service_options(),
                    password if self.encryption_check.isChecked() else "",
                )
                self.encoded_image_path = save_path
                self._result_pixmap = QPixmap(save_path)
                self._set_preview_pixmap(self.result_lbl, self._result_pixmap)
                self.result_lbl.show()
                self.extracted_output.hide()
                self.preview_tabs.setCurrentWidget(self.result_page)
                QMessageBox.information(self, translator.get("Success"), translator.get("Data hidden successfully."))
            elif mode == 1:
                options = self._service_options()
                if options.method == AUTO_METHOD_ID:
                    self._start_auto_extraction(img_path, password)
                    return
                payload = steganography_service.decode(img_path, password, options)
                try:
                    output = payload.decode("utf-8")
                except UnicodeDecodeError:
                    output = payload.hex(" ")
                self.extracted_output.setPlainText(output)
                self.result_lbl.hide()
                self.extracted_output.show()
                self.preview_tabs.setCurrentWidget(self.result_page)
            elif mode == 2:
                self.extracted_output.setPlainText(steganography_service.analyze_json(img_path, password))
                self.result_lbl.hide()
                self.extracted_output.show()
                self.preview_tabs.setCurrentWidget(self.result_page)
            else:
                if os.path.splitext(img_path)[1].lower() != ".png":
                    raise ValueError(translator.get("Metadata injector requires a PNG image."))
                text = self.payload_input.toPlainText()
                if not text:
                    raise ValueError(translator.get("Please enter a payload to hide."))
                save_path, _ = QFileDialog.getSaveFileName(
                    self, translator.get("Save Encoded Image"), "", translator.get("PNG Image (*.png)")
                )
                if not save_path:
                    return
                save_path = steganography_service.inject_png_text(img_path, save_path, text)
                self._result_pixmap = QPixmap(save_path)
                self._set_preview_pixmap(self.result_lbl, self._result_pixmap)
                self.result_lbl.show()
                self.extracted_output.hide()
                self.preview_tabs.setCurrentWidget(self.result_page)
        except Exception as exc:
            traceback.print_exc()
            QMessageBox.critical(self, translator.get("Error"), str(exc))

    def _start_auto_extraction(self, image_path, password):
        if getattr(self, "_extraction_worker", None) and self._extraction_worker.isRunning():
            return
        self.process_btn.setEnabled(False)
        self.process_btn.setText(translator.get("Trying all methods..."))
        self.scan_progress_bar.setRange(0, 0)
        self.scan_progress_bar.setFormat(translator.get("Preparing scan..."))
        self.scan_progress_bar.show()
        self.extracted_output.setPlainText(translator.get("Scanning method and parameter combinations..."))
        self.result_lbl.hide()
        self.extracted_output.show()
        self.preview_tabs.setCurrentWidget(self.result_page)
        self._extraction_worker = ExtractionScanWorker(image_path, password, self)
        self._extraction_worker.completed.connect(self._show_auto_extraction)
        self._extraction_worker.failed.connect(self._auto_extraction_failed)
        self._extraction_worker.progress.connect(self._update_auto_extraction_progress)
        self._extraction_worker.finished.connect(self._auto_extraction_finished)
        self._extraction_worker.start()

    def _update_auto_extraction_progress(self, current, total, label):
        self.scan_progress_bar.setRange(0, total)
        self.scan_progress_bar.setValue(current)
        self.scan_progress_bar.setFormat(f"{current} / {total} · {label}")

    def _show_auto_extraction(self, report):
        if report["matches"]:
            output = __import__("json").dumps(report, ensure_ascii=False, indent=2)
        else:
            skipped = "; ".join(f"{item['method']}: {item['reason']}" for item in report["skipped"])
            output = f"No validated hidden data found after {report['attempted']} attempts.\nSkipped: {skipped}"
        self.extracted_output.setPlainText(output)

    def _auto_extraction_failed(self, message):
        self.extracted_output.setPlainText(message)

    def _auto_extraction_finished(self):
        self._extraction_worker.deleteLater()
        self._extraction_worker = None
        self.scan_progress_bar.hide()
        self._on_mode_changed()

    def closeEvent(self, event):
        worker = getattr(self, "_extraction_worker", None)
        if worker and worker.isRunning():
            worker.completed.disconnect()
            worker.failed.disconnect()
            stop_and_detach_thread(worker)
            self._extraction_worker = None
        super().closeEvent(event)

    def _btn_style(self, color):
        return f"""
            QPushButton#ProcessButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
            }}
            QPushButton#ProcessButton:hover {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color}, stop:1 #ffffff);
                color: black;
            }}
            QPushButton#ProcessButton:disabled {{
                background-color: rgba(255, 255, 255, 0.09);
                color: rgba(255, 255, 255, 0.35);
            }}
        """

    def update_theme(self, theme_data=None):
        if theme_data is not None:
            self.theme_data = theme_data
        td = resolved_theme(self.theme_data)
        if not td:
            return

        bg = td["surface_base_color"]
        panel = td["surface_raised_color"]
        field = td["surface_input_color"]
        work = td["surface_work_color"]
        text_color = td["text_primary_color"]
        secondary = td["text_secondary_color"]
        subtle_border = td["border_subtle_color"]
        strong_border = td["border_strong_color"]
        soft_accent = td["accent_soft_color"]
        accent = td.get("accent_color", "#4CAF50")
        font_family = td.get("font_family", "Segoe UI")
        font_size = int(td.get("font_size", 13))

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {text_color};
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: {font_size}px;
            }}
            QFrame#ModernCard {{
                background-color: {panel};
                border-radius: 12px;
                border: 1px solid {subtle_border};
            }}
            QLabel {{
                color: {text_color};
                border: none;
                background: transparent;
            }}
            QLabel#ConstraintsLabel {{
                background-color: {work};
                border-radius: 8px;
                padding: 10px;
                border: 1px solid {subtle_border};
                font-size: 13px;
                line-height: 1.5;
            }}
            QLabel#PreviewArea {{
                background-color: {work};
                border: 1px dashed {strong_border};
                border-radius: 10px;
                color: {secondary};
                font-size: 13px;
            }}
            QLabel#PreviewArea[dragActive="true"] {{
                background-color: {soft_accent};
                border: 1px solid {accent};
                color: {text_color};
            }}
            QLabel#RecommendationLabel {{
                background-color: {field};
                border-left: 3px solid {accent};
                border-radius: 5px;
                padding: 7px 9px;
                color: {secondary};
                font-size: 11px;
            }}
            QTextEdit, QLineEdit, QComboBox {{
                background-color: {field};
                color: {text_color};
                border: 1px solid {subtle_border};
                border-radius: 6px;
                padding: 7px;
                font-size: 12px;
            }}
            QTextEdit:focus, QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {accent};
                background-color: {work};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QPushButton {{
                background-color: {accent};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 5px 11px;
                min-height: 28px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
            QPushButton#SecondaryButton {{
                background-color: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.12);
                padding: 7px 9px;
            }}
            QPushButton#SecondaryButton:hover {{
                border-color: {accent};
                background-color: rgba(255,255,255,0.13);
            }}
            QPushButton#SecondaryButton:disabled {{
                color: rgba(255,255,255,0.3);
                background-color: rgba(255,255,255,0.035);
            }}
            QSplitter::handle {{
                background-color: transparent;
            }}
            QTabWidget::pane {{
                border: none;
                background: transparent;
                top: -1px;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {secondary};
                border: none;
                border-bottom: 2px solid transparent;
                padding: 7px 14px;
                margin-right: 4px;
                font-size: 12px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                color: {text_color};
                border-bottom: 2px solid {accent};
            }}
            QTabBar::tab:hover {{ color: {text_color}; }}
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: transparent; width: 7px; margin: 2px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {strong_border}; border-radius: 3px; min-height: 28px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        self.setStyleSheet(self.styleSheet() + build_workspace_qss(td))
        self._update_capacity()
        # Preserve the blue extract action when themes are reapplied.
        self._on_mode_changed()
