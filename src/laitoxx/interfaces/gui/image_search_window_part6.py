"""Focused behavior slice for ImageSearchWindow."""
# ruff: noqa: F405

from .image_search_window_context import *  # noqa: F403


class ImageSearchWindowMixin6:
    def _show_forensics_placeholder(self) -> None:
        c = self._tc()
        lbl = QLabel(_t("is_forensics_placeholder", "Click «Run Analysis»\nto start forensics"))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {c['text_dim']}; font-size: 13px; padding: 20px;")
        lbl.setWordWrap(True)
        self._add_result_widget(lbl)

    def _start_forensics(self) -> None:
        if not self._pil_original:
            QMessageBox.information(
                self,
                _t("error", "Error"),
                _t("is_no_image", "Please load an image first."),
            )
            return
        checks = {k: cb.isChecked() for k, cb in self._forensics_checks.items()}
        if not any(checks.values()):
            QMessageBox.information(
                self,
                _t("error", "Error"),
                _t("is_no_checks", "Select at least one check."),
            )
            return

        self._forensics_btn.setEnabled(False)
        self._forensics_btn.setText(_t("is_forensics_btn_running", "Analysing…"))
        self._forensics_progress.setValue(0)
        self._forensics_progress.setVisible(True)
        self._hdr_status.setText(_t("is_forensics_running", "Forensics…"))
        self._clear_results()

        self._forensics_thread = QThread()
        self._forensics_worker = ForensicsWorker(self._pil_original, self._file_path or "", checks)
        self._forensics_worker.moveToThread(self._forensics_thread)
        self._forensics_thread.started.connect(self._forensics_worker.run)
        self._forensics_worker.progress.connect(self._forensics_progress.setValue)
        self._forensics_worker.finished.connect(self._on_forensics_done)
        self._forensics_worker.finished.connect(self._forensics_thread.quit)
        self._forensics_thread.start()

    def _on_forensics_done(self, report: dict) -> None:
        self._forensics_btn.setEnabled(True)
        self._forensics_btn.setText(_t("is_forensics_btn", "Run Analysis"))
        self._forensics_progress.setValue(100)
        self._hdr_status.setText(_t("is_forensics_done", "Forensics complete"))
        self._render_forensics_report(report)

    def _render_forensics_report(self, report: dict) -> None:
        self._clear_results()
        c = self._tc()
        ac, tp, ts, td = c["accent"], c["text_pri"], c["text_sec"], c["text_dim"]

        te = QTextEdit()
        te.setReadOnly(True)
        te.setMinimumHeight(220)
        te.setStyleSheet(f"""
            QTextEdit {{
                background: {c["bg_card"]};
                border: 1px solid {c["border"]};
                border-radius: 10px;
                color: {tp};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 12px;
            }}
        """)

        html_parts: list[str] = []
        suspicious_count = 0
        verdict_notes: list[str] = []
        ela_image = None

        # EXIF
        if "exif" in report:
            exif = report["exif"]
            if "error" in exif:
                html_parts.append(
                    f'<p><span style="color:{ORANGE}">⚠ EXIF: {_t("error", "Error")} - {exif["error"]}</span></p>'
                )
            else:
                html_parts.append(f'<p><b style="color:{ac}">{_t("is_exif_section", "📋 EXIF / Metadata")}</b></p>')
                raw = exif.get("raw", {})
                for k, v in list(raw.items())[:20]:
                    html_parts.append(
                        f'<p style="margin:1px 0"><span style="color:{td}">{k}:</span> '
                        f'<span style="color:{ts}">{v}</span></p>'
                    )
                flags = exif.get("flags", [])
                for fl in flags:
                    html_parts.append(f'<p style="color:{ORANGE}">⚠ {fl}</p>')
                    suspicious_count += 1
                    verdict_notes.append(fl)
                if not flags and raw:
                    html_parts.append(
                        f'<p style="color:{GREEN}">{_t("is_exif_no_flags", "✓ No suspicious signs found")}</p>'
                    )

        # ELA
        if "ela" in report:
            ela = report["ela"]
            if "error" in ela:
                html_parts.append(
                    f'<p><span style="color:{ORANGE}">⚠ ELA: {_t("error", "Error")} - {ela["error"]}</span></p>'
                )
            else:
                ela_image = ela.get("ela_image")
                mean_v = ela.get("mean", 0)
                is_susp = ela.get("verdict", "") == "подозрительно"
                color = RED if is_susp else GREEN
                verdict_str = (
                    _t("is_ela_verdict_suspicious", "suspicious") if is_susp else _t("is_ela_verdict_ok", "normal")
                )
                html_parts.append(
                    f'<p><b style="color:{ac}">{_t("is_ela_section", "🔎 ELA (Error Level Analysis)")}</b></p>'
                )
                html_parts.append(
                    f'<p><b style="color:{color}">{mean_v}</b> - <span style="color:{color}">{verdict_str}</span></p>'
                )
                if is_susp:
                    suspicious_count += 1
                    verdict_notes.append(f"ELA: {mean_v}")

        # Clone
        if "clone" in report:
            cl = report["clone"]
            if "error" in cl:
                html_parts.append(
                    f'<p><span style="color:{ORANGE}">⚠ {_t("is_clone_section", "Clone")}: '
                    f"{_t('error', 'Error')} - {cl['error']}</span></p>"
                )
            else:
                dupes = cl.get("duplicate_blocks", 0)
                susp = cl.get("suspicious", False)
                color = RED if susp else GREEN
                html_parts.append(f'<p><b style="color:{ac}">{_t("is_clone_section", "🔁 Clone Detection")}</b></p>')
                susp_str = _t("is_clone_suspicious", "⚠ possible clones") if susp else _t("is_clone_ok", "✓ normal")
                html_parts.append(
                    f'<p><b style="color:{color}">{dupes}</b> - <span style="color:{color}">{susp_str}</span></p>'
                )
                if susp:
                    suspicious_count += 1
                    verdict_notes.append(f"{_t('is_clone_section', 'Clone')}: {dupes}")

        # Noise
        if "noise" in report:
            ns = report["noise"]
            if "error" in ns:
                html_parts.append(
                    f'<p><span style="color:{ORANGE}">⚠ {_t("is_noise_section", "Noise")}: '
                    f"{_t('error', 'Error')} - {ns['error']}</span></p>"
                )
            else:
                susp = ns.get("suspicious", False)
                ratio = ns.get("ratio", 0)
                color = RED if susp else GREEN
                html_parts.append(f'<p><b style="color:{ac}">{_t("is_noise_section", "- Noise Analysis")}</b></p>')
                susp_str = _t("is_noise_suspicious", "⚠ uneven noise") if susp else _t("is_noise_ok", "✓ even")
                html_parts.append(
                    f'<p><b style="color:{color}">{ratio}</b> - <span style="color:{color}">{susp_str}</span></p>'
                )
                if susp:
                    suspicious_count += 1
                    verdict_notes.append(f"{_t('is_noise_section', 'Noise')}: {ratio}")

        # Color
        if "color" in report:
            col = report["color"]
            if "error" in col:
                html_parts.append(
                    f'<p><span style="color:{ORANGE}">⚠ {_t("is_color_section", "Color")}: '
                    f"{_t('error', 'Error')} - {col['error']}</span></p>"
                )
            else:
                wb_map = {
                    "тёплый": _t("is_wb_warm", "warm"),
                    "холодный": _t("is_wb_cool", "cool"),
                    "нейтральный": _t("is_wb_neutral", "neutral"),
                }
                wb = wb_map.get(col.get("white_balance", ""), col.get("white_balance", "-"))
                r, g, b = (
                    col.get("r_mean", 0),
                    col.get("g_mean", 0),
                    col.get("b_mean", 0),
                )
                html_parts.append(
                    f'<p><b style="color:{ac}">{_t("is_color_section", "🎨 Color & White Balance")}</b></p>'
                )
                html_parts.append(
                    f"<p>{_t('is_color_channels', 'R/G/B channels:')} "
                    f'<span style="color:#ff7675">{r}</span> / '
                    f'<span style="color:{GREEN}">{g}</span> / '
                    f'<span style="color:#74b9ff">{b}</span></p>'
                )
                html_parts.append(f"<p>{_t('is_color_wb', 'White balance: {wb}').format(wb=wb)}</p>")

        te.setHtml("<html><body>" + "".join(html_parts) + "</body></html>")
        self._add_result_widget(te)

        # ELA image
        if ela_image is not None:
            ela_lbl_hdr = QLabel(_t("is_ela_image_label", "ELA image:"))
            ela_lbl_hdr.setStyleSheet(f"color: {c['text_sec']}; font-size: 12px; padding: 4px 0 2px 0;")
            self._add_result_widget(ela_lbl_hdr)

            ela_px = pil_to_qpixmap(ela_image)
            ela_scaled = ela_px.scaledToWidth(
                min(ela_px.width(), 500),
                Qt.TransformationMode.SmoothTransformation,
            )
            ela_lbl = QLabel()
            ela_lbl.setPixmap(ela_scaled)
            ela_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ela_lbl.setStyleSheet(f"border: 1px solid {c['border']}; border-radius: 6px;")
            self._add_result_widget(ela_lbl)

        # Verdict banner
        if suspicious_count == 0:
            verdict_color = GREEN
            verdict_text = _t("is_verdict_clean", "✅  No manipulation signs detected")
        elif suspicious_count == 1:
            verdict_color = ORANGE
            verdict_text = _t("is_verdict_warn", "⚠  {count} suspicious sign detected").format(count=suspicious_count)
        else:
            verdict_color = RED
            verdict_text = _t("is_verdict_danger", "🚨  {count} suspicious signs detected").format(
                count=suspicious_count
            )

        if verdict_notes:
            verdict_text += "\n• " + "\n• ".join(verdict_notes)

        verdict_banner = QLabel(verdict_text)
        verdict_banner.setWordWrap(True)
        verdict_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        verdict_banner.setStyleSheet(f"""
            background: {verdict_color}22;
            border: 1px solid {verdict_color}66;
            border-radius: 10px;
            color: {verdict_color};
            font-size: 13px;
            font-weight: 600;
            padding: 12px 16px;
            margin-top: 6px;
        """)
        self._add_result_widget(verdict_banner)
