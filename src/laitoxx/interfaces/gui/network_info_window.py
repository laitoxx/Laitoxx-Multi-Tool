"""Composition root for NetworkInfoWindow."""
# ruff: noqa: F405

from .network_info_window_context import *  # noqa: F403
from .network_info_window_part1 import NetworkInfoWindowMixin1
from .network_info_window_part2 import NetworkInfoWindowMixin2
from .network_info_window_part3 import NetworkInfoWindowMixin3


class NetworkInfoWindow(NetworkInfoWindowMixin1, NetworkInfoWindowMixin2, NetworkInfoWindowMixin3, QDialog):
    osint_data_ready = pyqtSignal(dict)
    subdomain_progress = pyqtSignal(object)
    subdomain_ready = pyqtSignal(object)
    subdomain_failed = pyqtSignal(str)

    def __init__(self, parent=None, mode="ip", theme_data=None):
        super().__init__(parent)
        self.mode = mode
        self.theme_data = theme_data or {}
        if mode == "ip":
            self.setWindowTitle(translator.get("ni_title_ip"))
        elif mode == "mac":
            self.setWindowTitle(translator.get("ni_title_mac"))
        else:
            self.setWindowTitle(translator.get("ni_title_website"))
        self.resize(1100, 750)
        self.setWindowOpacity(0.92)  # Keep the workspace background visible.
        self.osint_data_ready.connect(self._on_osint_data_ready)
        self.subdomain_progress.connect(self._on_subdomain_progress)
        self.subdomain_ready.connect(self._on_subdomain_ready)
        self.subdomain_failed.connect(self._on_subdomain_failed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Search controls.
        top_bar = QHBoxLayout()
        self.input_field = QLineEdit()
        if mode == "ip":
            self.input_field.setPlaceholderText(translator.get("ni_placeholder_ip"))
        elif mode == "mac":
            self.input_field.setPlaceholderText(translator.get("ni_placeholder_mac"))
        else:
            self.input_field.setPlaceholderText(translator.get("ni_placeholder_domain"))
        self.input_field.returnPressed.connect(self.run_search)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                font-size: 14px;
            }
        """)

        self.search_btn = QPushButton(translator.get("ni_search"))
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0098ff;
            }
        """)
        self.search_btn.clicked.connect(self.run_search)

        top_bar.addWidget(self.input_field)
        top_bar.addWidget(self.search_btn)
        if self.mode == "website":
            self.subdomain_btn = QPushButton(translator.get("di_discover_subdomains"))
            self.subdomain_btn.setToolTip(translator.get("di_subdomain_hint"))
            self.subdomain_btn.clicked.connect(self._run_subdomain_discovery)
            top_bar.addWidget(self.subdomain_btn)
        layout.addLayout(top_bar)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Use indeterminate progress for the main profile.
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Main workspace splitter.
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Result tabs.
        self.tabs = QTabWidget()
        self.console_tab = QWidget()
        console_layout = QVBoxLayout(self.console_tab)
        console_layout.setContentsMargins(0, 0, 0, 0)
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        console_layout.addWidget(self.console_output)
        self.tabs.addTab(self.console_tab, translator.get("ni_terminal"))

        if self.mode == "website":
            self.subdomain_tab = QWidget()
            subdomain_layout = QVBoxLayout(self.subdomain_tab)
            subdomain_layout.setContentsMargins(0, 0, 0, 0)
            options = QHBoxLayout()
            self.subdomain_resolve = QCheckBox(translator.get("di_resolve_dns"))
            self.subdomain_resolve.setChecked(True)
            self.subdomain_http = QCheckBox(translator.get("di_probe_http"))
            self.subdomain_filter = QComboBox()
            self.subdomain_filter.addItem(translator.get("di_filter_all"), "all")
            self.subdomain_filter.addItem(translator.get("di_filter_resolved"), "resolved")
            self.subdomain_filter.addItem(translator.get("di_filter_http"), "http")
            self.subdomain_filter.addItem(translator.get("di_filter_wildcard"), "wildcard")
            self.subdomain_filter.currentIndexChanged.connect(self._filter_subdomains)
            self.subdomain_stop_btn = QPushButton(translator.get("di_stop"))
            self.subdomain_stop_btn.setEnabled(False)
            self.subdomain_stop_btn.clicked.connect(self._stop_subdomain_discovery)
            self.subdomain_export_btn = QPushButton(translator.get("di_export"))
            self.subdomain_export_btn.setEnabled(False)
            self.subdomain_export_btn.clicked.connect(self._export_subdomains)
            self.subdomain_graph_btn = QPushButton(translator.get("di_open_graph"))
            self.subdomain_graph_btn.setEnabled(False)
            self.subdomain_graph_btn.clicked.connect(self._open_subdomain_graph)
            for widget in (
                self.subdomain_resolve,
                self.subdomain_http,
                self.subdomain_filter,
                self.subdomain_stop_btn,
                self.subdomain_export_btn,
                self.subdomain_graph_btn,
            ):
                options.addWidget(widget)
            options.addStretch()
            subdomain_layout.addLayout(options)
            self.subdomain_progress_bar = QProgressBar()
            self.subdomain_progress_bar.setFormat(translator.get("di_ready"))
            subdomain_layout.addWidget(self.subdomain_progress_bar)
            self.subdomain_table = QTableWidget(0, 7)
            self.subdomain_table.setHorizontalHeaderLabels(
                [
                    translator.get("di_col_hostname"),
                    translator.get("di_col_dns"),
                    "IPv4",
                    "IPv6",
                    "CNAME",
                    "HTTP",
                    translator.get("di_col_source"),
                ]
            )
            self.subdomain_table.setSortingEnabled(True)
            subdomain_layout.addWidget(self.subdomain_table)
            self.tabs.addTab(self.subdomain_tab, translator.get("di_subdomains"))

        splitter.addWidget(self.tabs)

        # Map panel for IP and MAC modes.
        if self.mode in ("ip", "mac"):
            map_container = QWidget()
            map_layout = QVBoxLayout(map_container)
            map_layout.setContentsMargins(0, 0, 0, 0)

            if QWebEngineView:
                self.map_view = QWebEngineView()
                settings = self.map_view.settings()
                settings.setAttribute(
                    QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                    True,
                )
                settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
                self._load_empty_map()
                map_layout.addWidget(self.map_view)
            else:
                self.map_view = None
                lbl = QLabel("Map view requires PyQt6-WebEngine.\nPlease install it via 'pip install PyQt6-WebEngine'")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("color: #ff5555; font-size: 14px;")
                map_layout.addWidget(lbl)

            splitter.addWidget(map_container)
            splitter.setSizes([550, 550])
        else:
            self.map_view = None
            splitter.setSizes([1100])

        self._worker_thread = None
        self._worker = None
        self._subdomain_control = None
        self._subdomain_report = None
        self.lat = 0.0
        self.lon = 0.0

        self._apply_theme()
