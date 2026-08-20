"""Masscan discovery and service fingerprinting workspace."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.core.settings.paths import REPORTS_DIR, TOOLS_DIR
from laitoxx.features.network.masscan_scanner import MasscanOptions, MasscanReport, MasscanRunner
from laitoxx.features.network.masscan_scanner.installer import install_masscan
from laitoxx.features.network.masscan_scanner.scanner import find_masscan
from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme
from laitoxx.interfaces.gui.external_tool_messages import external_tool_message
from laitoxx.interfaces.gui.worker import stop_and_detach_thread


def _t(key: str, **kwargs) -> str:
    return translator.get(key, **kwargs)


class _ScanThread(QThread):
    progress = pyqtSignal(float, str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(object)
    cancelled = pyqtSignal()

    def __init__(self, target: str, options: MasscanOptions, parent=None):
        super().__init__(parent)
        self.target = target
        self.options = options
        self.runner = MasscanRunner()
        self.stop_event = threading.Event()

    def cancel(self) -> None:
        self.stop_event.set()
        self.runner.cancel()

    def run(self) -> None:
        try:
            report = self.runner.scan(
                self.target,
                self.options,
                progress=lambda percent, message: self.progress.emit(percent, message),
                cancelled=self.stop_event.is_set,
            )
            if self.stop_event.is_set():
                self.cancelled.emit()
            else:
                self.completed.emit(report)
        except Exception as exc:
            if self.stop_event.is_set():
                self.cancelled.emit()
            else:
                self.failed.emit(exc)


class _InstallThread(QThread):
    progress = pyqtSignal(str)
    completed = pyqtSignal(str)
    failed = pyqtSignal(object)

    def run(self) -> None:
        try:
            target = install_masscan(TOOLS_DIR, self.progress.emit)
            self.completed.emit(str(target))
        except Exception as exc:
            self.failed.emit(exc)


class MasscanWindow(QDialog):
    def __init__(self, parent=None, theme_data: dict | None = None):
        super().__init__(parent)
        self.theme_data = resolved_theme(theme_data or {})
        self.report: MasscanReport | None = None
        self._scan_thread: _ScanThread | None = None
        self._install_thread: _InstallThread | None = None
        self.setWindowTitle(_t("Masscan Scanner"))
        self.setMinimumSize(1040, 680)
        self.resize(1320, 820)
        self._build_ui()
        self._apply_style()
        self._refresh_runtime()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)
        title = QLabel(_t("Masscan Scanner"))
        title.setObjectName("PageTitle")
        root.addWidget(title)
        subtitle = QLabel(_t("masscan_subtitle"))
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        runtime_panel = QFrame()
        runtime_panel.setObjectName("PanelSurface")
        runtime_row = QHBoxLayout(runtime_panel)
        self.runtime_status = QLabel()
        self.runtime_status.setObjectName("Muted")
        runtime_row.addWidget(self.runtime_status, 1)
        self.install_button = QPushButton(_t("masscan_install"))
        self.install_button.clicked.connect(self._install)
        runtime_row.addWidget(self.install_button)
        root.addWidget(runtime_panel)

        query_panel = QFrame()
        query_panel.setObjectName("PanelSurface")
        query = QVBoxLayout(query_panel)
        first = QHBoxLayout()
        self.target = QLineEdit()
        self.target.setPlaceholderText(_t("masscan_target_placeholder"))
        first.addWidget(self.target, 2)
        self.ports = QLineEdit(MasscanOptions().ports)
        self.ports.setPlaceholderText(_t("masscan_ports_placeholder"))
        first.addWidget(self.ports, 3)
        self.rate = QSpinBox()
        self.rate.setRange(1, 10_000)
        self.rate.setValue(500)
        self.rate.setSuffix(" pps")
        first.addWidget(self.rate)
        query.addLayout(first)
        second = QHBoxLayout()
        self.banners = QCheckBox(_t("masscan_banners"))
        self.banners.setChecked(True)
        second.addWidget(self.banners)
        self.authorization = QCheckBox(_t("masscan_authorization"))
        second.addWidget(self.authorization, 1)
        self.start_button = QPushButton(_t("masscan_start"))
        self.start_button.setProperty("variant", "primary")
        self.start_button.clicked.connect(self._start)
        second.addWidget(self.start_button)
        self.cancel_button = QPushButton(_t("masscan_cancel"))
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel)
        second.addWidget(self.cancel_button)
        query.addLayout(second)
        root.addWidget(query_panel)

        status_row = QHBoxLayout()
        self.status = QLabel(_t("masscan_ready"))
        self.status.setObjectName("Muted")
        status_row.addWidget(self.status, 1)
        self.result_count = QLabel("0")
        status_row.addWidget(self.result_count)
        root.addLayout(status_row)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        root.addWidget(self.progress)

        self.tabs = QTabWidget()
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                _t("masscan_col_host"),
                _t("masscan_col_port"),
                _t("masscan_col_protocol"),
                _t("masscan_col_service"),
                _t("masscan_col_product"),
                _t("masscan_col_version"),
                _t("masscan_col_confidence"),
                _t("masscan_col_banner"),
            ]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.tabs.addTab(self.table, _t("masscan_results"))
        self.raw = QTextEdit()
        self.raw.setReadOnly(True)
        self.tabs.addTab(self.raw, "JSON")
        root.addWidget(self.tabs, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        self.export_button = QPushButton(_t("masscan_export"))
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export)
        actions.addWidget(self.export_button)
        root.addLayout(actions)

    def _apply_style(self) -> None:
        self.setStyleSheet(build_workspace_qss(self.theme_data))

    def update_theme(self, theme_data: dict) -> None:
        self.theme_data = resolved_theme(theme_data or {})
        self._apply_style()

    def _refresh_runtime(self) -> None:
        executable = find_masscan()
        self.runtime_status.setText(
            _t("masscan_runtime_found", path=executable) if executable else _t("masscan_runtime_missing")
        )
        self.start_button.setEnabled(bool(executable) and not self._scan_thread)

    def _install(self) -> None:
        if self._install_thread and self._install_thread.isRunning():
            return
        answer = QMessageBox.question(
            self,
            _t("masscan_install_title"),
            _t("masscan_install_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.install_button.setEnabled(False)
        self.status.setText(_t("masscan_installing"))
        self._install_thread = _InstallThread(self)
        self._install_thread.progress.connect(self.status.setText)
        self._install_thread.completed.connect(self._installed)
        self._install_thread.failed.connect(self._install_failed)
        self._install_thread.start()

    def _installed(self, path: str) -> None:
        self._install_thread = None
        self.install_button.setEnabled(True)
        self.status.setText(_t("masscan_installed", path=path))
        self._refresh_runtime()

    def _install_failed(self, error: object) -> None:
        self._install_thread = None
        self.install_button.setEnabled(True)
        self.status.setText(_t("masscan_install_failed"))
        QMessageBox.warning(self, _t("Masscan Scanner"), external_tool_message(error))

    def _start(self) -> None:
        if self._scan_thread and self._scan_thread.isRunning():
            return
        if not self.authorization.isChecked():
            QMessageBox.warning(self, _t("Masscan Scanner"), _t("masscan_authorization_required"))
            return
        target = self.target.text().strip()
        if not target:
            return
        self.report = None
        self.table.setRowCount(0)
        self.raw.clear()
        self.export_button.setEnabled(False)
        self.progress.setValue(0)
        options = MasscanOptions(
            ports=self.ports.text().strip(), rate=self.rate.value(), banners=self.banners.isChecked()
        )
        self._scan_thread = _ScanThread(target, options, self)
        self._scan_thread.progress.connect(self._scan_progress)
        self._scan_thread.completed.connect(self._completed)
        self._scan_thread.failed.connect(self._failed)
        self._scan_thread.cancelled.connect(self._cancelled)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText(_t("masscan_running"))
        self._scan_thread.start()

    def _scan_progress(self, percent: float, message: str) -> None:
        self.progress.setValue(max(0, min(100, round(percent))))
        self.status.setText(message)

    def _cancel(self) -> None:
        if self._scan_thread and self._scan_thread.isRunning():
            self.cancel_button.setEnabled(False)
            self.status.setText(_t("masscan_cancelling"))
            self._scan_thread.cancel()

    def _completed(self, report: MasscanReport) -> None:
        self.report = report
        self._finish_scan()
        self.progress.setValue(100)
        self.status.setText(_t("masscan_complete", count=len(report.observations), ms=report.duration_ms))
        self.result_count.setText(str(len(report.observations)))
        self.export_button.setEnabled(True)
        self._populate()

    def _failed(self, error: object) -> None:
        self._finish_scan()
        self.status.setText(_t("masscan_failed"))
        QMessageBox.warning(self, _t("Masscan Scanner"), external_tool_message(error))

    def _cancelled(self) -> None:
        self._finish_scan()
        self.status.setText(_t("masscan_cancelled"))

    def _finish_scan(self) -> None:
        self._scan_thread = None
        self.cancel_button.setEnabled(False)
        self._refresh_runtime()

    def _populate(self) -> None:
        assert self.report is not None
        self.table.setRowCount(len(self.report.observations))
        for row, observation in enumerate(self.report.observations):
            match = observation.fingerprint
            values = (
                observation.ip,
                observation.port,
                observation.protocol,
                observation.service,
                match.product if match else "",
                match.version if match else "",
                f"{match.confidence:.0%}" if match else _t("masscan_port_inference"),
                observation.banner,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                self.table.setItem(row, column, item)
        self.raw.setPlainText(json.dumps(self.report.to_dict(), ensure_ascii=False, indent=2))

    def _export(self) -> None:
        if not self.report:
            return
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        default = REPORTS_DIR / f"masscan-{self.report.resolved_target.replace('/', '_')}.json"
        path, _ = QFileDialog.getSaveFileName(self, _t("masscan_export"), str(default), "JSON (*.json)")
        if path:
            Path(path).write_text(json.dumps(self.report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def closeEvent(self, event) -> None:
        if self._scan_thread and self._scan_thread.isRunning():
            self._scan_thread.cancel()
            stop_and_detach_thread(self._scan_thread, self._scan_thread)
            self._scan_thread = None
        if self._install_thread and self._install_thread.isRunning():
            stop_and_detach_thread(self._install_thread, self._install_thread)
            self._install_thread = None
        super().closeEvent(event)
