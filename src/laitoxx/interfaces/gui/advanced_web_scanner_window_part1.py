"""Focused behavior slice for AdvancedWebScannerWindow."""
# ruff: noqa: F405

from .advanced_web_scanner_window_context import *  # noqa: F403


class AdvancedWebScannerWindowMixin1:
    def _build_ui(self):
        root = QVBoxLayout(self)
        self._root_layout = root
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        self.hero_panel = QWidget()
        hero = QHBoxLayout(self.hero_panel)
        hero.setContentsMargins(0, 0, 0, 0)
        hero_text = QVBoxLayout()
        self.page_title = QLabel(translator.get("Advanced Web Scanner"))
        self.page_title.setObjectName("pageTitle")
        hero_text.addWidget(self.page_title)
        subtitle = QLabel(translator.get("aws_window_subtitle"))
        subtitle.setObjectName("secondaryText")
        hero_text.addWidget(subtitle)
        hero.addLayout(hero_text)
        hero.addStretch()
        self.keys_button = QPushButton(translator.get("aws_api_keys"))
        self.keys_button.setObjectName("secondaryButton")
        self.keys_button.clicked.connect(self._configure_api_keys)
        hero.addWidget(self.keys_button)
        root.addWidget(self.hero_panel)

        self.query_panel = QFrame()
        self.query_panel.setObjectName("queryPanel")
        header = QHBoxLayout(self.query_panel)
        header.setContentsMargins(12, 10, 12, 10)
        header.setSpacing(9)
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText(translator.get("aws_target_placeholder"))
        self.target_input.returnPressed.connect(self._start_scan)
        header.addWidget(self.target_input, 1)
        self.profile_combo = QComboBox()
        self.profile_combo.addItem(translator.get("aws_minimum_profile"), "minimum")
        self.profile_combo.addItem(translator.get("aws_maximum_profile"), "maximum")
        header.addWidget(self.profile_combo)
        self.dns_combo = QComboBox()
        self.dns_combo.addItem("DNS-over-HTTPS", "doh")
        self.dns_combo.addItem(translator.get("aws_system_dns"), "system")
        header.addWidget(self.dns_combo)
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(1, 10)
        self.depth_spin.setValue(2)
        self.depth_spin.setPrefix(translator.get("aws_depth_prefix"))
        self.depth_spin.setToolTip(translator.get("aws_depth_hint"))
        self.depth_spin.valueChanged.connect(self._update_scan_warning)
        header.addWidget(self.depth_spin)
        self.active_scan_checkbox = QCheckBox(translator.get("aws_active_validation"))
        self.active_scan_checkbox.setToolTip(translator.get("aws_active_validation_hint"))
        self.active_scan_checkbox.toggled.connect(self._on_active_scan_toggled)
        header.addWidget(self.active_scan_checkbox)
        self.scan_button = QPushButton(translator.get("aws_scan"))
        self.scan_button.setObjectName("primaryButton")
        self.scan_button.clicked.connect(self._start_scan)
        header.addWidget(self.scan_button)
        root.addWidget(self.query_panel)
        self.scan_warning = QLabel()
        self.scan_warning.setObjectName("warningText")
        self.scan_warning.setWordWrap(True)
        self.scan_warning.hide()
        root.addWidget(self.scan_warning)

        self.status_panel = QWidget()
        status_row = QHBoxLayout(self.status_panel)
        status_row.setContentsMargins(0, 0, 0, 0)
        self.status_label = QLabel(translator.get("aws_ready"))
        self.status_label.setObjectName("secondaryText")
        status_row.addWidget(self.status_label, 1)
        root.addWidget(self.status_panel)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        root.addWidget(self.progress)

        self.metrics_panel = QWidget()
        metrics = QHBoxLayout(self.metrics_panel)
        metrics.setContentsMargins(0, 0, 0, 0)
        self.coverage_value = self._add_metric(metrics, translator.get("aws_metric_coverage"))
        self.entities_value = self._add_metric(metrics, translator.get("aws_metric_entities"))
        self.relations_value = self._add_metric(metrics, translator.get("aws_metric_relations"))
        self.vulnerabilities_value = self._add_metric(metrics, translator.get("aws_metric_vulnerabilities"))
        self.risk_label = self._add_metric(metrics, translator.get("aws_metric_risk"))
        root.addWidget(self.metrics_panel)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self._build_overview_tab()
        self._build_graph_tab()
        self._build_timeline_tab()
        self._build_sources_tab()
        self._build_quotas_tab()
        self._build_raw_tab()
        self.tabs.currentChanged.connect(self._update_workspace_chrome)

        self.actions_panel = QWidget()
        actions = QHBoxLayout(self.actions_panel)
        actions.setContentsMargins(0, 0, 0, 0)
        self.export_button = QPushButton(translator.get("aws_export_json"))
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export_json)
        actions.addWidget(self.export_button)
        self.graph_button = QPushButton(translator.get("aws_open_graph_editor"))
        self.graph_button.setEnabled(False)
        self.graph_button.clicked.connect(self._open_graph_editor)
        actions.addWidget(self.graph_button)
        actions.addStretch()
        root.addWidget(self.actions_panel)

    @staticmethod
    def _add_metric(layout, title):
        card = QFrame()
        card.setObjectName("metricCard")
        box = QVBoxLayout(card)
        box.setContentsMargins(12, 8, 12, 8)
        caption = QLabel(title)
        caption.setObjectName("metricCaption")
        value = QLabel("-")
        value.setObjectName("metricValue")
        box.addWidget(caption)
        box.addWidget(value)
        layout.addWidget(card, 1)
        return value

    def _build_overview_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.overview = QTextEdit()
        self.overview.setReadOnly(True)
        layout.addWidget(self.overview)
        self.tabs.addTab(tab, translator.get("aws_overview"))

    def _build_graph_tab(self):
        self.graph_tab = QWidget()
        layout = QVBoxLayout(self.graph_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        toolbar = QHBoxLayout()
        self.graph_projection_notice = QLabel()
        self.graph_projection_notice.setObjectName("secondaryText")
        toolbar.addWidget(self.graph_projection_notice)
        self.vulnerability_badge = QLabel(translator.get("aws_vulnerabilities_count", count=0))
        toolbar.addWidget(self.vulnerability_badge)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.graph_editor = GraphEditorWindow(self.graph_tab, theme_data=self.theme_data)
        self.graph_editor.setWindowFlags(Qt.WindowType.Widget)
        self.graph_editor.setModal(False)
        self.graph_editor.set_embedded_analysis_mode(True)
        layout.addWidget(self.graph_editor, 1)
        self.tabs.addTab(self.graph_tab, translator.get("aws_graph"))

    def _update_workspace_chrome(self, index: int):
        graph_active = self.tabs.widget(index) is self.graph_tab
        for widget in (
            self.hero_panel,
            self.query_panel,
            self.scan_warning,
            self.status_panel,
            self.progress,
            self.metrics_panel,
            self.actions_panel,
        ):
            widget.setVisible(not graph_active)
        if graph_active:
            self._root_layout.setContentsMargins(8, 8, 8, 8)
        else:
            self._root_layout.setContentsMargins(18, 16, 18, 14)
        self._root_layout.setSpacing(6 if graph_active else 12)

    def _build_timeline_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.timeline_table = QTableWidget(0, 7)
        self.timeline_table.setHorizontalHeaderLabels(
            [
                translator.get("aws_event_time"),
                translator.get("aws_observed_at"),
                translator.get("aws_source"),
                translator.get("aws_relation"),
                translator.get("aws_subject"),
                translator.get("aws_object"),
                translator.get("aws_confidence"),
            ]
        )
        self.timeline_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.timeline_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.timeline_table)
        self.tabs.addTab(tab, translator.get("aws_timeline"))

    def _build_sources_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.sources_tree = QTreeWidget()
        self.sources_tree.setHeaderLabels(
            [translator.get("aws_source"), translator.get("aws_status"), translator.get("aws_latency")]
        )
        self.sources_tree.itemSelectionChanged.connect(self._show_selected_source)
        splitter.addWidget(self.sources_tree)
        self.source_details = QTextEdit()
        self.source_details.setReadOnly(True)
        splitter.addWidget(self.source_details)
        splitter.setSizes([360, 700])
        layout.addWidget(splitter)
        self.tabs.addTab(tab, translator.get("aws_sources"))

    def _build_raw_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.raw_output = QTextEdit()
        self.raw_output.setReadOnly(True)
        layout.addWidget(self.raw_output)
        self.tabs.addTab(tab, "JSON")

    def _build_quotas_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.quota_table = QTableWidget(0, 5)
        self.quota_table.setHorizontalHeaderLabels(
            [
                translator.get("aws_source"),
                translator.get("aws_tier"),
                translator.get("aws_mode"),
                translator.get("aws_remaining"),
                translator.get("aws_reset_policy"),
            ]
        )
        self.quota_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.quota_table)
        self.tabs.addTab(tab, translator.get("aws_api_quotas"))
        self._refresh_quotas()

    def _refresh_quotas(self):
        config = load_configuration()
        active = [spec for spec in PROVIDERS if spec.mandatory or config["providers"][spec.id].get("enabled")]
        self.quota_table.setRowCount(len(active))
        for row, spec in enumerate(active):
            status = ledger.status(spec.id)
            values = [
                spec.name,
                translator.get("aws_required" if spec.mandatory else "aws_extended"),
                status.mode,
                "-" if status.remaining is None else str(status.remaining),
                status.label if not status.reset_at else status.reset_at.replace("T", " ")[:19] + " UTC",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if status.exhausted:
                    item.setForeground(QColor("#f94144"))
                self.quota_table.setItem(row, column, item)
