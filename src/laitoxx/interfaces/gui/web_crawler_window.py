"""Dedicated GUI for the structured Web Crawler service."""

from __future__ import annotations

import json
import re
import time

from PyQt6.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from laitoxx.core.localization.i18n import translator
from laitoxx.features.web_audit.crawler import CrawlConfig, crawl_website
from laitoxx.features.web_audit.crawler.export import export_crawl_report
from laitoxx.interfaces.gui.design_system import build_workspace_qss, resolved_theme
from laitoxx.interfaces.gui.worker import stop_and_detach_thread
from laitoxx.shared.execution import JobControl


def _t(key: str, fallback: str) -> str:
    value = translator.get(key)
    return fallback if not value or value == key else value


class _CrawlerWorker(QObject):
    progress = pyqtSignal(object)
    page = pyqtSignal(object)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, config: CrawlConfig, control: JobControl) -> None:
        super().__init__()
        self.config = config
        self.control = control

    @pyqtSlot()
    def run(self) -> None:
        try:
            report = crawl_website(
                self.config,
                progress=self.progress.emit,
                control=self.control,
                page_callback=self.page.emit,
            )
            self.completed.emit(report)
        except Exception as error:
            self.failed.emit(str(error))


class WebCrawlerWindow(QDialog):
    """Configure, monitor, filter and export a bounded website crawl."""

    def __init__(self, parent=None, theme_data=None) -> None:
        super().__init__(parent)
        self.theme_data = theme_data or {}
        self._thread: QThread | None = None
        self._worker: _CrawlerWorker | None = None
        self._control: JobControl | None = None
        self._report = None
        self._pages = []
        self._started_monotonic = 0.0
        self._queue_count = 0
        self.setWindowTitle(_t("wc_title", "Web Crawler"))
        self.resize(1180, 760)
        self._build_ui()
        self.update_theme(self.theme_data)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        self.url_input.returnPressed.connect(self.start_crawl)
        controls.addWidget(self.url_input, 1)
        self.max_pages = QSpinBox()
        self.max_pages.setRange(1, 10000)
        self.max_pages.setValue(200)
        self.max_pages.setPrefix(_t("wc_pages", "Pages") + ": ")
        controls.addWidget(self.max_pages)
        self.max_depth = QSpinBox()
        self.max_depth.setRange(0, 50)
        self.max_depth.setValue(4)
        self.max_depth.setPrefix(_t("wc_depth", "Depth") + ": ")
        controls.addWidget(self.max_depth)
        self.concurrency = QSpinBox()
        self.concurrency.setRange(1, 50)
        self.concurrency.setValue(8)
        self.concurrency.setPrefix(_t("wc_workers", "Workers") + ": ")
        controls.addWidget(self.concurrency)
        self.delay = QDoubleSpinBox()
        self.delay.setRange(0, 10)
        self.delay.setDecimals(2)
        self.delay.setValue(0.05)
        self.delay.setPrefix(_t("wc_delay", "Delay") + ": ")
        self.delay.setSuffix(" s")
        controls.addWidget(self.delay)
        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(1, 120)
        self.timeout.setDecimals(1)
        self.timeout.setValue(10)
        self.timeout.setPrefix(_t("wc_timeout", "Timeout") + ": ")
        self.timeout.setSuffix(" s")
        controls.addWidget(self.timeout)
        self.max_size = QSpinBox()
        self.max_size.setRange(1, 100)
        self.max_size.setValue(2)
        self.max_size.setPrefix(_t("wc_max_size", "Max response") + ": ")
        self.max_size.setSuffix(" MB")
        controls.addWidget(self.max_size)
        root.addLayout(controls)

        options = QHBoxLayout()
        self.scope = QComboBox()
        self.scope.addItem(_t("wc_scope_host", "Current host"), "host")
        self.scope.addItem(_t("wc_scope_subdomains", "Host and subdomains"), "subdomains")
        options.addWidget(self.scope)
        self.query_policy = QComboBox()
        self.query_policy.addItem(_t("wc_query_normalize", "Normalize query"), "sort")
        self.query_policy.addItem(_t("wc_query_drop", "Drop query"), "drop")
        self.query_policy.addItem(_t("wc_query_keep", "Keep query"), "keep")
        options.addWidget(self.query_policy)
        self.robots = QCheckBox(_t("wc_respect_robots", "Respect robots.txt"))
        self.robots.setChecked(True)
        options.addWidget(self.robots)
        self.sitemap = QCheckBox(_t("wc_use_sitemap", "Use sitemap"))
        self.sitemap.setChecked(True)
        options.addWidget(self.sitemap)
        options.addStretch()
        self.start_button = QPushButton(_t("wc_start", "Start"))
        self.start_button.clicked.connect(self.start_crawl)
        options.addWidget(self.start_button)
        self.pause_button = QPushButton(_t("wc_pause", "Pause"))
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.toggle_pause)
        options.addWidget(self.pause_button)
        self.stop_button = QPushButton(_t("wc_stop", "Stop"))
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_crawl)
        options.addWidget(self.stop_button)
        self.export_button = QPushButton(_t("wc_export", "Export"))
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_report)
        options.addWidget(self.export_button)
        self.graph_button = QPushButton(_t("wc_graph", "Open Graph"))
        self.graph_button.setEnabled(False)
        self.graph_button.clicked.connect(self.open_graph)
        options.addWidget(self.graph_button)
        root.addLayout(options)

        status_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setFormat(_t("wc_ready", "Ready"))
        status_row.addWidget(self.progress, 1)
        self.summary = QLabel("Pages: 0 | Broken: 0 | Errors: 0 | Queue: 0")
        status_row.addWidget(self.summary)
        root.addLayout(status_row)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(_t("wc_show", "Show") + ":"))
        self.status_filter = QComboBox()
        self.status_filter.addItem(_t("wc_all", "All"), "all")
        self.status_filter.addItem(_t("wc_successful", "Successful"), "success")
        self.status_filter.addItem(_t("wc_broken", "Broken"), "broken")
        self.status_filter.addItem(_t("wc_errors", "Errors"), "error")
        self.status_filter.currentIndexChanged.connect(self.apply_filter)
        filter_row.addWidget(self.status_filter)
        self.result_search = QLineEdit()
        self.result_search.setPlaceholderText(_t("wc_filter_hint", "Filter by URL or title"))
        self.result_search.textChanged.connect(self.apply_filter)
        filter_row.addWidget(self.result_search, 1)
        root.addLayout(filter_row)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.result_tabs = QTabWidget()
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                _t("wc_col_status", "Status"),
                _t("wc_depth", "Depth"),
                "URL",
                _t("wc_col_title", "Title"),
                _t("wc_col_type", "Type"),
                _t("wc_col_time", "Time"),
                _t("wc_col_error", "Error"),
            ]
        )
        self.table.setSortingEnabled(True)
        self.table.itemSelectionChanged.connect(self.show_selected_details)
        self.result_tabs.addTab(self.table, _t("wc_pages_tab", "Pages"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            [
                _t("wc_tree_tab", "Site Tree"),
                _t("wc_col_status", "Status"),
                _t("wc_col_title", "Title"),
            ]
        )
        self.result_tabs.addTab(self.tree, _t("wc_tree_tab", "Site Tree"))
        splitter.addWidget(self.result_tabs)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText(
            _t("wc_details_hint", "Select a page to inspect links, forms, assets and headers.")
        )
        splitter.addWidget(self.details)
        splitter.setSizes([520, 180])
        root.addWidget(splitter, 1)

    def _config(self) -> CrawlConfig:
        return CrawlConfig(
            seed_url=self.url_input.text().strip(),
            max_pages=self.max_pages.value(),
            max_depth=self.max_depth.value(),
            concurrency=self.concurrency.value(),
            request_delay=self.delay.value(),
            timeout=self.timeout.value(),
            max_response_bytes=self.max_size.value() * 1_000_000,
            scope=self.scope.currentData(),
            query_policy=self.query_policy.currentData(),
            respect_robots=self.robots.isChecked(),
            use_sitemap=self.sitemap.isChecked(),
        ).validated()

    def start_crawl(self) -> None:
        if self._thread is not None:
            return
        try:
            config = self._config()
        except ValueError as error:
            QMessageBox.warning(self, _t("wc_title", "Web Crawler"), str(error))
            return
        self._report = None
        self._pages.clear()
        self._started_monotonic = time.monotonic()
        self._queue_count = 0
        self.table.setRowCount(0)
        self.tree.clear()
        self.details.clear()
        self._control = JobControl()
        self._thread = QThread(self)
        self._worker = _CrawlerWorker(config, self._control)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.on_progress)
        self._worker.page.connect(self.on_page)
        self._worker.completed.connect(self.on_completed)
        self._worker.failed.connect(self.on_failed)
        self._worker.completed.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.export_button.setEnabled(False)
        self.graph_button.setEnabled(False)

    def toggle_pause(self) -> None:
        if self._control is None:
            return
        if self._control.paused:
            self._control.resume()
            self.pause_button.setText(_t("wc_pause", "Pause"))
        else:
            self._control.pause()
            self.pause_button.setText(_t("wc_resume", "Resume"))

    def stop_crawl(self) -> None:
        if self._control is not None:
            self._control.cancel()
            self.stop_button.setEnabled(False)
            self.progress.setFormat(_t("wc_stopping", "Stopping"))

    def on_progress(self, event) -> None:
        maximum = max(1, event.total)
        self.progress.setRange(0, maximum)
        self.progress.setValue(min(event.completed, maximum))
        self.progress.setFormat(f"{event.phase}: {event.completed}/{event.total} {event.message}".strip())
        queue_match = re.search(r"Queue:\s*(\d+)", event.message)
        if queue_match:
            self._queue_count = int(queue_match.group(1))
        self._update_summary()

    def on_page(self, page) -> None:
        self._pages.append(page)
        self._append_page(page)
        self._update_summary()

    def _update_summary(self) -> None:
        broken = sum(item.broken for item in self._pages)
        errors = sum(bool(item.error) for item in self._pages)
        elapsed = max(0.001, time.monotonic() - self._started_monotonic) if self._started_monotonic else 0
        speed = len(self._pages) / elapsed if elapsed else 0
        self.summary.setText(
            f"Pages: {len(self._pages)} | Broken: {broken} | Errors: {errors} | "
            f"Queue: {self._queue_count} | Speed: {speed:.1f} pages/s"
        )

    def _append_page(self, page) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = (
            str(page.status or ""),
            str(page.depth),
            page.url,
            page.title,
            page.content_type,
            f"{page.response_ms:.0f} ms",
            page.error,
        )
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setData(Qt.ItemDataRole.UserRole, page)
            self.table.setItem(row, column, item)

    def apply_filter(self) -> None:
        selected = self.status_filter.currentData()
        needle = self.result_search.text().strip().casefold()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            page = item.data(Qt.ItemDataRole.UserRole) if item else None
            visible = page is not None
            if selected == "success":
                visible = visible and page.status is not None and page.status < 400 and not page.error
            elif selected == "broken":
                visible = visible and page.broken
            elif selected == "error":
                visible = visible and bool(page.error)
            if needle:
                visible = visible and needle in f"{page.url} {page.title}".casefold()
            self.table.setRowHidden(row, not visible)

    def show_selected_details(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        page = items[0].data(Qt.ItemDataRole.UserRole)
        if page is not None:
            self.details.setPlainText(json.dumps(page.to_dict(), ensure_ascii=False, indent=2))

    def on_completed(self, report) -> None:
        self._report = report
        self.progress.setRange(0, max(1, len(report.pages)))
        self.progress.setValue(len(report.pages))
        state = _t("wc_cancelled", "Cancelled") if report.cancelled else _t("wc_complete", "Complete")
        self.progress.setFormat(f"{state}: {len(report.pages)} pages in {report.elapsed_seconds:.1f} s")
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.export_button.setEnabled(bool(report.pages))
        self.graph_button.setEnabled(bool(report.pages))
        self._build_site_tree(report)

    def _build_site_tree(self, report) -> None:
        self.tree.clear()
        items: dict[str, QTreeWidgetItem] = {}
        for page in sorted(report.pages, key=lambda item: (item.depth, item.url)):
            key = page.final_url or page.url
            item = QTreeWidgetItem([key, str(page.status or ""), page.title])
            parent = items.get(page.parent_url)
            if parent is None:
                self.tree.addTopLevelItem(item)
            else:
                parent.addChild(item)
            items[key] = item
            items.setdefault(page.url, item)
        self.tree.expandToDepth(1)

    def on_failed(self, message: str) -> None:
        self.progress.setFormat(f"Error: {message[:100]}")
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def _cleanup_thread(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        if self._thread is not None:
            self._thread.deleteLater()
        self._worker = None
        self._thread = None
        self._control = None

    def export_report(self) -> None:
        if self._report is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            _t("wc_export_title", "Export Crawl Report"),
            "crawl_report.json",
            "JSON (*.json);;CSV (*.csv);;HTML (*.html)",
        )
        if path:
            export_crawl_report(self._report, path)

    def open_graph(self) -> None:
        if self._report is None:
            return
        from laitoxx.features.web_audit.crawler.graph_adapter import build_crawl_graph
        from laitoxx.interfaces.gui.graph_editor import GraphEditorWindow

        if len(self._report.pages) > 300:
            answer = QMessageBox.question(
                self,
                _t("wc_graph", "Open Graph"),
                _t("wc_large_graph", "The report contains more than 300 pages. Open a graph with the first 300 pages?"),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        editor = GraphEditorWindow(self, theme_data=self.theme_data)
        editor._graph = build_crawl_graph(self._report)
        editor._graph_name_edit.setText(editor._graph.name)
        QTimer.singleShot(150, editor._refresh_all)
        editor.exec()

    def update_theme(self, theme_data: dict) -> None:
        self.theme_data = theme_data or {}
        self.setStyleSheet(build_workspace_qss(resolved_theme(self.theme_data)))

    def closeEvent(self, event) -> None:
        if self._control is not None:
            self._control.cancel()
        if self._thread is not None and self._thread.isRunning():
            stop_and_detach_thread(self._thread, self._worker)
            self._thread = None
            self._worker = None
        super().closeEvent(event)
