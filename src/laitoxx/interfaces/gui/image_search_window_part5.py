"""Focused behavior slice for ImageSearchWindow."""
# ruff: noqa: F405

from .image_search_window_context import *  # noqa: F403


class ImageSearchWindowMixin5:
    def _apply_edits(self) -> None:
        if not HAS_PIL or self._pil_original is None:
            return
        img = self._pil_original.copy()
        vals = {k: s.value() for k, s in self._sliders.items()}

        def _apply(v: int, fn):
            return fn() if v != 0 else img

        v = vals["brightness"]
        if v != 0:
            img = ImageEnhance.Brightness(img).enhance(1.0 + v / 100)
        v = vals["contrast"]
        if v != 0:
            img = ImageEnhance.Contrast(img).enhance(1.0 + v / 100)
        v = vals["saturation"]
        if v != 0:
            img = ImageEnhance.Color(img).enhance(1.0 + v / 100)
        v = vals["sharpness"]
        if v != 0:
            img = ImageEnhance.Sharpness(img).enhance(1.0 + v / 50)
        v = vals["exposure"]
        if v != 0:
            delta = int(v * 2.55)
            img = img.convert("RGB").point(lambda x: min(255, max(0, x + delta)))
        v = vals["shadows"]
        if v != 0:
            img = img.convert("RGB").point(lambda x, _v=v: min(255, max(0, x + int(_v * 0.8))) if x < 128 else x)
        v = vals["highlights"]
        if v != 0:
            img = img.convert("RGB").point(lambda x, _v=v: min(255, max(0, x + int(_v * 0.8))) if x >= 128 else x)
        v = vals["warmth"]
        if v != 0:
            r, g, b = img.convert("RGB").split()
            shift = int(abs(v) * 0.6)
            if v > 0:
                r = r.point(lambda x: min(255, x + shift))
                b = b.point(lambda x: max(0, x - shift))
            else:
                r = r.point(lambda x: max(0, x - shift))
                b = b.point(lambda x: min(255, x + shift))
            img = Image.merge("RGB", (r, g, b))
        v = vals["fade"]
        if v > 0:
            gray = Image.new("RGB", img.size, (128, 128, 128))
            img = Image.blend(img.convert("RGB"), gray, alpha=(v / 100) * 0.5)
        v = vals["grain"]
        if v > 0:
            noise_layer = Image.frombytes(
                "L",
                img.size,
                bytes([min(255, max(0, 128 + random.randint(-v, v))) for _ in range(img.size[0] * img.size[1])]),
            )
            img = Image.merge(
                "RGB",
                [Image.blend(ch, noise_layer, alpha=v / 300) for ch in img.convert("RGB").split()],
            )
        v = vals["noise"]
        if v > 0:
            img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
            img = ImageEnhance.Sharpness(img).enhance(1.0 + v / 200)
        v = vals["blur"]
        if v > 0:
            img = img.filter(ImageFilter.GaussianBlur(radius=v / 20))

        self._pil_edited = img
        if not self._show_original:
            self._update_preview(img)

        active = [
            f"{_t(t_key, key.capitalize())} {'+' if vals[key] > 0 else ''}{vals[key]}"
            for key, t_key, *_ in _SLIDER_DEFS
            if vals[key] != 0
        ]
        status = (
            _t("is_edited", "Edited: {changes}").format(changes=", ".join(active))
            if active
            else _t("is_no_changes", "No changes")
        )
        if hasattr(self, "_editor_status_lbl"):
            self._editor_status_lbl.setText(status)

    def _toggle_original(self) -> None:
        self._show_original = not self._show_original
        if self._show_original:
            self._toggle_preview_btn.setText(_t("is_toggle_show_result", "Show Result"))
            self._update_preview(self._pil_original)
        else:
            self._toggle_preview_btn.setText(_t("is_toggle_before_after", "Before / After"))
            self._update_preview(self._pil_edited)

    def _reset_sliders(self) -> None:
        for sl in self._sliders.values():
            sl.blockSignals(True)
            sl.setValue(0)
            sl.blockSignals(False)
        for lbl in self._slider_labels.values():
            lbl.setText("+0")
        if self._pil_original:
            self._pil_edited = self._pil_original.copy()
            self._update_preview(self._pil_edited)
        if hasattr(self, "_editor_status_lbl"):
            self._editor_status_lbl.setText(_t("is_no_changes", "No changes"))

    def _save_edited(self) -> None:
        if not self._pil_edited:
            QMessageBox.information(
                self,
                _t("error", "Error"),
                _t("is_no_image", "Please load an image first."),
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            _t("is_save_file_dialog", "Save Image"),
            "",
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;WebP (*.webp)",
        )
        if path:
            try:
                self._pil_edited.convert("RGB").save(path)
                self._hdr_status.setText(_t("is_saved", "Saved"))
                QMessageBox.information(
                    self,
                    _t("is_saved", "Saved"),
                    f"{_t('is_saved', 'Saved')}:\n{path}",
                )
            except Exception as e:
                QMessageBox.critical(self, _t("error", "Error"), str(e))

    def _show_hashes_note(self) -> None:
        c = self._tc()
        lbl = QLabel(_t("is_hashes_note", "Hashes are shown in the right panel."))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {c['text_dim']}; font-size: 13px; padding: 20px;")
        self._add_result_widget(lbl)

    def _compute_hashes(self) -> None:
        if not self._file_path or not self._pil_original:
            return
        self._hash_thread = QThread()
        self._hash_worker = HashWorker(self._file_path, self._pil_original)
        self._hash_worker.moveToThread(self._hash_thread)
        self._hash_thread.started.connect(self._hash_worker.run)
        self._hash_worker.finished.connect(self._show_hashes)
        self._hash_worker.finished.connect(self._hash_thread.quit)
        self._hash_thread.start()
        self._hdr_status.setText(_t("is_computing_hashes", "Computing hashes…"))

    def _show_hashes(self, hashes: dict) -> None:
        self._hashes = hashes
        self._hdr_status.setText(_t("is_hashes_done", "Hashes computed"))

        while self._hashes_vlay.count() > 1:
            item = self._hashes_vlay.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                self._hashes_vlay.removeItem(item)

        self._hashes_placeholder.setVisible(False)
        self._hash_row_widgets.clear()

        for key in _HASH_ORDER:
            self._add_hash_row(key, hashes.get(key, "-"))

        self._hashes_vlay.addStretch()

    def _add_hash_row(self, name: str, value: str) -> None:
        c = self._tc()
        row_w = QWidget()
        row_w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(row_w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        lbl = QLabel(name)
        lbl.setStyleSheet(f"color: {c['text_dim']}; font-size: 10px; font-weight: 700; letter-spacing: 0.8px;")
        lay.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(4)

        edit = QLineEdit(value)
        edit.setReadOnly(True)
        edit.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.04);
                border: 1px solid {c["border"]};
                border-radius: 5px;
                color: {c["text_pri"]};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10px;
                padding: 3px 6px;
            }}
        """)
        row.addWidget(edit, stretch=1)
        self._hash_row_widgets[name] = edit

        copy_btn = QPushButton("⎘")
        copy_btn.setFixedSize(24, 24)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setToolTip(_t("is_copy_tooltip", "Copy"))
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.05);
                border: 1px solid {c["border"]};
                border-radius: 4px;
                color: {c["text_sec"]};
                font-size: 12px;
            }}
            QPushButton:hover {{ background: transparent; color: {c["accent"]}; }}
        """)
        copy_btn.clicked.connect(
            lambda _, v=value, b=copy_btn: (
                QApplication.clipboard().setText(v),
                b.setText("✓"),
                QTimer.singleShot(1200, lambda: b.setText("⎘")),
            )
        )
        row.addWidget(copy_btn)
        lay.addLayout(row)

        idx = max(0, self._hashes_vlay.count() - 1)
        self._hashes_vlay.insertWidget(idx, row_w)

    def _compare_images(self) -> None:
        if not HAS_PIL:
            QMessageBox.information(self, _t("error", "Error"), _t("is_no_pil", "Pillow not installed."))
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            _t("is_compare_file_dialog", "Select file to compare"),
            "",
            _t(
                "is_compare_file_filter",
                "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)",
            ),
        )
        if not path:
            return
        try:
            with open(path, "rb") as fh:
                data = fh.read()
            other_hashes = {
                "MD5": hashlib.md5(data).hexdigest(),
                "SHA-1": hashlib.sha1(data).hexdigest(),
                "SHA-256": hashlib.sha256(data).hexdigest(),
            }
        except Exception as e:
            QMessageBox.critical(self, _t("error", "Error"), str(e))
            return

        lines = []
        for k in ("MD5", "SHA-1", "SHA-256"):
            mine = self._hashes.get(k, "")
            other = other_hashes.get(k, "")
            match = _t("is_hash_match", "✅ match") if mine == other else _t("is_hash_differ", "❌ differ")
            lines.append(f"{k}: {match}")

        QMessageBox.information(
            self,
            _t("is_compare_title", "Hash Comparison"),
            _t("is_compare_with", "Compared with: {name}").format(name=os.path.basename(path))
            + "\n\n"
            + "\n".join(lines),
        )
