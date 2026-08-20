"""Focused behavior slice for SteganographyWindow."""
# ruff: noqa: F405

from .steganography_window_context import *  # noqa: F403


class SteganographyWindowMixin1:
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 16)
        main_layout.setSpacing(10)

        # Compact common page header.
        header = QFrame()
        header.setObjectName("PageHeader")
        header.setFixedHeight(82)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 12, 8)
        header_copy = QVBoxLayout()
        header_copy.setSpacing(1)
        header_lbl = QLabel(translator.get("Steganography Studio"))
        font = header_lbl.font()
        font.setPointSize(18)
        font.setBold(True)
        header_lbl.setFont(font)
        header_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_lbl.setObjectName("PanelTitle")

        sub_lbl = QLabel(translator.get("Hide or extract secret data within image files."))
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        sub_lbl.setObjectName("Muted")
        header_copy.addWidget(header_lbl)
        header_copy.addWidget(sub_lbl)
        header_layout.addLayout(header_copy)
        header_layout.addStretch()
        self.hide_mode_btn = QPushButton(translator.get("Hide Data"))
        self.extract_mode_btn = QPushButton(translator.get("Extract Data"))
        for button in (self.hide_mode_btn, self.extract_mode_btn):
            button.setCheckable(True)
            button.setProperty("nav", "true")
            header_layout.addWidget(button)
        self.hide_mode_btn.clicked.connect(lambda: self._select_mode(0))
        self.extract_mode_btn.clicked.connect(lambda: self._select_mode(1))
        self.hide_mode_btn.setChecked(True)
        main_layout.addWidget(header)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(10)

        # --- LEFT PANEL ---
        self.left_panel = QScrollArea()
        self.left_panel.setWidgetResizable(True)
        self.left_panel.setFrameShape(QFrame.Shape.NoFrame)
        self.left_panel.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_content = QWidget()
        left_layout = QVBoxLayout(left_content)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)
        self.left_panel.setWidget(left_content)

        # 1. Operation Details Card
        action_card = ModernCard(translator.get("Operation Details"))

        settings_grid = QGridLayout()
        settings_grid.setHorizontalSpacing(14)
        settings_grid.setVerticalSpacing(10)
        settings_grid.setColumnStretch(1, 1)
        mode_lbl = QLabel(translator.get("Action:"))
        mode_lbl.setObjectName("Muted")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(
            [
                translator.get("Hide Data"),
                translator.get("Extract Data"),
                translator.get("Analyze"),
                translator.get("Injector"),
            ]
        )
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        settings_grid.addWidget(mode_lbl, 0, 0)
        settings_grid.addWidget(self.mode_combo, 0, 1)

        self._build_method_controls(settings_grid)
        action_card.layout.addLayout(settings_grid)

        self.constraints_lbl = QLabel()
        self.constraints_lbl.setWordWrap(True)
        self.constraints_lbl.setObjectName("ConstraintsLabel")
        action_card.layout.addWidget(self.constraints_lbl)

        self.recommendation_container = QWidget()
        recommendation_layout = QHBoxLayout(self.recommendation_container)
        recommendation_layout.setContentsMargins(0, 0, 0, 0)
        recommendation_layout.setSpacing(8)
        self.recommendation_lbl = QLabel()
        self.recommendation_lbl.setObjectName("RecommendationLabel")
        self.recommendation_lbl.setWordWrap(True)
        self.apply_recommendation_btn = QPushButton(translator.get("Use"))
        self.apply_recommendation_btn.setObjectName("SecondaryButton")
        self.apply_recommendation_btn.setFixedWidth(76)
        self.apply_recommendation_btn.clicked.connect(self._apply_recommended_method)
        recommendation_layout.addWidget(self.recommendation_lbl, 1)
        recommendation_layout.addWidget(self.apply_recommendation_btn)
        self.recommendation_container.hide()
        action_card.layout.addWidget(self.recommendation_container)

        left_layout.addWidget(action_card)

        # 2. Data & Inputs Card
        io_card = ModernCard(translator.get("Data & Inputs"))

        img_lbl = QLabel(translator.get("Cover Image:"))
        img_lbl.setObjectName("Muted")
        img_row = QHBoxLayout()
        self.image_input = QLineEdit()
        self.image_input.setPlaceholderText(translator.get("Select cover image..."))
        self.image_input.textChanged.connect(self._update_capacity)
        self.image_input.textChanged.connect(self._update_process_state)
        browse_img_btn = QPushButton(translator.get("Browse"))
        browse_img_btn.setFixedWidth(100)
        browse_img_btn.clicked.connect(self._browse_image)
        img_row.addWidget(self.image_input)
        img_row.addWidget(browse_img_btn)

        io_card.layout.addWidget(img_lbl)
        io_card.layout.addLayout(img_row)

        self.payload_label = QLabel(translator.get("Payload Text:"))
        self.payload_label.setObjectName("Muted")
        self.payload_input = QTextEdit()
        self.payload_input.setPlaceholderText(translator.get("Enter secret text to hide..."))
        self.payload_input.setMinimumHeight(64)
        self.payload_input.setMaximumHeight(88)
        self.payload_input.textChanged.connect(self._update_capacity)
        self.payload_input.textChanged.connect(self._update_recommendation)

        io_card.layout.addWidget(self.payload_label)
        io_card.layout.addWidget(self.payload_input)

        payload_file_row = QHBoxLayout()
        self.payload_file_input = QLineEdit()
        self.payload_file_input.setReadOnly(True)
        self.payload_file_input.setPlaceholderText(translator.get("Or select any file to hide..."))
        self.payload_file_btn = QPushButton(translator.get("Select File"))
        self.payload_file_btn.clicked.connect(self._browse_payload_file)
        payload_file_row.addWidget(self.payload_file_input, 1)
        payload_file_row.addWidget(self.payload_file_btn)
        io_card.layout.addLayout(payload_file_row)

        # Password Container (Hidden by default, shown for F5)
        self.password_container = QWidget()
        pwd_layout = QVBoxLayout(self.password_container)
        pwd_layout.setContentsMargins(0, 10, 0, 0)
        self.encryption_check = QCheckBox(translator.get("Encrypt payload"))
        self.password_label = QLabel(translator.get("Encryption password:"))
        self.password_label.setObjectName("Muted")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(translator.get("Enter encryption password"))
        self.encryption_check.toggled.connect(self._update_encryption_fields)
        pwd_layout.addWidget(self.encryption_check)
        pwd_layout.addWidget(self.password_label)
        pwd_layout.addWidget(self.password_input)

        io_card.layout.addWidget(self.password_container)

        # Capacity Container
        self.capacity_container = QWidget()
        cap_layout = QVBoxLayout(self.capacity_container)
        cap_layout.setContentsMargins(0, 10, 0, 0)
        self.capacity_label = QLabel(translator.get("Capacity Usage:"))
        self.capacity_label.setObjectName("Muted")
        self.capacity_bar = QProgressBar()
        self.capacity_bar.setTextVisible(True)
        self.capacity_bar.setFormat(translator.get("%v / %m bytes used"))
        cap_layout.addWidget(self.capacity_label)
        cap_layout.addWidget(self.capacity_bar)

        io_card.layout.addWidget(self.capacity_container)

        left_layout.addWidget(io_card)

        # Process Button
        self.process_btn = QPushButton(translator.get("Hide Data"))
        self.process_btn.setMinimumHeight(44)
        font = self.process_btn.font()
        font.setBold(True)
        font.setPointSize(12)
        self.process_btn.setFont(font)
        self.process_btn.setObjectName("ProcessButton")
        self.process_btn.clicked.connect(self._process_stego)
        apply_shadow(self.process_btn)

        left_layout.addWidget(self.process_btn)
        self.scan_progress_bar = QProgressBar()
        self.scan_progress_bar.setTextVisible(True)
        self.scan_progress_bar.setFormat("%v / %m")
        self.scan_progress_bar.hide()
        left_layout.addWidget(self.scan_progress_bar)
        left_layout.addStretch(1)

        # --- RIGHT PANEL ---
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(10)

        # A single preview workspace keeps the compact window useful and avoids
        # two large empty cards before an image has been selected.
        preview_card = ModernCard(translator.get("Preview"))
        self.preview_tabs = QTabWidget()
        self.preview_tabs.setDocumentMode(True)

        self.original_lbl = ImageDropLabel(translator.get("Drop an image here or click Browse"))
        self.original_lbl.setObjectName("PreviewArea")
        self.original_lbl.setMinimumHeight(320)
        self.original_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_lbl.imageDropped.connect(self._load_image)
        self.result_lbl = QLabel(translator.get("Result Preview"))
        self.result_lbl.setObjectName("PreviewArea")
        self.result_lbl.setMinimumHeight(320)
        self.result_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.extracted_output = QTextEdit()
        self.extracted_output.setObjectName("ExtractedOutput")
        self.extracted_output.setReadOnly(True)
        self.extracted_output.setPlaceholderText(translator.get("Extracted data will appear here."))
        self.extracted_output.hide()
        self.result_page = QWidget()
        result_page_layout = QVBoxLayout(self.result_page)
        result_page_layout.setContentsMargins(0, 0, 0, 0)
        result_page_layout.addWidget(self.result_lbl)
        result_page_layout.addWidget(self.extracted_output)
        self.preview_tabs.addTab(self.original_lbl, translator.get("Original Cover"))
        self.preview_tabs.addTab(self.result_page, translator.get("Result / Extracted Preview"))
        preview_card.layout.addWidget(self.preview_tabs)
        right_layout.addWidget(preview_card)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([380, 620])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self.splitter)

        self._on_method_changed()
        self._on_mode_changed()
        self._update_encryption_fields()
        self._update_process_state()
