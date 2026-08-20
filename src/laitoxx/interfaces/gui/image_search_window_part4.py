"""Focused behavior slice for ImageSearchWindow."""
# ruff: noqa: F405

from .image_search_window_context import *  # noqa: F403


class ImageSearchWindowMixin4:
    def _load_file(self, path: str) -> None:
        self._cleanup_threads()
        if not HAS_PIL:
            QMessageBox.critical(self, _t("error", "Error"), _t("is_no_pil", "Pillow not installed."))
            return
        if not os.path.isfile(path):
            QMessageBox.warning(
                self,
                _t("error", "Error"),
                f"{_t('file_not_found', 'File not found')}:\n{path}",
            )
            return
        try:
            pil = Image.open(path)
            pil.load()
        except Exception as e:
            QMessageBox.critical(self, _t("error", "Error"), str(e))
            return

        self._file_path = path
        self._pil_original = pil.copy()
        self._pil_edited = pil.copy()
        self._hashes = {}
        self._search_urls = {}

        fname = os.path.basename(path)
        fsize = os.path.getsize(path)
        w, h = pil.size
        self._hdr_filename.setText(fname)
        self._hdr_size.setText(self._fmt_size(fsize))
        self._hdr_dims.setText(f"{w} × {h} px")
        self._hdr_status.setText(_t("is_loaded", "Loaded"))

        self._update_preview(pil)
        self._switch_tool("search")
        self._compute_hashes()

    @staticmethod
    def _fmt_size(sz: int) -> str:
        if sz < 1024:
            return f"{sz} Б"
        if sz < 1024 * 1024:
            return f"{sz / 1024:.1f} КБ"
        return f"{sz / 1024 / 1024:.2f} МБ"

    def _update_preview(self, pil_img: Image.Image | None = None) -> None:
        if pil_img is None:
            pil_img = self._pil_edited
        if pil_img is None:
            return
        self._preview_label.set_pixmap(pil_to_qpixmap(pil_img))

    def _show_search_placeholder(self) -> None:
        c = self._tc()
        self._search_btn = make_button(
            _t("is_search_btn", "Upload & Search"),
            accent=True,
            ac=c["accent"],
            ac2=c["accent2"],
            acd=c["accent_dim"],
        )
        self._search_btn.clicked.connect(self._start_search)
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wlay = QHBoxLayout(wrapper)
        wlay.setContentsMargins(0, 8, 0, 8)
        wlay.addStretch()
        wlay.addWidget(self._search_btn)
        wlay.addStretch()
        self._add_result_widget(wrapper)

    def _start_search(self) -> None:
        if not self._pil_original:
            QMessageBox.information(
                self,
                _t("error", "Error"),
                _t("is_no_image", "Please load an image first."),
            )
            return
        if not HAS_REQUESTS:
            QMessageBox.warning(
                self,
                _t("error", "Error"),
                _t(
                    "is_no_requests",
                    "requests library not installed.\nSearch unavailable.",
                ),
            )
            return

        selected = [eng for eng, btn in self._engine_buttons.items() if btn.isChecked()]
        if not selected:
            QMessageBox.information(
                self,
                _t("error", "Error"),
                _t("is_no_engines", "Select at least one search engine."),
            )
            return

        c = self._tc()
        if self._search_btn:
            self._search_btn.setEnabled(False)
            self._search_btn.setText(_t("is_searching_btn", "Uploading..."))
        self._hdr_status.setText(_t("is_searching", "Loading image…"))
        self._clear_results()

        prog_lbl = QLabel(_t("is_upload_progress", "Uploading to server…"))
        prog_lbl.setStyleSheet(f"color: {c['text_sec']}; padding: 8px;")
        self._add_result_widget(prog_lbl)

        self._search_thread = QThread()
        self._search_worker = SearchWorker(self._pil_original, selected)
        self._search_worker.moveToThread(self._search_thread)
        self._search_thread.started.connect(self._search_worker.run)
        self._search_worker.finished.connect(self._on_search_done)
        self._search_worker.error.connect(self._on_search_error)
        self._search_worker.finished.connect(self._search_thread.quit)
        self._search_worker.error.connect(self._search_thread.quit)
        self._search_thread.start()

    def _on_search_error(self, msg: str) -> None:
        if self._search_btn:
            self._search_btn.setEnabled(True)
            self._search_btn.setText(_t("is_search_btn", "Upload & Search"))
        self._hdr_status.setText(_t("is_search_error", "Search error"))
        self._clear_results()
        err = QLabel(f"{_t('error', 'Error')}: {msg}")
        err.setStyleSheet(f"color: {RED}; padding: 8px;")
        err.setWordWrap(True)
        self._add_result_widget(err)

    def _on_search_done(self, urls: dict) -> None:
        c = self._tc()
        self._search_urls = urls
        if self._search_btn:
            self._search_btn.setEnabled(True)
            self._search_btn.setText(_t("is_search_btn", "Upload & Search"))
        self._hdr_status.setText(_t("is_search_done", "Engines found: {count}").format(count=len(urls)))
        self._clear_results()

        if not urls:
            lbl = QLabel(_t("is_no_results", "No results."))
            lbl.setStyleSheet(f"color: {c['text_dim']}; padding: 8px;")
            self._add_result_widget(lbl)
            return

        for key, engines in _ENGINE_GROUPS:
            grp_name = _t(key, _ENGINE_GROUP_FALLBACKS[key])
            shown = [e for e in engines if e in urls]
            if not shown:
                continue
            hdr = QLabel(grp_name.upper())
            hdr.setStyleSheet(f"""
                color: {c["text_dim"]};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.2px;
                padding: 8px 0 2px 0;
            """)
            self._add_result_widget(hdr)
            for eng in shown:
                self._add_result_widget(self._make_engine_result_card(eng, urls[eng]))

    def _make_engine_result_card(self, engine: str, url: str) -> QWidget:
        c = self._tc()
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background: {c["bg_card"]};
                border: 1px solid {c["border"]};
                border-radius: 8px;
            }}
        """)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(8)

        name_lbl = QLabel(engine)
        name_lbl.setStyleSheet(f"color: {c['text_pri']}; font-size: 12px; background: transparent; border: none;")
        lay.addWidget(name_lbl, stretch=1)

        open_btn = make_button(
            _t("is_open_btn", "Open"),
            accent=True,
            ac=c["accent"],
            ac2=c["accent2"],
            acd=c["accent_dim"],
        )
        open_btn.setFixedHeight(28)
        open_btn.setStyleSheet(open_btn.styleSheet() + "padding: 2px 10px; font-size: 11px;")
        open_btn.clicked.connect(lambda _, u=url: QDesktopServices.openUrl(QUrl(u)))
        lay.addWidget(open_btn)

        copy_btn = make_button(
            "⎘",
            ghost=True,
            ac=c["accent"],
            ac2=c["accent2"],
            acd=c["accent_dim"],
            ts=c["text_sec"],
            bd=c["border"],
        )
        copy_btn.setFixedSize(28, 28)
        copy_btn.setToolTip(_t("is_copy_link_tooltip", "Copy link"))
        copy_btn.clicked.connect(
            lambda _, u=url: (
                QApplication.clipboard().setText(u),
                copy_btn.setText("✓"),
                QTimer.singleShot(1500, lambda: copy_btn.setText("⎘")),
            )
        )
        lay.addWidget(copy_btn)
        return card

    def _show_editor_status(self) -> None:
        c = self._tc()
        self._editor_status_lbl = QLabel(_t("is_editor_hint", "Use sliders to edit"))
        self._editor_status_lbl.setStyleSheet(f"color: {c['text_dim']}; font-size: 12px; padding: 8px;")
        self._editor_status_lbl.setWordWrap(True)
        self._add_result_widget(self._editor_status_lbl)

    def _on_slider_changed(self, key: str, value: int, label: QLabel) -> None:
        sign = "+" if value >= 0 else ""
        label.setText(f"{sign}{value}")
        self._edit_timer.start()
