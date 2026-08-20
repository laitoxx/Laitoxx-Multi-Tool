"""Focused behavior slice for TongueWindow."""
# ruff: noqa: F405

from .tongue_window_context import *  # noqa: F403


class TongueWindowMixin2:
    def _build_summary_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(8, 8, 8, 8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(10)

        self.chain_card = QFrame()
        self.chain_card.setObjectName("ChainStatusCard")
        chain_layout = QHBoxLayout(self.chain_card)
        chain_layout.setContentsMargins(16, 12, 16, 12)
        self.chain_state_icon = _BrandIcon("ton", 38)
        chain_layout.addWidget(self.chain_state_icon)
        state_box = QVBoxLayout()
        self.chain_state = QLabel(_t("tongue_chain_waiting", "Blockchain state will appear here"))
        self.chain_state.setObjectName("PanelTitle")
        self.chain_message = QLabel(
            _t("tongue_chain_waiting_text", "Telegram owner and TON owner are verified independently.")
        )
        self.chain_message.setObjectName("Muted")
        self.chain_message.setWordWrap(True)
        state_box.addWidget(self.chain_state)
        state_box.addWidget(self.chain_message)
        chain_layout.addLayout(state_box, 1)
        self.chain_badge = QLabel(_t("tongue_not_checked", "NOT CHECKED"))
        self.chain_badge.setObjectName("SectionLabel")
        chain_layout.addWidget(self.chain_badge)
        layout.addWidget(self.chain_card)

        identity_card = QFrame()
        identity_card.setObjectName("PanelSurface")
        identity_layout = QVBoxLayout(identity_card)
        identity_layout.setContentsMargins(14, 10, 14, 12)
        identity_title = QLabel(_t("tongue_resolved_identity", "RESOLVED IDENTITIES AND CONTRACTS"))
        identity_title.setObjectName("SectionLabel")
        identity_layout.addWidget(identity_title)
        self.address_fields: dict[str, QLineEdit] = {}
        address_grid = QGridLayout()
        address_grid.setColumnStretch(1, 1)
        self._add_address_row(address_grid, 0, _t("tongue_telegram_host", "Telegram profile (host)"), "telegram")
        self._add_address_row(address_grid, 1, _t("tongue_item_contract", "NFT item contract"), "item")
        self._add_address_row(address_grid, 2, _t("tongue_chain_owner", "Blockchain owner"), "owner")
        self._add_address_row(address_grid, 3, _t("tongue_collection_contract", "Collection contract"), "collection")
        identity_layout.addLayout(address_grid)
        layout.addWidget(identity_card)

        source_card = QFrame()
        source_card.setObjectName("PanelSurface")
        source_layout = QVBoxLayout(source_card)
        source_layout.setContentsMargins(14, 10, 14, 12)
        source_title = QLabel(_t("tongue_evidence_pipeline", "EVIDENCE PIPELINE"))
        source_title.setObjectName("SectionLabel")
        source_layout.addWidget(source_title)
        self.source_table = QTableWidget(0, 3)
        self.source_table.setHorizontalHeaderLabels(
            [
                _t("tongue_col_source", "Source"),
                _t("tongue_col_status", "Status"),
                _t("tongue_col_detail", "Detail"),
            ]
        )
        self.source_table.horizontalHeader().setStretchLastSection(True)
        self.source_table.setMaximumHeight(180)
        source_layout.addWidget(self.source_table)
        layout.addWidget(source_card)

        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMaximumHeight(230)
        self.summary.setHtml(
            f"<h2>{escape(_t('tongue_empty_title', 'Start with Telegram or TON'))}</h2>"
            f"<p>{escape(_t('tongue_empty_text', 'Enter @username, a public t.me link, Gift, NFT or wallet. Public relationships are shown as evidence, not proof of identity.'))}</p>"
        )
        layout.addWidget(self.summary)
        layout.addStretch()
        scroll.setWidget(content)
        tab_layout.addWidget(scroll)
        self.tabs.addTab(tab, _t("tongue_summary", "Overview"))

    def _add_address_row(self, layout: QGridLayout, row: int, label: str, key: str) -> None:
        caption = QLabel(label)
        caption.setObjectName("Muted")
        layout.addWidget(caption, row, 0)
        field = QLineEdit()
        field.setReadOnly(True)
        field.setPlaceholderText(_t("tongue_no_chain_value", "Not available"))
        self.address_fields[key] = field
        layout.addWidget(field, row, 1)
        copy_button = QPushButton(_t("tongue_copy", "Copy"))
        copy_button.setProperty("variant", "ghost")
        copy_button.clicked.connect(lambda _=False, name=key: self._copy_address(name))
        layout.addWidget(copy_button, row, 2)
        open_button = QPushButton("↗")
        open_button.setProperty("variant", "ghost")
        open_button.setFixedWidth(38)
        open_button.clicked.connect(lambda _=False, name=key: self._open_address(name))
        layout.addWidget(open_button, row, 3)

    def _build_entities_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.entity_search = QLineEdit()
        self.entity_search.setPlaceholderText(_t("tongue_entity_search", "Filter entities, evidence or identifiers"))
        self.entity_search.textChanged.connect(self._filter_entities)
        layout.addWidget(self.entity_search)
        self.entities = QTableWidget(0, 4)
        self.entities.setHorizontalHeaderLabels(
            [
                _t("tongue_col_type", "Type"),
                _t("tongue_col_entity", "Entity"),
                _t("tongue_col_confidence", "Confidence"),
                _t("tongue_col_evidence", "Evidence"),
            ]
        )
        self.entities.setSortingEnabled(True)
        self.entities.cellDoubleClicked.connect(self._investigate_entity_row)
        self.entities.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.entities)
        self.tabs.addTab(tab, _t("tongue_entities", "Entities"))

    def _build_timeline_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.timeline_totals = QLabel(_t("tongue_timeline_empty", "No transfer totals yet"))
        self.timeline_totals.setObjectName("Muted")
        layout.addWidget(self.timeline_totals)
        self.timeline = QTableWidget(0, 6)
        self.timeline.setHorizontalHeaderLabels(
            [
                _t("tongue_col_time", "Time"),
                _t("tongue_col_flow", "Flow"),
                _t("tongue_col_counterparty", "Counterparty / transfer"),
                "TON",
                _t("tongue_col_usd", "USD at transaction"),
                _t("tongue_col_asset", "Asset / evidence"),
            ]
        )
        header = self.timeline.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.timeline.setAlternatingRowColors(True)
        self.timeline.setSortingEnabled(True)
        layout.addWidget(self.timeline)
        self.tabs.addTab(tab, _t("tongue_timeline", "Timeline"))

    def _build_graph_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        self.graph_notice = QLabel()
        self.graph_notice.setObjectName("Muted")
        layout.addWidget(self.graph_notice)
        self.graph_editor = GraphEditorWindow(tab, theme_data=self.theme_data)
        self.graph_editor.setWindowFlags(Qt.WindowType.Widget)
        self.graph_editor.setModal(False)
        self.graph_editor.set_embedded_analysis_mode(True)
        layout.addWidget(self.graph_editor, 1)
        self.tabs.addTab(tab, _t("tongue_graph", "Evidence graph"))

    def _build_json_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.raw_json = QTextEdit()
        self.raw_json.setReadOnly(True)
        self.raw_json.setObjectName("CodeText")
        layout.addWidget(self.raw_json)
        self.tabs.addTab(tab, "JSON")

    def _apply_profile(self):
        profile = self.profile_combo.currentData()
        self.depth.setValue({"quick": 1, "balanced": 3, "deep": 5}[profile])

    def _options(self) -> TongueOptions:
        profiles = {
            "quick": dict(
                tx_limit=80,
                trace_limit=5,
                nft_limit=80,
                transfer_limit=80,
                history_limit=250,
                wallet_budget=5,
                nft_budget=50,
                history_budget=300,
                profile_budget=20,
                nfts_per_wallet=40,
                chain_item_budget=1000,
            ),
            "balanced": dict(
                tx_limit=250,
                trace_limit=25,
                nft_limit=250,
                transfer_limit=250,
                history_limit=1000,
                wallet_budget=20,
                nft_budget=200,
                history_budget=3000,
                profile_budget=100,
                nfts_per_wallet=100,
                chain_item_budget=5000,
            ),
            "deep": dict(
                tx_limit=750,
                trace_limit=75,
                nft_limit=600,
                transfer_limit=600,
                history_limit=5000,
                wallet_budget=50,
                nft_budget=600,
                history_budget=10000,
                profile_budget=250,
                nfts_per_wallet=250,
                chain_item_budget=20000,
            ),
        }
        return TongueOptions(
            target=self.target_input.text(),
            target_kind=self.kind_combo.currentData(),
            api_key=self.api_key.text(),
            tonapi_key=self.tonapi_key.text(),
            blockchain_gifts=self.blockchain_gifts.isChecked(),
            recursive=self.recursive.isChecked(),
            max_depth=self.depth.value(),
            public_profiles=self.public_profiles.isChecked(),
            trace_sales=self.trace_sales.isChecked(),
            preserve_raw=self.preserve_raw.isChecked(),
            price_estimates=self.price_estimates.isChecked(),
            **profiles[self.profile_combo.currentData()],
        )

    def _start(self):
        if self._thread:
            return
        if not self.target_input.text().strip():
            self.status.setText(_t("tongue_target_required", "Enter a TON target first."))
            return
        settings.tongue = {
            **settings.tongue,
            "api_key": self.api_key.text().strip(),
            "tonapi_key": self.tonapi_key.text().strip(),
        }
        self.report = None
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.export_button.setEnabled(False)
        self.report_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.status.setText(_t("tongue_scanning", "Building public evidence chain…"))
        self._thread = _TongueThread(self._options())
        self._thread.progress.connect(self.status.setText)
        self._thread.completed.connect(self._complete)
        self._thread.failed.connect(self._failed)
        self._thread.cancelled.connect(self._cancelled)
        self._thread.finished.connect(self._thread_finished)
        self._thread.start()

    def _cancel(self):
        if self._thread:
            self.status.setText(_t("tongue_stopping", "Stopping after the current request…"))
            self._thread.cancel()
            self.cancel_button.setEnabled(False)

    def _thread_finished(self):
        thread = self._thread
        self._thread = None
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if thread:
            thread.deleteLater()
        if self._close_pending:
            self._close_pending = False
            self.close()

    def _failed(self, message: str):
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.status.setText(f"{_t('tongue_failed', 'Investigation failed')}: {message}")

    def _cancelled(self):
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.status.setText(_t("tongue_cancelled", "Investigation stopped"))

    def _complete(self, report: dict):
        self.report = report
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.status.setText(_t("tongue_complete", "Investigation complete"))
        self.export_button.setEnabled(True)
        self.report_button.setEnabled(bool((report.get("artifacts") or {}).get("html")))
        self._populate_report()
