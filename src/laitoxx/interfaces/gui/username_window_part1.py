# ruff: noqa: F405
from .username_window_context import *  # noqa: F403


class UsernameOsintMixin1:
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(8)

        # ── Hero input row ──
        hero = QHBoxLayout()
        hero.setSpacing(8)

        self._at_label = QLabel("@")
        self._at_label.setStyleSheet(f"color: {_ACCENT}; font-size: 22px; font-weight: 700; background: transparent;")
        self._at_label.setFixedWidth(20)
        hero.addWidget(self._at_label)

        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText(_t("uo_enter_username", "Enter username..."))
        self._username_input.setMinimumHeight(40)
        self._username_input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.04);
                border: 1px solid {_BORDER};
                border-radius: 10px;
                color: {_TEXT_PRI};
                padding: 6px 14px;
                font-size: 16px;
                font-weight: 500;
            }}
            QLineEdit:focus {{
                border-color: {_ACCENT};
                background: rgba(255,255,255,0.06);
            }}
        """)
        self._username_input.returnPressed.connect(self._on_search_clicked)
        hero.addWidget(self._username_input, 1)

        self._btn_search = _AccentButton(_t("uo_search", "SEARCH"))
        self._btn_search.setMinimumWidth(110)
        self._btn_search.setMinimumHeight(40)
        self._btn_search.clicked.connect(self._on_search_clicked)
        hero.addWidget(self._btn_search)

        root.addLayout(hero)

        # ── Secondary controls row ──
        sec = QHBoxLayout()
        sec.setSpacing(6)

        self._search_mode = QComboBox()
        self._search_mode.addItem(_t("uo_mode_quick", "Quick: 120 reliable sites"), "quick")
        self._search_mode.addItem(_t("uo_mode_standard", "Standard: 500 sites"), "standard")
        self._search_mode.addItem(_t("uo_mode_full", "Full database"), "full")
        self._search_mode.addItem(_t("uo_mode_custom", "Selected categories"), "custom")
        self._search_mode.setCurrentIndex(1)
        self._search_mode.setToolTip("Choose a bounded search profile or scan the complete database.")
        sec.addWidget(self._search_mode)

        self._sort_mode = QComboBox()
        self._sort_mode.addItem(_t("uo_sort_confidence", "Sort: Confidence"), "confidence")
        self._sort_mode.addItem(_t("uo_sort_site", "Sort: Site"), "site")
        self._sort_mode.addItem(_t("uo_sort_arrival", "Sort: Arrival"), "arrival")
        self._sort_mode.currentIndexChanged.connect(self._filter_results)
        sec.addWidget(self._sort_mode)

        self._first_name = QLineEdit()
        self._first_name.setPlaceholderText(_t("uo_first_name", "First name"))
        self._first_name.setMaximumWidth(130)
        self._first_name.setFixedHeight(28)
        sec.addWidget(self._first_name)

        self._last_name = QLineEdit()
        self._last_name.setPlaceholderText(_t("uo_last_name", "Last name"))
        self._last_name.setMaximumWidth(130)
        self._last_name.setFixedHeight(28)
        sec.addWidget(self._last_name)

        sec.addStretch()

        self._btn_nicks = _GhostButton(_t("uo_generate_nicks", "Variants"))
        self._btn_nicks.clicked.connect(self._generate_nicknames)
        sec.addWidget(self._btn_nicks)

        self._btn_health = _GhostButton(_t("uo_provider_health", "Provider Health"))
        self._btn_health.setToolTip(
            _t("uo_provider_health_hint", "Show validation and runtime reliability statistics for the site database.")
        )
        self._btn_health.clicked.connect(self._show_provider_health)
        sec.addWidget(self._btn_health)

        self._btn_correlate = _GhostButton(_t("osint_accounts_compare", "Compare Accounts"))
        self._btn_correlate.setToolTip(
            _t(
                "osint_accounts_compare_hint",
                "Compare evidence across found profiles; username equality alone is not proof.",
            )
        )
        self._btn_correlate.clicked.connect(self._show_account_correlation)
        self._btn_correlate.setEnabled(False)
        sec.addWidget(self._btn_correlate)

        self._btn_graph = _GhostButton(_t("uo_send_to_graph", "To Graph"))
        self._btn_graph.clicked.connect(self._send_to_graph)
        self._btn_graph.setEnabled(False)
        sec.addWidget(self._btn_graph)

        self._btn_export = _GhostButton(_t("uo_export_results", "Export"))
        self._btn_export.clicked.connect(self._export_results)
        self._btn_export.setEnabled(False)
        sec.addWidget(self._btn_export)

        root.addLayout(sec)

        # ── Progress bar ──
        self._progress = QProgressBar()
        self._progress.setTextVisible(True)
        self._progress.setFormat(_t("uo_ready", "Ready to search"))
        self._progress.setValue(0)
        self._progress.setFixedHeight(18)
        root.addWidget(self._progress)

        # ── Dashboard stats row ──
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._stat_found = _StatCard("\u2714", "0", _t("uo_found", "Found"), _GREEN)
        self._stat_total = _StatCard("\u2630", "0", _t("uo_total", "Checked"), _ACCENT)
        self._stat_errors = _StatCard("\u26a0", "0", _t("uo_errors", "Errors"), _ORANGE)
        self._stat_conf = _StatCard("\u272a", "-", _t("uo_confidence", "Confidence"), _BLUE)
        for card in (
            self._stat_found,
            self._stat_total,
            self._stat_errors,
            self._stat_conf,
        ):
            stats_row.addWidget(card)
        root.addLayout(stats_row)

        # ── Main content area (splitter) ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

        # ── Left sidebar ──
        left = _GlassPanel(alpha=0.35, radius=10)
        self._left_panel = left
        left.setMaximumWidth(210)
        left.setMinimumWidth(160)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(6, 6, 6, 6)
        left_layout.setSpacing(4)

        # Categories section
        left_layout.addWidget(_SectionLabel(_t("uo_categories", "CATEGORIES").upper()))

        # Select/deselect row
        sel_row = QHBoxLayout()
        sel_row.setSpacing(4)
        btn_all = QPushButton(_t("uo_select_all", "All"))
        btn_all.setFixedHeight(20)
        btn_all.setStyleSheet(self._mini_btn_css())
        btn_all.clicked.connect(lambda: self._set_all_categories(True))
        sel_row.addWidget(btn_all)
        btn_none = QPushButton(_t("uo_deselect_all", "None"))
        btn_none.setFixedHeight(20)
        btn_none.setStyleSheet(self._mini_btn_css())
        btn_none.clicked.connect(lambda: self._set_all_categories(False))
        sel_row.addWidget(btn_none)
        sel_row.addStretch()
        left_layout.addLayout(sel_row)

        # Category checks (scrollable)
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cat_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        cat_inner = QWidget()
        cat_inner.setStyleSheet("background: transparent;")
        cat_inner_layout = QVBoxLayout(cat_inner)
        cat_inner_layout.setContentsMargins(0, 0, 0, 0)
        cat_inner_layout.setSpacing(0)

        self._category_checks: dict[str, QCheckBox] = {}
        for cat in SITE_CATEGORIES:
            icon = CATEGORY_ICONS.get(cat, "")
            count = sum(1 for s in self._db.sites if s.category == cat)
            cb = QCheckBox(f"{icon} {cat.capitalize()} · {count}")
            cb.setChecked(True)
            cb.stateChanged.connect(self._filter_results)
            self._category_checks[cat] = cb
            cat_inner_layout.addWidget(cb)
        cat_inner_layout.addStretch()
        cat_scroll.setWidget(cat_inner)
        left_layout.addWidget(cat_scroll, 1)

        # Status filter
        left_layout.addWidget(_SectionLabel(_t("uo_status_filter", "STATUS").upper()))
        self._status_group = QButtonGroup(self)
        for i, (label, value) in enumerate(
            [
                (_t("uo_all", "All"), "all"),
                (_t("uo_found_only", "Found"), "found"),
                (_t("uo_confirmed", "Confirmed"), "confirmed"),
                (_t("uo_probable", "Probable"), "probable"),
                (_t("uo_not_found", "Not found"), "not_found"),
                (_t("uo_errors", "Errors"), "error"),
            ]
        ):
            rb = QRadioButton(label)
            rb.setProperty("filter_value", value)
            if i == 0:
                rb.setChecked(True)
            self._status_group.addButton(rb)
            left_layout.addWidget(rb)
        self._status_group.buttonClicked.connect(self._filter_results)

        # Nickname variants
        left_layout.addWidget(_SectionLabel(_t("uo_nickname_variants", "VARIANTS").upper()))
        self._nick_list = QTextEdit()
        self._nick_list.setReadOnly(True)
        self._nick_list.setMaximumHeight(120)
        self._nick_list.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(0,0,0,0.15);
                border: 1px solid rgba(192,132,252,0.1);
                border-radius: 6px;
                color: {_TEXT_SEC};
                font-size: 10px;
                font-family: 'Consolas', monospace;
            }}
        """)
        left_layout.addWidget(self._nick_list)

        # Phonetic
        self._phonetic_text = QLabel("")
        self._phonetic_text.setWordWrap(True)
        self._phonetic_text.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 9px; background: transparent;")
        left_layout.addWidget(self._phonetic_text)

        splitter.addWidget(left)

        # ── Center: results stream ──
        center = QWidget()
        center.setStyleSheet("background: transparent;")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(4, 0, 0, 0)
        center_layout.setSpacing(0)

        # Results scroll
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._results_container = QWidget()
        self._results_container.setStyleSheet("background: transparent;")
        self._results_layout = QVBoxLayout(self._results_container)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(1)
        self._results_layout.addStretch()
        self._scroll.setWidget(self._results_container)
        center_layout.addWidget(self._scroll, 1)

        # Portrait text (shown after search)
        self._portrait_text = QTextEdit()
        self._portrait_text.setReadOnly(True)
        self._portrait_text.setMaximumHeight(160)
        self._portrait_text.setVisible(False)
        self._portrait_text.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(0,0,0,0.2);
                border: 1px solid {_BORDER};
                border-radius: 8px;
                color: {_TEXT_SEC};
                font-size: 11px;
                font-family: 'Consolas', monospace;
            }}
        """)
        center_layout.addWidget(self._portrait_text)

        splitter.addWidget(center)
        splitter.setSizes([200, 800])
        root.addWidget(splitter, 1)

    def update_theme(self, theme_data: dict):
        """Called from MainWindow when user changes the theme."""
        self._theme = theme_data
        self._apply_global_style()
        self._restyle_widgets(theme_data)
