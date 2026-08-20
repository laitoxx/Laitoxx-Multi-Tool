"""Focused behavior slice for AdvancedWebScannerWindow."""
# ruff: noqa: F405

from .advanced_web_scanner_window_context import *  # noqa: F403


class AdvancedWebScannerWindowMixin2:
    def _apply_style(self):
        self.theme_data = resolved_theme(self.theme_data)
        bg = self.theme_data["surface_base_color"]
        fg = self.theme_data["text_primary_color"]
        secondary = self.theme_data["text_secondary_color"]
        border = self.theme_data["border_subtle_color"]
        field = self.theme_data["surface_input_color"]
        panel = self.theme_data["surface_raised_color"]
        accent = self.theme_data.get("accent_color", "#526eff")
        warning_color = self.theme_data.get("warning_color", "#f9c74f")
        button = self.theme_data.get("button_bg_color", "rgba(82, 110, 255, 0.28)")
        button_hover = self.theme_data.get("button_hover_bg_color", "rgba(82, 110, 255, 0.5)")
        button_pressed = self.theme_data.get("button_pressed_bg_color", button_hover)
        button_border = self.theme_data.get("button_border_color", border)
        button_text = self.theme_data.get("button_text_color", fg)
        scrollbar = self.theme_data.get("scrollbar_handle_color", accent)
        scrollbar_hover = self.theme_data.get("scrollbar_handle_hover_color", scrollbar)
        radius = int(self.theme_data.get("border_radius", 8))
        font_family = self.theme_data.get("font_family", "Segoe UI")
        font_size = int(self.theme_data.get("font_size", 13))
        self.setStyleSheet(f"""
            QDialog {{ background: {bg}; color: {fg}; font-family: '{font_family}'; font-size: {font_size}px; }}
            QLabel {{ color: {fg}; }}
            QLabel#pageTitle {{ font-size: 22px; font-weight: 700; color: {fg}; }}
            QLabel#secondaryText, QLabel#metricCaption {{ color: {secondary}; }}
            QLabel#warningText {{ color: {warning_color}; background: {panel}; border: 1px solid {warning_color}; border-radius: {radius}px; padding: 7px 10px; }}
            QLabel#metricCaption {{ font-size: 11px; }}
            QLabel#metricValue {{ font-size: 18px; font-weight: 700; color: {fg}; }}
            QFrame#queryPanel, QFrame#metricCard {{ background: {panel}; border: 1px solid {border}; border-radius: {radius}px; }}
            QLineEdit, QComboBox, QTextEdit, QTreeWidget, QTableWidget {{
                background: {field}; color: {fg}; border: 1px solid {border}; border-radius: {radius}px; padding: 6px;
            }}
            QPushButton {{ background: {button}; color: {button_text}; border: 1px solid {button_border}; border-radius: {radius}px; padding: 4px 10px; min-height: 28px; }}
            QPushButton:hover {{ background: {button_hover}; }}
            QPushButton:pressed {{ background: {button_pressed}; }}
            QPushButton#primaryButton {{ background: {accent}; color: {button_text}; font-weight: 700; padding-left: 18px; padding-right: 18px; }}
            QPushButton:disabled {{ color: #6c757d; background: rgba(50,50,50,0.15); }}
            QTabWidget::pane {{ background: {panel}; border: 1px solid {border}; border-radius: {radius}px; }}
            QTabBar::tab:selected {{ color: {accent}; background: {panel}; border-bottom: 2px solid {accent}; }}
            QTabBar::tab:hover {{ color: {fg}; }}
            QTabBar::tab {{ color: {secondary}; padding: 8px 12px; }}
            QHeaderView::section {{ background: {panel}; color: {fg}; border: none; padding: 5px; }}
            QProgressBar {{ background: {field}; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{ background: {accent}; border-radius: 3px; }}
            QCheckBox {{ color: {secondary}; spacing: 6px; }}
            QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {border}; border-radius: 3px; background: {field}; }}
            QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
            QSplitter::handle {{ background: {border}; }}
            QScrollBar:vertical {{ background: {field}; width: 10px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: {scrollbar}; min-height: 24px; border-radius: 5px; }}
            QScrollBar::handle:vertical:hover {{ background: {scrollbar_hover}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal {{ background: {field}; height: 10px; margin: 0; }}
            QScrollBar::handle:horizontal {{ background: {scrollbar}; min-width: 24px; border-radius: 5px; }}
            QToolTip {{ background: {panel}; color: {fg}; border: 1px solid {border}; padding: 5px; }}
        """)
        self.setStyleSheet(self.styleSheet() + build_workspace_qss(self.theme_data))
        if hasattr(self, "graph_editor"):
            self.graph_editor.update_theme(self.theme_data)

    def update_theme(self, theme_data: dict):
        self.theme_data = theme_data or {}
        self._apply_style()

    def _update_scan_warning(self, *_):
        if not hasattr(self, "scan_warning"):
            return
        messages = []
        depth = self.depth_spin.value()
        if depth >= 4:
            messages.append(translator.get("aws_depth_warning", depth=depth))
        if self.active_scan_checkbox.isChecked():
            config = load_configuration()
            enabled = [
                name
                for provider_id, name in (("naabu", "Naabu"), ("nuclei", "Nuclei"))
                if config.get("providers", {}).get(provider_id, {}).get("enabled", True)
            ]
            if enabled:
                messages.append(
                    translator.get(
                        "aws_active_scanner_inline_warning",
                        scanners=" & ".join(enabled),
                    )
                )
        self.scan_warning.setText("\n".join(messages))
        self.scan_warning.setVisible(bool(messages))

    def _on_active_scan_toggled(self, checked: bool):
        self._update_scan_warning()
        if checked:
            self._show_active_scanner_warning(load_configuration())

    def _show_active_scanner_warning(self, config: dict):
        if self._active_scanner_warning_shown:
            return
        enabled = [
            name
            for provider_id, name in (("naabu", "Naabu"), ("nuclei", "Nuclei"))
            if config.get("providers", {}).get(provider_id, {}).get("enabled", True)
        ]
        if not enabled:
            return
        self._active_scanner_warning_shown = True
        QMessageBox.warning(
            self,
            translator.get("aws_active_scanner_av_title"),
            translator.get("aws_active_scanner_av_text", scanners=" & ".join(enabled)),
        )

    def _start_scan(self):
        target = self.target_input.text().strip()
        if not target or (self._thread and self._thread.isRunning()):
            return
        if self.depth_spin.value() >= 4:
            message = translator.get("aws_depth_confirm_text", depth=self.depth_spin.value())
            if self.active_scan_checkbox.isChecked():
                message += "\n\n" + translator.get("aws_depth_active_suffix")
            answer = QMessageBox.question(
                self,
                translator.get("aws_depth_confirm_title"),
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        if self.active_scan_checkbox.isChecked():
            answer = QMessageBox.question(
                self,
                translator.get("aws_active_confirm_title"),
                translator.get("aws_active_confirm_text", target=target),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        config = load_configuration()
        errors = configuration_errors(config, self.profile_combo.currentData())
        if errors:
            if not AdvancedWebScannerSettingsDialog(self, self.theme_data).exec():
                return
            config = load_configuration()
            errors = configuration_errors(config, self.profile_combo.currentData())
            if errors:
                QMessageBox.warning(self, translator.get("aws_required_setup"), "\n".join(errors))
                return
        if self.active_scan_checkbox.isChecked():
            self._show_active_scanner_warning(config)
        options = ScanOptions(
            profile=self.profile_combo.currentData(),
            dns_mode=self.dns_combo.currentData(),
            max_depth=self.depth_spin.value(),
            active_scanning=self.active_scan_checkbox.isChecked(),
            provider_config=config,
        )
        self._reset_results()
        self.scan_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.status_label.setText(translator.get("aws_scanning"))
        self._thread = _ScanThread(target, options)
        self._thread.provider_done.connect(self._on_provider_done)
        self._thread.completed.connect(self._on_scan_complete)
        self._thread.failed.connect(self._on_scan_failed)
        self._thread.start()

    def _configure_api_keys(self):
        AdvancedWebScannerSettingsDialog(self, self.theme_data).exec()
        self._refresh_quotas()
        self._update_scan_warning()

    def _reset_results(self):
        self.report = None
        self.sources_tree.clear()
        self.source_details.clear()
        self.overview.clear()
        self.raw_output.clear()
        self.timeline_table.setRowCount(0)
        self.graph_editor.set_graph(Graph(name=translator.get("ge_new_graph_name")))
        self.graph_projection_notice.clear()
        self.vulnerability_badge.setText(translator.get("aws_vulnerabilities_count", count=0))
        self.export_button.setEnabled(False)
        self.graph_button.setEnabled(False)
        for value in (
            self.coverage_value,
            self.entities_value,
            self.relations_value,
            self.vulnerabilities_value,
            self.risk_label,
        ):
            value.setText("-")

    def _on_provider_done(self, name, result):
        self.status_label.setText(
            f"{translator.get('aws_scanning')} · {name}: {translator.get(f'aws_status_{result.status}')}"
        )
        self._refresh_quotas()

    def _on_scan_failed(self, message):
        self.scan_button.setEnabled(True)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.status_label.setText(translator.get("aws_failed"))
        self._thread = None
        QMessageBox.warning(self, translator.get("Advanced Web Scanner"), message)

    def _on_scan_complete(self, report):
        self.report = report
        self.scan_button.setEnabled(True)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.status_label.setText(translator.get("aws_complete"))
        self._thread = None
        self.export_button.setEnabled(True)
        self.graph_button.setEnabled(True)
        self._populate_report()

    def _populate_report(self):
        report = self.report
        color = {"low": "#52b788", "medium": "#f9c74f", "high": "#f9844a", "critical": "#f94144"}.get(
            report.risk_level, "#adb5bd"
        )
        ok = sum(item.status in {"ok", "cached"} for item in report.providers)
        failed = sum(item.status == "error" for item in report.providers)
        skipped = sum(item.status == "skipped" for item in report.providers)
        limited = sum(item.status == "rate_limited" for item in report.providers)
        unavailable = sum(
            item.status in {"unavailable", "no_data", "restricted", "auth_error"} for item in report.providers
        )
        cve_count = sum(entity.kind == "cve" for entity in report.entities)
        self.coverage_value.setText(f"{ok}/{len(report.providers)}")
        self.entities_value.setText(str(len(report.entities)))
        self.relations_value.setText(str(len(report.relations)))
        self.vulnerabilities_value.setText(str(cve_count))
        self.risk_label.setText(
            f"<span style='color:{color}'>{report.risk_score:.1f} · {report.risk_level.upper()}</span>"
        )
        coverage_text = translator.get(
            "aws_overview_coverage",
            ok=ok,
            failed=failed,
            limited=limited,
            unavailable=unavailable + skipped,
        )
        entity_text = translator.get(
            "aws_overview_entities",
            entities=len(report.entities),
            relations=len(report.relations),
            events=len(report.timeline),
        )
        risk_items = "".join(
            f"<li><b>+{factor.points:.1f} {escape(factor.label)}</b><br>{escape(factor.evidence)}</li>"
            for factor in report.risk_factors
        )
        self.overview.setHtml(
            f"<h2>{escape(report.target.value)}</h2><p>{escape(coverage_text)}</p><p>{escape(entity_text)}</p>"
            f"<h3>{escape(translator.get('aws_risk_factors'))}</h3><ul>{risk_items}</ul>"
            f"<p><i>{escape(translator.get('aws_history_warning'))}</i></p>"
        )
        self.vulnerability_badge.setText(translator.get("aws_vulnerabilities_count", count=cve_count))
        self._load_graph_projection()
        self._populate_timeline()
        self._populate_sources()
        self.raw_output.setPlainText(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=str))

    def _populate_timeline(self):
        self.timeline_table.setRowCount(len(self.report.timeline))
        for row, event in enumerate(self.report.timeline):
            values = (
                event.event_time,
                event.observed_at,
                event.source,
                event.relation,
                event.subject,
                event.object,
                event.confidence,
            )
            for column, value in enumerate(values):
                self.timeline_table.setItem(row, column, QTableWidgetItem(str(value)))

    def _populate_sources(self):
        self.sources_tree.clear()
        for index, result in enumerate(self.report.providers):
            item = QTreeWidgetItem(
                [
                    result.name,
                    translator.get(f"aws_status_{result.status}"),
                    f"{result.duration_ms} ms",
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, index)
            status_color = {
                "ok": "#52b788",
                "cached": "#74c0fc",
                "no_data": "#adb5bd",
                "rate_limited": "#f9c74f",
                "unavailable": "#f9844a",
                "skipped": "#adb5bd",
                "error": "#f94144",
                "restricted": "#f9844a",
                "auth_error": "#f94144",
            }.get(result.status, "#adb5bd")
            item.setForeground(1, QBrush(QColor(status_color)))
            if result.error:
                QTreeWidgetItem(item, [result.error])
            self.sources_tree.addTopLevelItem(item)
        self.sources_tree.resizeColumnToContents(0)
