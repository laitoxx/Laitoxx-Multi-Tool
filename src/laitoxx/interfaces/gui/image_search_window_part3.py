"""Focused behavior slice for ImageSearchWindow."""
# ruff: noqa: F405

from .image_search_window_context import *  # noqa: F403


class ImageSearchWindowMixin3:
    def _build_ctx_hashes(self) -> QWidget:
        c = self._tc()
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        outer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        vlay = QVBoxLayout(outer)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self._hashes_inner = QWidget()
        self._hashes_inner.setStyleSheet("background: transparent;")
        self._hashes_vlay = QVBoxLayout(self._hashes_inner)
        self._hashes_vlay.setContentsMargins(12, 12, 12, 12)
        self._hashes_vlay.setSpacing(8)

        self._hashes_vlay.addWidget(_section_label(_t("is_hashes_section", "File Hashes"), c["text_dim"]))

        self._hashes_placeholder = QLabel(_t("is_hashes_placeholder", "Load an image\nto compute hashes"))
        self._hashes_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hashes_placeholder.setStyleSheet(f"color: {c['text_dim']}; font-size: 12px; padding: 20px;")
        self._hashes_vlay.addWidget(self._hashes_placeholder)
        self._hashes_vlay.addStretch()

        self._hash_row_widgets: dict[str, QLineEdit] = {}

        scroll.setWidget(self._hashes_inner)
        vlay.addWidget(scroll, stretch=1)

        self._hashes_btn_area = QWidget()
        self._hashes_btn_area.setStyleSheet(f"background: {c['bg_panel']}; border-top: 1px solid {c['border']};")
        btn_lay = QVBoxLayout(self._hashes_btn_area)
        btn_lay.setContentsMargins(12, 8, 12, 12)

        cmp_btn = make_button(
            _t("is_compare_btn", "Compare with another file"),
            ghost=True,
            ac=c["accent"],
            ac2=c["accent2"],
            acd=c["accent_dim"],
            ts=c["text_sec"],
            bd=c["border"],
        )
        cmp_btn.clicked.connect(self._compare_images)
        btn_lay.addWidget(cmp_btn)

        vlay.addWidget(self._hashes_btn_area)
        return outer

    def _build_ctx_fingerprint(self) -> QWidget:
        c = self._tc()
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        lay.addWidget(_section_label(_t("Avatar Fingerprinting", "Avatar Fingerprint"), c["text_dim"]))

        hint = QLabel(
            _t(
                "osint_avatar_fingerprint_hint",
                "Generate a perceptual fingerprint or compare the loaded avatar with another image. Crops and mirrored copies are considered.",
            )
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {c['text_sec']}; font-size: 11px;")
        lay.addWidget(hint)

        self._avatar_compare_path = QLineEdit()
        self._avatar_compare_path.setReadOnly(True)
        self._avatar_compare_path.setPlaceholderText(_t("osint_avatar_second", "Optional second avatar"))
        lay.addWidget(self._avatar_compare_path)

        browse = make_button(
            _t("osint_avatar_choose_second", "Choose second avatar"),
            ghost=True,
            ac=c["accent"],
            ac2=c["accent2"],
            acd=c["accent_dim"],
            ts=c["text_sec"],
            bd=c["border"],
        )
        browse.clicked.connect(self._choose_avatar_comparison)
        lay.addWidget(browse)
        lay.addStretch()

        run = make_button(
            _t("osint_avatar_analyze", "Analyze avatar"),
            accent=True,
            ac=c["accent"],
            ac2=c["accent2"],
            acd=c["accent_dim"],
        )
        run.clicked.connect(self._run_avatar_fingerprint)
        lay.addWidget(run)
        return w

    def _build_ctx_forensics(self) -> QWidget:
        c = self._tc()
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        lay.addWidget(_section_label(_t("is_forensics_section", "Analysis"), c["text_dim"]))

        self._forensics_checks: dict[str, QCheckBox] = {}
        for key, t_key in _FORENSICS_CHECKS:
            cb = QCheckBox(_t(t_key, _FORENSICS_CHECK_FALLBACKS[t_key]))
            cb.setChecked(True)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: {c["text_sec"]};
                    font-size: 12px;
                    spacing: 6px;
                }}
                QCheckBox::indicator {{
                    width: 16px; height: 16px;
                    border: 1px solid {c["border"]};
                    border-radius: 4px;
                    background: rgba(255,255,255,0.04);
                }}
                QCheckBox::indicator:checked {{
                    background: {c["accent_dim"]};
                    border-color: {c["accent"]};
                }}
            """)
            lay.addWidget(cb)
            self._forensics_checks[key] = cb

        lay.addStretch()

        self._forensics_progress = QProgressBar()
        self._forensics_progress.setRange(0, 100)
        self._forensics_progress.setValue(0)
        self._forensics_progress.setFixedHeight(6)
        self._forensics_progress.setVisible(False)
        lay.addWidget(self._forensics_progress)

        self._forensics_btn = make_button(
            _t("is_forensics_btn", "Run Analysis"),
            accent=True,
            ac=c["accent"],
            ac2=c["accent2"],
            acd=c["accent_dim"],
        )
        self._forensics_btn.clicked.connect(self._start_forensics)
        lay.addWidget(self._forensics_btn)

        return w

    def _switch_tool(self, tool: str) -> None:
        self._current_tool = tool
        self._highlight_tool(tool)

        panels = {
            "search": self._ctx_search,
            "editor": self._ctx_editor,
            "hashes": self._ctx_hashes,
            "fingerprint": self._ctx_fingerprint,
            "forensics": self._ctx_forensics,
        }
        for key, panel in panels.items():
            panel.setVisible(key == tool)

        self._toggle_preview_btn.setVisible(tool == "editor" and self._pil_original is not None)
        self._clear_results()

        placeholder_map = {
            "search": self._show_search_placeholder,
            "editor": self._show_editor_status,
            "hashes": self._show_hashes_note,
            "fingerprint": self._show_fingerprint_placeholder,
            "forensics": self._show_forensics_placeholder,
        }
        placeholder_map[tool]()

    def _show_fingerprint_placeholder(self) -> None:
        lbl = QLabel(
            _t(
                "osint_avatar_placeholder",
                "Load an avatar, then analyze it or choose a second avatar to compare.",
            )
        )
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {self._tc()['text_dim']}; padding: 24px;")
        self._add_result_widget(lbl)

    def _choose_avatar_comparison(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            _t("osint_avatar_choose_second", "Choose second avatar"),
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff)",
        )
        if path:
            self._avatar_compare_path.setText(path)

    def _run_avatar_fingerprint(self) -> None:
        if not self._file_path:
            QMessageBox.information(self, _t("is_title", "Image Analysis"), _t("is_load_first", "Load an image first."))
            return
        try:
            second = self._avatar_compare_path.text().strip()
            result = compare_avatars(self._file_path, second) if second else avatar_fingerprint(self._file_path)
        except Exception as exc:
            QMessageBox.warning(self, _t("is_title", "Image Analysis"), str(exc))
            return

        self._clear_results()
        output = QTextEdit()
        output.setReadOnly(True)
        if second:
            similarity = result.get("similarity", 0)
            verdict = (
                _t("is_avatar_likely_same", "Likely the same avatar")
                if similarity >= 80
                else _t("is_avatar_possible_match", "Possible visual match")
                if similarity >= 55
                else _t("is_avatar_likely_different", "Likely different avatars")
            )
            output.setPlainText(
                f"{verdict}\nSimilarity: {similarity}%\nBest variant: {result.get('best_variant')}\n"
                f"Hamming distance: {result.get('hamming_distance')}\nExact file: {result.get('exact_file')}\n\n"
                + json.dumps(result, ensure_ascii=False, indent=2)
            )
        else:
            output.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))
        output.setMinimumHeight(220)
        self._add_result_widget(output)

    def _clear_results(self) -> None:
        self._search_btn = None
        while self._results_layout.count() > 1:
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_result_widget(self, w: QWidget) -> None:
        self._results_layout.insertWidget(self._results_layout.count() - 1, w)

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            _t("is_open_file_dialog", "Open Image"),
            "",
            _t(
                "is_file_filter",
                "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff *.tif);;All Files (*)",
            ),
        )
        if path:
            self._load_file(path)

    def _cleanup_threads(self) -> None:
        for prefix in ("_hash", "_search", "_forensics"):
            t = getattr(self, f"{prefix}_thread", None)
            w = getattr(self, f"{prefix}_worker", None)
            if t:
                stop_and_detach_thread(t, w)
            setattr(self, f"{prefix}_thread", None)
            setattr(self, f"{prefix}_worker", None)
