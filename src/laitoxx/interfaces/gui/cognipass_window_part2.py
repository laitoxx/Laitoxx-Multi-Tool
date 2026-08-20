"""Focused behavior slice for CogniPassWindow."""
# ruff: noqa: F405

from .cognipass_window_context import *  # noqa: F403


class CogniPassWindowMixin2:
    def _start(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        if not self.output_path.text().strip():
            self._browse_output()
            if not self.output_path.text().strip():
                return
        output = Path(self.output_path.text().strip()).expanduser()
        if output.exists():
            answer = QMessageBox.question(
                self,
                _t("cognipass_replace_title", "Replace dictionary?"),
                _t(
                    "cognipass_replace_text",
                    "The selected file already exists. Replace it after generation?",
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._last_result = None
        self.generate_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.open_folder_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.status.setText(_t("cognipass_running", "Generating candidates locally…"))
        self._worker = _CogniPassWorker(self._profile())
        self._worker.completed.connect(self._completed)
        self._worker.failed.connect(self._failed)
        self._worker.cancelled.connect(self._cancelled)
        self._worker.start()

    def _cancel(self) -> None:
        if self._worker:
            self._worker.cancel()
            self.status.setText(_t("cognipass_stopping", "Stopping…"))

    def _reset_running_state(self) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.generate_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def _completed(self, result: CogniPassResult) -> None:
        self._reset_running_state()
        self._last_result = result
        size_kib = result.file_size / 1024
        self.status.setToolTip(result.process_output.strip())
        self.status.setText(
            _t(
                "cognipass_complete",
                "Generated {count} unique candidates · {size:.1f} KiB",
                count=result.line_count,
                size=size_kib,
            )
        )
        self.open_folder_button.setEnabled(True)

    def _failed(self, error: object) -> None:
        self._reset_running_state()
        self.status.setText(_t("cognipass_failed", "Generation failed"))
        QMessageBox.critical(
            self,
            _t("cognipass_title", "CogniPass"),
            external_tool_message(error),
        )

    def _cancelled(self) -> None:
        self._reset_running_state()
        self.status.setText(_t("cognipass_cancelled", "Generation cancelled"))

    def _open_folder(self) -> None:
        if self._last_result:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_result.output_path.parent)))

    def update_theme(self, theme_data: dict | None = None) -> None:
        if theme_data is not None:
            self.theme_data = theme_data
        theme = resolved_theme(self.theme_data)
        self.setStyleSheet(
            build_workspace_qss(theme)
            + f"""
            QPushButton#AdditionalToggle {{
                background: transparent;
                color: {theme["text_secondary_color"]};
                border: none;
                padding: 5px 2px;
                text-align: left;
                font-weight: 600;
            }}
            QPushButton#AdditionalToggle:hover {{
                color: {theme["accent_color"]};
            }}
            """
        )

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(2500)
        super().closeEvent(event)
