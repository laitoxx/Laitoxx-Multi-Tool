"""Focused behavior slice for MetadataViewerWindow."""
# ruff: noqa: F405

from .gui_window_context import *  # noqa: F403


class MetadataViewerWindowMixin2:
    def _add_file_to_list(self, filepath):
        # Prevent duplicates
        for i in range(self.file_list.count()):
            if self.file_list.item(i).data(Qt.ItemDataRole.UserRole) == filepath:
                return

        # We'll use QListWidgetItem
        from PyQt6.QtWidgets import QListWidgetItem

        list_item = QListWidgetItem(os.path.basename(filepath))
        list_item.setData(Qt.ItemDataRole.UserRole, filepath)
        self.file_list.addItem(list_item)
        self.file_list.setCurrentItem(list_item)
        self.content_stack.setCurrentWidget(self.content_page)
        self._load_file(filepath)

    def _copy_current_path(self):
        if not self.current_filepath:
            return
        from PyQt6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.current_filepath)

    def _remove_current_file(self):
        row = self.file_list.currentRow()
        if row < 0:
            return
        self.file_list.takeItem(row)
        if self.file_list.count():
            next_row = min(row, self.file_list.count() - 1)
            self.file_list.setCurrentRow(next_row)
            self._load_file(self.file_list.item(next_row).data(Qt.ItemDataRole.UserRole))
        else:
            self.current_filepath = None
            self.current_metadata = {}
            self.content_stack.setCurrentWidget(self.empty_page)
            self.lbl_status.setText(translator.get("metadata_drag_drop"))

    def _on_file_selected(self, item):
        filepath = item.data(Qt.ItemDataRole.UserRole)
        self._load_file(filepath)

    def _load_file(self, filepath):
        self.current_filepath = filepath
        self.content_stack.setCurrentWidget(self.content_page)
        self.file_name_label.setText(os.path.basename(filepath))
        try:
            size = os.path.getsize(filepath)
            self.file_meta_label.setText(
                f"{os.path.splitext(filepath)[1].upper().lstrip('.') or 'FILE'} · {self._human_size(size)}"
            )
        except OSError:
            self.file_meta_label.clear()
        self.lbl_status.setText(f"Loading metadata for {os.path.basename(filepath)}...")

        supported = os.path.splitext(filepath)[1].lower() in {
            ".pdf",
            ".docx",
            ".xlsx",
            ".pptx",
            ".odt",
            ".png",
            ".jpg",
            ".jpeg",
            ".tiff",
            ".webp",
            ".bmp",
        }
        self.tabs.setTabEnabled(self.identity_tab_index, supported)
        self.current_identity = {}
        self.identity_output.clear()
        if supported:
            self.identity_output.setPlainText("Analyzing document identity clues...")

        if not hasattr(self, "_active_workers"):
            self._active_workers = []

        worker = WorkerThread(filepath)

        def on_finished(data):
            if worker in self._active_workers:
                self._active_workers.remove(worker)
            # Only update UI if this is STILL the currently selected file!
            if self.current_filepath == filepath:
                self._on_load_finished(data)

        worker.finished_signal.connect(on_finished)
        self._active_workers.append(worker)
        worker.start()

        if supported:
            identity_worker = IdentityWorkerThread(filepath)

            def on_identity_finished(data):
                if identity_worker in self._active_workers:
                    self._active_workers.remove(identity_worker)
                if self.current_filepath == filepath:
                    self._on_identity_finished(data)

            identity_worker.finished_signal.connect(on_identity_finished)
            self._active_workers.append(identity_worker)
            identity_worker.start()

    def _on_identity_finished(self, data):
        if "error" in data and len(data) == 1:
            self.current_identity = {}
            self.identity_output.setPlainText(f"Identity analysis failed: {data['error']}")
            return
        self.current_identity = data
        identity = data.get("identity", {})
        entities = data.get("entities", [])
        lines = [
            f"SHA-256: {data.get('sha256', 'N/A')}",
            f"File size: {data.get('size', 0)} bytes",
            "",
            "Identity metadata:",
        ]
        if identity:
            lines.extend(f"  {key}: {value}" for key, value in identity.items())
        else:
            lines.append("  No explicit author or creator fields found.")
        lines.extend(("", f"Extracted entities ({len(entities)}):"))
        if entities:
            lines.extend(f"  [{item.get('kind', 'unknown')}] {item.get('value', '')}" for item in entities)
        else:
            lines.append("  No identity-related entities found.")
        lines.extend(
            ("", "Full metadata:", json.dumps(data.get("metadata", {}), ensure_ascii=False, indent=2, default=str))
        )
        self.identity_output.setPlainText("\n".join(lines))

    def _on_load_finished(self, data):
        self.lbl_status.setText("Metadata loaded.")
        if "error" in data and len(data) == 1:
            QMessageBox.warning(self, "Error", data["error"])
            return

        self.current_metadata = data
        self._populate_raw_table(data)
        self._populate_forensics(data)
        self._populate_overview(data)
        self.btn_export.setEnabled(True)

    def _populate_raw_table(self, data):
        self.table_meta.setRowCount(0)
        row = 0
        for k, v in data.items():
            if k == "ExtractedWith":
                v = ", ".join(v)
            key = str(k)
            if ":" in key:
                group, prop = key.split(":", 1)
            else:
                group, prop = "File", key
            source = group if group not in {"File", "Composite"} else "Local"
            self.table_meta.insertRow(row)
            self.table_meta.setItem(row, 0, QTableWidgetItem(group))
            self.table_meta.setItem(row, 1, QTableWidgetItem(prop))
            self.table_meta.setItem(row, 2, QTableWidgetItem(str(v)))
            self.table_meta.setItem(row, 3, QTableWidgetItem(source))
            row += 1

    def _filter_metadata(self, query):
        query = query.strip().casefold()
        for row in range(self.table_meta.rowCount()):
            values = [self.table_meta.item(row, col) for col in range(self.table_meta.columnCount())]
            visible = not query or any(item and query in item.text().casefold() for item in values)
            self.table_meta.setRowHidden(row, not visible)

    @staticmethod
    def _human_size(size):
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
            value /= 1024

    def _populate_overview(self, data):
        path = self.current_filepath or ""
        try:
            stat = os.stat(path)
            size = self._human_size(stat.st_size)
            created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M")
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        except OSError:
            size = created = modified = "-"
        width = data.get("ImageWidth") or data.get("EXIF:ImageWidth") or data.get("File:ImageWidth")
        height = data.get("ImageHeight") or data.get("EXIF:ImageHeight") or data.get("File:ImageHeight")
        author = next(
            (data.get(key) for key in ("Author", "Creator", "EXIF:Artist", "PDF:Author") if data.get(key)), "-"
        )
        values = {
            "type": os.path.splitext(path)[1].upper().lstrip(".") or "-",
            "size": size,
            "dimensions": f"{width} × {height}" if width and height else "-",
            "created": created,
            "modified": modified,
            "author": str(author),
        }
        for key, value in values.items():
            self.overview_labels[key].setText(value)

    def _populate_forensics(self, data):
        self.list_anomalies.clear()

        # Privacy Score
        privacy = MetadataForensics.calculate_privacy_score(data)
        score = privacy["score"]

        self.lbl_privacy_score.setText(f"{translator.get('Privacy Score:')} {score}/100")
        self.lbl_privacy_rec.setText(privacy["message"])

        for leak in privacy["leaks"]:
            self.list_anomalies.addItem(f"Privacy Leak: {leak[0]} -> {leak[1]}")

        # Anomalies
        anomalies = MetadataForensics.detect_anomalies(data)
        for a in anomalies:
            self.list_anomalies.addItem(a)

    def _sanitize_current(self):
        if not self.current_filepath:
            return
        reply = QMessageBox.question(self, "Confirm", "This will permanently wipe metadata. Continue?")
        if reply == QMessageBox.StandardButton.Yes:
            success = MetadataSanitizer.sanitize(self.current_filepath)
            if success:
                QMessageBox.information(self, "Success", "File sanitized successfully!")
                self._load_file(self.current_filepath)  # Reload clean
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Sanitization failed. Do you have ExifTool installed?",
                )

    def _smart_rename(self):
        if not self.current_filepath or not self.current_metadata:
            return
        pattern = self.input_rename_pattern.text().strip()
        if not pattern:
            return

        new_name = pattern
        import re

        # Find all [Tag] in pattern
        tags = re.findall(r"\[(.*?)\]", pattern)
        for tag in tags:
            val = str(self.current_metadata.get(tag, f"UNKNOWN_{tag}"))
            # clean invalid filename chars
            val = re.sub(r'[\\/*?:"<>|]', "", val)
            new_name = new_name.replace(f"[{tag}]", val)

        dir_name = os.path.dirname(self.current_filepath)
        new_path = os.path.join(dir_name, new_name)

        try:
            os.rename(self.current_filepath, new_path)
            QMessageBox.information(self, "Success", f"Renamed to {new_name}")

            # update UI
            for i in range(self.file_list.count()):
                item = self.file_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == self.current_filepath:
                    item.setData(Qt.ItemDataRole.UserRole, new_path)
                    item.setText(new_name)
                    self.current_filepath = new_path
                    break
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
