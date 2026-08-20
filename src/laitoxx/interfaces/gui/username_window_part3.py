# ruff: noqa: F405
from .username_window_context import *  # noqa: F403


class UsernameOsintMixin3:
    def _apply_global_style(self):
        td = resolved_theme(self._theme if hasattr(self, "_theme") else {})
        bg_color = td["surface_base_color"]
        text_color = td["text_primary_color"]
        btn_bg = td.get("button_bg_color", "rgba(124,58,237,0.5)")
        btn_hover = td.get("button_hover_bg_color", "rgba(139,92,246,0.7)")
        btn_border = td["border_subtle_color"]
        btn_text = td.get("button_text_color", "white")
        accent = td.get("accent_color", _ACCENT)
        txt_sec = td["text_secondary_color"]
        font_family = td.get("font_family", "Segoe UI")
        font_size = int(td.get("font_size", 13))
        # Update module-level tokens so newly created widgets pick them up
        import laitoxx.interfaces.gui.username_osint_window as _self_mod

        _self_mod._ACCENT = accent
        _self_mod._ACCENT_DIM = td.get("accent_dim_color", _ACCENT_DIM)
        _self_mod._BORDER = btn_border
        _self_mod._BORDER_FOCUS = accent
        _self_mod._TEXT_PRI = text_color
        _self_mod._TEXT_SEC = txt_sec
        _self_mod._TEXT_DIM = txt_sec  # dim ≈ sec for better readability

        self.setStyleSheet(f"""
            QDialog {{
                background: {bg_color};
                font-family: '{font_family}';
                font-size: {font_size}px;
            }}
            QPushButton {{
                background: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 7px;
                color: {btn_text};
                padding: 4px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {btn_hover};
            }}
            QLineEdit {{
                background: rgba(255,255,255,0.04);
                border: 1px solid {btn_border};
                border-radius: 6px;
                color: {text_color};
                padding: 4px 8px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {accent};
            }}
            QCheckBox {{
                color: {txt_sec};
                font-size: 11px;
                spacing: 4px;
                background: transparent;
                padding: 2px 0;
            }}
            QCheckBox::indicator {{
                width: 12px; height: 12px;
                border: 1px solid {btn_border};
                border-radius: 3px;
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {accent};
                border-color: {accent};
            }}
            QRadioButton {{
                color: {txt_sec};
                font-size: 11px;
                background: transparent;
                padding: 1px 0;
            }}
            QRadioButton::indicator {{
                width: 11px; height: 11px;
            }}
            QProgressBar {{
                background: rgba(255,255,255,0.03);
                border: 1px solid {btn_border};
                border-radius: 4px;
                color: {txt_sec};
                font-size: 10px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {btn_bg}, stop:1 {btn_hover});
                border-radius: 3px;
            }}
            QScrollBar:vertical {{
                border: none; background: transparent; width: 5px;
                margin: 0; border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {btn_border};
                min-height: 20px; border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {btn_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
            QLabel {{
                background: transparent;
                color: {text_color};
            }}
        """)
        self.setStyleSheet(self.styleSheet() + build_workspace_qss(td))

    def _mini_btn_css(self) -> str:
        td = getattr(self, "_theme", {})
        btn_bg = td.get("button_bg_color", "rgba(192,132,252,0.08)")
        btn_hov = td.get("button_hover_bg_color", "rgba(192,132,252,0.2)")
        bdr = td.get("border_color", td.get("button_border_color", _BORDER))
        txt_dim = td.get("text_secondary_color", _TEXT_DIM)
        txt_pri = td.get("text_area_text_color", _TEXT_PRI)
        return f"""
            QPushButton {{
                background: {btn_bg};
                border: 1px solid {bdr};
                border-radius: 4px;
                color: {txt_dim};
                font-size: 9px;
                padding: 0 6px;
            }}
            QPushButton:hover {{
                background: {btn_hov};
                color: {txt_pri};
            }}
        """

    def _on_search_clicked(self):
        if self._is_searching:
            self._stop_search()
            self._finish_ui()
        else:
            self._start_search()

    def _start_search(self):
        username = self._username_input.text().strip()
        if not username:
            return

        self._stop_search()
        self._results.clear()
        self._avatar_paths.clear()
        self._clear_results_ui()
        self._btn_correlate.setEnabled(False)
        self._btn_graph.setEnabled(False)
        self._btn_export.setEnabled(False)
        self._portrait_text.setVisible(False)
        self._is_searching = True
        self._btn_search.setText(_t("uo_stop", "STOP"))

        selected_cats = [c for c, cb in self._category_checks.items() if cb.isChecked()]
        mode = self._search_mode.currentData()
        categories = selected_cats if mode == "custom" else None
        sites = self._db.select(mode=mode, categories=categories)

        self._progress.setMaximum(len(sites))
        self._progress.setValue(0)
        self._progress.setFormat(f"0 / {len(sites)}")

        self._thread = QThread()
        worker_limits = {"quick": 20, "standard": 35, "full": 50, "custom": 35}
        self._worker = _CheckWorker(sites, username, max_workers=worker_limits.get(mode, 35))
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _stop_search(self):
        if self._thread:
            stop_and_detach_thread(self._thread, self._worker)
            self._thread = None
            self._worker = None

    def _cleanup_thread(self):
        self._worker = None
        self._thread = None

    def _finish_ui(self):
        self._is_searching = False
        self._btn_search.setText(_t("uo_search", "SEARCH"))
        self._btn_graph.setEnabled(bool(self._results))
        self._btn_export.setEnabled(bool(self._results))
        self._btn_correlate.setEnabled(sum(1 for result in self._results if result.is_found) >= 2)
        self._update_stats()

    def _on_progress(self, checked, total, result: CheckResult):
        self._results.append(result)
        self._progress.setValue(checked)
        found_count = sum(1 for r in self._results if r.is_found)
        self._progress.setFormat(f"{checked}/{total}  ·  {_t('uo_found', 'Found')}: {found_count}")

        if self._should_show(result):
            self._add_result_card(result)
        self._update_stats()

    def _on_finished(self, results: list[CheckResult]):
        self._results = results
        for result in self._results:
            if self._db.health.is_degraded(result.site_name):
                result.evidence.append("Provider health is degraded")
        self._finish_ui()
        self._filter_results()

        found = [r for r in results if r.is_found]
        self._progress.setFormat(f"{_t('uo_done', 'Done')}  ·  {_t('uo_found', 'Found')}: {len(found)}/{len(results)}")

        # Portrait
        username = self._username_input.text().strip()
        portrait = DigitalPortrait(username, results)
        self._portrait_text.setPlainText(portrait.to_text())
        self._portrait_text.setVisible(True)

        self._try_load_avatar(results)
        self._generate_nicknames()

    def _on_error(self, msg: str):
        self._finish_ui()
        self._progress.setFormat(f"Error: {msg[:60]}")

    def _clear_results_ui(self):
        while self._results_layout.count() > 1:
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_result_card(self, result: CheckResult):
        card = _ResultRow(result, self._results_container)
        self._results_layout.insertWidget(self._results_layout.count() - 1, card)

    def _should_show(self, result: CheckResult) -> bool:
        cat_cb = self._category_checks.get(result.category)
        if cat_cb and not cat_cb.isChecked():
            return False
        checked_btn = self._status_group.checkedButton()
        if checked_btn:
            fval = checked_btn.property("filter_value")
            if fval == "found" and not result.is_found:
                return False
            if fval == "confirmed" and result.status != "confirmed":
                return False
            if fval == "probable" and result.status != "probable":
                return False
            if fval == "not_found" and result.status != "not_found":
                return False
            if fval == "error" and result.status not in (
                "error",
                "timeout",
                "rate_limited",
                "waf_blocked",
                "network_error",
            ):
                return False
        return True

    def _filter_results(self):
        self._clear_results_ui()
        results = list(self._results)
        sort_mode = self._sort_mode.currentData() if hasattr(self, "_sort_mode") else "arrival"
        if sort_mode == "confidence":
            results.sort(key=lambda result: (-result.confidence, result.site_name.casefold()))
        elif sort_mode == "site":
            results.sort(key=lambda result: result.site_name.casefold())
        for r in results:
            if self._should_show(r):
                self._add_result_card(r)
        self._update_stats()

    def _set_all_categories(self, checked: bool):
        for cb in self._category_checks.values():
            cb.setChecked(checked)

    def _update_stats(self):
        total = len(self._results)
        found = sum(1 for r in self._results if r.is_found)
        errors = sum(1 for r in self._results if r.status in ("error", "timeout", "network_error"))
        waf = sum(1 for r in self._results if r.status == "waf_blocked")
        confs = [r.confidence for r in self._results if r.is_found and r.confidence > 0]
        avg = f"{int(sum(confs) / len(confs) * 100)}%" if confs else "-"

        self._stat_found.set_value(str(found))
        self._stat_total.set_value(str(total))
        self._stat_errors.set_value(str(errors + waf))
        self._stat_conf.set_value(avg)
