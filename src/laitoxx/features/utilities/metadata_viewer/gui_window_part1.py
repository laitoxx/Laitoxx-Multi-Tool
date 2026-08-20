"""Focused behavior slice for MetadataViewerWindow."""
# ruff: noqa: F405

from .gui_window_context import *  # noqa: F403


class MetadataViewerWindowMixin1:
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("PageHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 12, 14, 12)
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel(translator.get("metadata_viewer_title"))
        title.setObjectName("PageTitle")
        subtitle = QLabel(translator.get("metadata_drag_drop"))
        subtitle.setObjectName("PageSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        self.lbl_status = QLabel(translator.get("metadata_drag_drop"))
        self.lbl_status.setObjectName("Muted")
        self.btn_export = QPushButton(translator.get("Export"))
        self.btn_export.setEnabled(False)
        self.btn_open = QPushButton(translator.get("Open File"))
        self.btn_open.setProperty("variant", "primary")
        self.btn_open.clicked.connect(self._browse_file)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_status)
        header_layout.addWidget(self.btn_export)
        header_layout.addWidget(self.btn_open)
        main_layout.addWidget(header)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        files_panel = QFrame()
        files_panel.setObjectName("PanelSurface")
        files_layout = QVBoxLayout(files_panel)
        files_layout.setContentsMargins(12, 14, 12, 12)
        files_title = QLabel(translator.get("Files"))
        files_title.setObjectName("PanelTitle")
        files_layout.addWidget(files_title)
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self._on_file_selected)
        files_layout.addWidget(self.file_list, 1)
        add_file = QPushButton(translator.get("Open File"))
        add_file.setProperty("variant", "ghost")
        add_file.clicked.connect(self._browse_file)
        files_layout.addWidget(add_file)
        files_panel.setMinimumWidth(210)
        files_panel.setMaximumWidth(310)
        self.splitter.addWidget(files_panel)

        self.content_stack = QStackedWidget()
        self.empty_page = self._build_empty_page()
        self.content_page = QWidget()
        content_layout = QVBoxLayout(self.content_page)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        file_header = QFrame()
        file_header.setObjectName("PanelSurface")
        file_header_layout = QHBoxLayout(file_header)
        file_header_layout.setContentsMargins(14, 10, 10, 10)
        file_info = QVBoxLayout()
        file_info.setSpacing(2)
        self.file_name_label = QLabel(translator.get("No file selected"))
        self.file_name_label.setObjectName("PanelTitle")
        self.file_meta_label = QLabel("")
        self.file_meta_label.setObjectName("Muted")
        file_info.addWidget(self.file_name_label)
        file_info.addWidget(self.file_meta_label)
        file_header_layout.addLayout(file_info)
        file_header_layout.addStretch()
        copy_path = QPushButton(translator.get("Copy path"))
        copy_path.setProperty("variant", "ghost")
        copy_path.clicked.connect(self._copy_current_path)
        reanalyze = QPushButton(translator.get("Re-analyze"))
        reanalyze.clicked.connect(lambda: self.current_filepath and self._load_file(self.current_filepath))
        remove_file = QPushButton(translator.get("Remove"))
        remove_file.setProperty("variant", "ghost")
        remove_file.clicked.connect(self._remove_current_file)
        file_header_layout.addWidget(copy_path)
        file_header_layout.addWidget(reanalyze)
        file_header_layout.addWidget(remove_file)
        content_layout.addWidget(file_header)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        content_layout.addWidget(self.tabs, 1)
        self.content_stack.addWidget(self.empty_page)
        self.content_stack.addWidget(self.content_page)
        self.splitter.addWidget(self.content_stack)
        self.splitter.setSizes([245, 760])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        main_layout.addWidget(self.splitter, 1)

        # Overview is deliberately the first tab: it answers what the file is
        # before exposing the full technical dump.
        self.tab_overview = QWidget()
        overview_outer = QVBoxLayout(self.tab_overview)
        overview_outer.setContentsMargins(14, 14, 14, 14)
        self.overview_grid = QGridLayout()
        self.overview_grid.setSpacing(10)
        self.overview_labels = {}
        overview_items = [
            ("type", translator.get("File type")),
            ("size", translator.get("File size")),
            ("dimensions", translator.get("Dimensions")),
            ("created", translator.get("Created")),
            ("modified", translator.get("Modified")),
            ("author", translator.get("Author / creator")),
        ]
        for index, (key, label_text) in enumerate(overview_items):
            card = QFrame()
            card.setObjectName("PanelSurface")
            card_layout = QVBoxLayout(card)
            caption = QLabel(label_text)
            caption.setObjectName("Muted")
            value = QLabel("-")
            value.setObjectName("PanelTitle")
            value.setWordWrap(True)
            card_layout.addWidget(caption)
            card_layout.addWidget(value)
            self.overview_labels[key] = value
            self.overview_grid.addWidget(card, index // 2, index % 2)
        overview_outer.addLayout(self.overview_grid)
        overview_outer.addStretch()
        self.tabs.addTab(self.tab_overview, translator.get("Overview"))

        self.tab_raw = QWidget()
        raw_layout = QVBoxLayout(self.tab_raw)
        raw_layout.setContentsMargins(12, 12, 12, 12)
        self.metadata_filter = QLineEdit()
        self.metadata_filter.setPlaceholderText(translator.get("Filter metadata…"))
        self.metadata_filter.textChanged.connect(self._filter_metadata)
        raw_layout.addWidget(self.metadata_filter)
        self.table_meta = QTableWidget()
        self.table_meta.setAlternatingRowColors(True)
        self.table_meta.setColumnCount(4)
        self.table_meta.setHorizontalHeaderLabels(
            [translator.get("Group"), translator.get("Property"), translator.get("Value"), translator.get("Source")]
        )
        self.table_meta.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_meta.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_meta.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_meta.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        raw_layout.addWidget(self.table_meta)
        self.tabs.addTab(self.tab_raw, translator.get("Metadata"))

        # Tab 2: Forensics & Privacy
        self.tab_forensics = QWidget()
        for_layout = QVBoxLayout(self.tab_forensics)
        self.lbl_privacy_score = QLabel(translator.get("Privacy Score: N/A"))
        self.lbl_privacy_score.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.lbl_privacy_rec = QLabel("")
        self.lbl_privacy_rec.setWordWrap(True)
        self.list_anomalies = QListWidget()

        for_layout.addWidget(self.lbl_privacy_score)
        for_layout.addWidget(self.lbl_privacy_rec)
        for_layout.addWidget(QLabel(translator.get("Detected Anomalies & Leaks:")))
        for_layout.addWidget(self.list_anomalies)

        # Sanitizer button inside Forensics
        self.btn_sanitize = QPushButton(translator.get("Sanitize (Wipe All Metadata)"))
        self.btn_sanitize.setProperty("variant", "ghost")
        self.btn_sanitize.clicked.connect(self._sanitize_current)
        self.tabs.addTab(self.tab_forensics, translator.get("Forensics"))

        # Tab 3: Productivity (Smart Renamer)
        self.tab_prod = QWidget()
        prod_layout = QVBoxLayout(self.tab_prod)
        prod_layout.addWidget(QLabel(translator.get("Smart Renamer (Uses Metadata Tags)")))
        self.input_rename_pattern = QLineEdit()
        self.input_rename_pattern.setPlaceholderText("E.g. [EXIF:Make]_[EXIF:Model]_[FileExtension]")
        prod_layout.addWidget(self.input_rename_pattern)
        self.btn_rename = QPushButton(translator.get("Rename Current File"))
        self.btn_rename.clicked.connect(self._smart_rename)
        prod_layout.addWidget(self.btn_rename)
        prod_layout.addStretch()
        prod_layout.addWidget(self.btn_sanitize)
        self.tabs.addTab(self.tab_prod, translator.get("Tools"))

        # Tab 4: Graph Analysis
        self.tab_graph = QWidget()
        graph_layout = QVBoxLayout(self.tab_graph)
        graph_layout.addWidget(QLabel(translator.get("Visualize relationships between files, authors, and software.")))
        self.btn_export_graph = QPushButton(translator.get("Export to Graph Editor"))
        self.btn_export_graph.clicked.connect(self._export_to_graph)
        graph_layout.addWidget(self.btn_export_graph)
        graph_layout.addStretch()
        self.tabs.addTab(self.tab_graph, translator.get("Relationships"))

        # Contextual document identity analysis. The tab is enabled only for
        # formats for which the local extractor can produce meaningful data.
        self.tab_identity = QWidget()
        identity_layout = QVBoxLayout(self.tab_identity)
        self.lbl_identity_hint = QLabel(translator.get("osint_document_identity_hint"))
        self.lbl_identity_hint.setWordWrap(True)
        identity_layout.addWidget(self.lbl_identity_hint)
        self.identity_output = QTextEdit()
        self.identity_output.setReadOnly(True)
        self.identity_output.setPlaceholderText(
            translator.get("Select a supported document to analyze identity clues.")
        )
        identity_layout.addWidget(self.identity_output)
        self.identity_tab_index = self.tabs.addTab(self.tab_identity, translator.get("Document"))
        self.tabs.setTabEnabled(self.identity_tab_index, False)

    def _build_empty_page(self):
        page = QFrame()
        page.setObjectName("EmptyState")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addStretch()
        icon = QLabel("◇")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setObjectName("PageTitle")
        title = QLabel(translator.get("Drop files to inspect metadata"))
        title.setObjectName("EmptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel(translator.get("Open one or several files. They will stay in the list for quick comparison."))
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button = QPushButton(translator.get("Open File"))
        button.setProperty("variant", "primary")
        button.clicked.connect(self._browse_file)
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        return page

    def _apply_style(self):
        td = resolved_theme(self.theme_data)
        self.setStyleSheet(build_workspace_qss(td) + f"QDialog {{ background: {td['surface_base_color']}; }}")

    def update_theme(self, theme_data: dict):
        self.theme_data = theme_data or {}
        self._apply_style()

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                self._add_file_to_list(path)
            elif os.path.isdir(path):
                self._load_directory(path)

    def _load_directory(self, dirpath):
        for root, _, files in os.walk(dirpath):
            for file in files:
                self._add_file_to_list(os.path.join(root, file))

    def _browse_file(self):
        paths, _ = QFileDialog.getOpenFileNames(self, translator.get("Open File"))
        for path in paths:
            self._add_file_to_list(path)
