from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.features.osint.advanced_web_scanner.catalog import PROVIDERS
from laitoxx.features.osint.advanced_web_scanner.configuration import (
    configuration_errors,
    load_configuration,
    save_configuration,
)
from laitoxx.features.osint.advanced_web_scanner.quota import ledger
from laitoxx.features.osint.intelligence.cache import cache


class AdvancedWebScannerSettingsDialog(QDialog):
    def __init__(self, parent=None, theme_data=None):
        super().__init__(parent)
        self._theme = theme_data or {}
        self.setWindowTitle(translator.get("aws_api_quota_title"))
        self.resize(980, 650)
        self._config = load_configuration()
        self._rows = {}
        layout = QVBoxLayout(self)
        note = QLabel(translator.get("aws_api_quota_note"))
        note.setWordWrap(True)
        layout.addWidget(note)
        summary_row = QHBoxLayout()
        active_count = sum(
            spec.mandatory or self._config["providers"][spec.id].get("enabled", False) for spec in PROVIDERS
        )
        exhausted_count = sum(ledger.status(spec.id).exhausted for spec in PROVIDERS)
        summary = QLabel(
            translator.get(
                "aws_settings_summary",
                active=active_count,
                required=sum(spec.mandatory for spec in PROVIDERS),
                exhausted=exhausted_count,
            )
        )
        summary.setObjectName("settingsSummary")
        summary_row.addWidget(summary)
        summary_row.addStretch()
        self.reveal_keys = QCheckBox(translator.get("aws_reveal_keys"))
        self.reveal_keys.toggled.connect(self._toggle_key_visibility)
        summary_row.addWidget(self.reveal_keys)
        layout.addLayout(summary_row)
        enrichment_group = QGroupBox(translator.get("aws_enrichment_options"))
        enrichment_layout = QGridLayout(enrichment_group)
        enrichment_items = (
            ("dns_consensus", "aws_enrichment_dns_consensus"),
            ("dns_security_posture", "aws_enrichment_dns_security"),
            ("dns_misconfiguration", "aws_enrichment_dns_misconfiguration"),
            ("scope_classifier", "aws_enrichment_scope"),
            ("evidence_freshness", "aws_enrichment_freshness"),
            ("routing_rpki", "aws_enrichment_routing"),
            ("technology_identity", "aws_enrichment_technology"),
            ("http_tls_posture", "aws_enrichment_http_tls"),
            ("archive_analysis", "aws_enrichment_archive"),
        )
        self._enrichment_boxes = {}
        for index, (option, translation_key) in enumerate(enrichment_items):
            checkbox = QCheckBox(translator.get(translation_key))
            checkbox.setChecked(bool(self._config.get("enrichments", {}).get(option, True)))
            enrichment_layout.addWidget(checkbox, index // 3, index % 3)
            self._enrichment_boxes[option] = checkbox
        layout.addWidget(enrichment_group)
        self.table = QTableWidget(len(PROVIDERS), 6)
        self.table.setHorizontalHeaderLabels(
            [
                translator.get("aws_use"),
                translator.get("aws_source"),
                translator.get("aws_tier"),
                translator.get("aws_access"),
                translator.get("aws_key_token"),
                translator.get("aws_quota_status"),
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        self._populate()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.clear_cache_button = buttons.addButton(
            translator.get("aws_clear_scan_cache"),
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.clear_cache_button.clicked.connect(self._clear_scan_cache)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._apply_theme()

    def _toggle_key_visibility(self, visible: bool):
        mode = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        for _enabled, _access, key in self._rows.values():
            key.setEchoMode(mode)

    def _clear_scan_cache(self):
        answer = QMessageBox.question(
            self,
            translator.get("aws_clear_scan_cache_title"),
            translator.get("aws_clear_scan_cache_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        removed = cache.clear_namespace_prefix("advanced_web_scanner:")
        QMessageBox.information(
            self,
            translator.get("aws_clear_scan_cache_title"),
            translator.get("aws_clear_scan_cache_done", count=removed),
        )

    def _apply_theme(self):
        theme = self._theme
        bg = theme.get("window_bg_color", "#11131a")
        panel = theme.get("panel_bg_color", theme.get("text_area_bg_color", "#171a23"))
        field = theme.get("text_area_bg_color", "#171a23")
        text = theme.get("text_area_text_color", theme.get("title_text_color", "#edf2f4"))
        border = theme.get("text_area_border_color", theme.get("border_color", "#343a40"))
        button = theme.get("button_bg_color", "rgba(82,110,255,.28)")
        hover = theme.get("button_hover_bg_color", "rgba(82,110,255,.5)")
        button_text = theme.get("button_text_color", text)
        accent = theme.get("accent_color", "#526eff")
        scrollbar = theme.get("scrollbar_handle_color", accent)
        radius = int(theme.get("border_radius", 8))
        self.setStyleSheet(f"""
            QDialog {{ background: {bg}; color: {text}; }}
            QLabel {{ color: {text}; }}
            QLabel#settingsSummary {{ color: {accent}; font-weight: 700; }}
            QGroupBox {{ color: {text}; border: 1px solid {border}; border-radius: {radius}px; margin-top: 8px; padding: 10px 6px 6px 6px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; color: {accent}; font-weight: 700; }}
            QTableWidget, QLineEdit, QComboBox {{ background: {field}; color: {text}; border: 1px solid {border}; border-radius: {radius}px; }}
            QTableWidget {{ alternate-background-color: {panel}; gridline-color: {border}; }}
            QHeaderView::section {{ background: {panel}; color: {text}; border: none; padding: 6px; }}
            QPushButton {{ background: {button}; color: {button_text}; border: 1px solid {border}; border-radius: {radius}px; padding: 6px 12px; }}
            QPushButton:hover {{ background: {hover}; }}
            QCheckBox::indicator:checked {{ background: {accent}; border: 1px solid {accent}; }}
            QCheckBox {{ color: {text}; spacing: 6px; }}
            QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {border}; border-radius: 3px; background: {field}; }}
            QScrollBar:vertical {{ background: {field}; width: 10px; }}
            QScrollBar::handle:vertical {{ background: {scrollbar}; min-height: 24px; border-radius: 5px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

    def _populate(self):
        for row, spec in enumerate(PROVIDERS):
            values = self._config["providers"][spec.id]
            enabled = QCheckBox()
            enabled.setChecked(bool(values.get("enabled", True)))
            if spec.mandatory:
                enabled.setChecked(True)
                enabled.setEnabled(False)
            self.table.setCellWidget(row, 0, enabled)
            self.table.setItem(row, 1, QTableWidgetItem(spec.name))
            tier = QTableWidgetItem(translator.get("aws_required" if spec.mandatory else "aws_extended"))
            if spec.mandatory:
                tier.setForeground(Qt.GlobalColor.yellow)
            self.table.setItem(row, 2, tier)
            access = QComboBox()
            if not spec.key_name:
                access.addItem(translator.get("aws_anonymous"), "anonymous")
            elif spec.key_required:
                access.addItem(translator.get("aws_api_key"), "key")
            else:
                access.addItem(translator.get("aws_auto"), "auto")
                access.addItem(translator.get("aws_anonymous"), "anonymous")
                access.addItem(translator.get("aws_api_key"), "key")
            index = access.findData(values.get("auth_mode", "auto"))
            access.setCurrentIndex(max(0, index))
            self.table.setCellWidget(row, 3, access)
            key = QLineEdit(str(values.get("key", "")))
            key.setEchoMode(QLineEdit.EchoMode.Password)
            key.setPlaceholderText(spec.key_name or translator.get("aws_no_key_required"))
            key.setEnabled(bool(spec.key_name))
            self.table.setCellWidget(row, 4, key)
            status = ledger.status(spec.id)
            if spec.id == "shodan_account":
                quota_text = f"{status.mode} · {status.label}"
            elif status.remaining is None:
                quota_text = f"{status.mode} · {status.label}"
            else:
                quota_text = translator.get(
                    "aws_quota_value",
                    mode=status.mode,
                    remaining=status.remaining,
                    reset=self._short_time(status.reset_at),
                )
            quota = QTableWidgetItem(quota_text)
            if status.exhausted:
                quota.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 5, quota)
            self._rows[spec.id] = (enabled, access, key)

    @staticmethod
    def _short_time(value: str | None) -> str:
        return value.replace("T", " ")[:19] + " UTC" if value else "unknown"

    def _save(self):
        extended_missing = []
        for spec in PROVIDERS:
            enabled, access, key = self._rows[spec.id]
            is_enabled = True if spec.mandatory else enabled.isChecked()
            if is_enabled and not spec.mandatory and spec.key_required and not key.text().strip():
                is_enabled = False
                extended_missing.append(spec.name)
            self._config["providers"][spec.id] = {
                "enabled": is_enabled,
                "auth_mode": access.currentData(),
                "key": key.text().strip(),
            }
        self._config["configured"] = True
        self._config["enrichments"] = {
            option: checkbox.isChecked() for option, checkbox in self._enrichment_boxes.items()
        }
        errors = configuration_errors(self._config, "minimum")
        if errors:
            QMessageBox.warning(self, translator.get("aws_required_setup"), "\n".join(errors))
            return
        save_configuration(self._config)
        if extended_missing:
            QMessageBox.information(
                self,
                translator.get("aws_optional_apis"),
                translator.get("aws_disabled_until_key") + "\n" + "\n".join(extended_missing),
            )
        self.accept()
