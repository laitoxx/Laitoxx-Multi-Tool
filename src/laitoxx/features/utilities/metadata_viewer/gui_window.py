import os

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from laitoxx.core.settings.theme import load_default_theme
from laitoxx.interfaces.gui.translator import translator


class GlassButton(QPushButton):
    pass


from .engine import engine_instance
from .forensics import MetadataForensics
from .sanitizer import MetadataSanitizer


class WorkerThread(QThread):
    finished_signal = pyqtSignal(dict)

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath

    def run(self):
        try:
            data = engine_instance.extract_metadata(self.filepath)
            self.finished_signal.emit(data)
        except Exception as e:
            self.finished_signal.emit({"error": str(e)})


class MetadataViewerWindow(QDialog):
    def __init__(self, parent=None, theme_data=None):
        super().__init__(parent)
        self.setWindowTitle(translator.get("metadata_viewer_title"))
        self.setMinimumSize(900, 600)
        self.setAcceptDrops(True)

        self.theme_data = theme_data or load_default_theme()
        self.current_metadata = {}
        self.current_filepath = None
        self.worker = None

        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        self.lbl_status = QLabel(translator.get("metadata_drag_drop"))
        self.btn_open = GlassButton("Open File")
        self.btn_open.clicked.connect(self._browse_file)
        header_layout.addWidget(self.lbl_status)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_open)
        main_layout.addLayout(header_layout)

        # Splitter for files list and tabs
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.file_list = QListWidget()
        self.file_list.setMaximumWidth(250)
        self.file_list.itemClicked.connect(self._on_file_selected)
        self.splitter.addWidget(self.file_list)

        self.tabs = QTabWidget()
        self.splitter.addWidget(self.tabs)
        main_layout.addWidget(self.splitter)

        # Tab 1: Raw Metadata
        self.tab_raw = QWidget()
        raw_layout = QVBoxLayout(self.tab_raw)
        self.table_meta = QTableWidget()
        self.table_meta.setColumnCount(2)
        self.table_meta.setHorizontalHeaderLabels(["Property", "Value"])
        self.table_meta.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        raw_layout.addWidget(self.table_meta)
        self.tabs.addTab(self.tab_raw, "Raw Metadata")

        # Tab 2: Forensics & Privacy
        self.tab_forensics = QWidget()
        for_layout = QVBoxLayout(self.tab_forensics)
        self.lbl_privacy_score = QLabel("Privacy Score: N/A")
        self.lbl_privacy_score.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.lbl_privacy_rec = QLabel("")
        self.lbl_privacy_rec.setWordWrap(True)
        self.list_anomalies = QListWidget()

        for_layout.addWidget(self.lbl_privacy_score)
        for_layout.addWidget(self.lbl_privacy_rec)
        for_layout.addWidget(QLabel("Detected Anomalies & Leaks:"))
        for_layout.addWidget(self.list_anomalies)

        # Sanitizer button inside Forensics
        self.btn_sanitize = GlassButton("Sanitize (Wipe All Metadata)")
        self.btn_sanitize.setStyleSheet("background-color: rgba(255,0,0,0.3);")
        self.btn_sanitize.clicked.connect(self._sanitize_current)
        for_layout.addWidget(self.btn_sanitize)
        self.tabs.addTab(self.tab_forensics, "Forensics & Privacy")

        # Tab 3: Productivity (Smart Renamer)
        self.tab_prod = QWidget()
        prod_layout = QVBoxLayout(self.tab_prod)
        prod_layout.addWidget(QLabel("Smart Renamer (Uses Metadata Tags)"))
        self.input_rename_pattern = QLineEdit()
        self.input_rename_pattern.setPlaceholderText("E.g. [EXIF:Make]_[EXIF:Model]_[FileExtension]")
        prod_layout.addWidget(self.input_rename_pattern)
        self.btn_rename = GlassButton("Rename Current File")
        self.btn_rename.clicked.connect(self._smart_rename)
        prod_layout.addWidget(self.btn_rename)
        prod_layout.addStretch()
        self.tabs.addTab(self.tab_prod, "Productivity")

        # Tab 4: Graph Analysis
        self.tab_graph = QWidget()
        graph_layout = QVBoxLayout(self.tab_graph)
        graph_layout.addWidget(QLabel("Visualize relationships between files, authors, and software."))
        self.btn_export_graph = GlassButton("Export to Graph Editor")
        self.btn_export_graph.clicked.connect(self._export_to_graph)
        graph_layout.addWidget(self.btn_export_graph)
        graph_layout.addStretch()
        self.tabs.addTab(self.tab_graph, "Graph Analysis")

    def _apply_style(self):
        td = self.theme_data
        bg = td.get("window_bg_color", "#121212")
        fg = td.get("title_text_color", "#ffffff")
        self.setStyleSheet(
            f"QDialog {{ background-color: {bg}; color: {fg}; }} "
            f"QLabel {{ color: {fg}; }} "
            f"QTableWidget {{ background-color: {td.get('text_area_bg_color', '#1e1e1e')}; color: {fg}; }} "
            f"QListWidget {{ background-color: {td.get('text_area_bg_color', '#1e1e1e')}; color: {fg}; }}"
        )

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
        path, _ = QFileDialog.getOpenFileName(self, "Open File")
        if path:
            self._add_file_to_list(path)

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
        self._load_file(filepath)

    def _on_file_selected(self, item):
        filepath = item.data(Qt.ItemDataRole.UserRole)
        self._load_file(filepath)

    def _load_file(self, filepath):
        self.current_filepath = filepath
        self.lbl_status.setText(f"Loading metadata for {os.path.basename(filepath)}...")

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

    def _on_load_finished(self, data):
        self.lbl_status.setText("Metadata loaded.")
        if "error" in data and len(data) == 1:
            QMessageBox.warning(self, "Error", data["error"])
            return

        self.current_metadata = data
        self._populate_raw_table(data)
        self._populate_forensics(data)

    def _populate_raw_table(self, data):
        self.table_meta.setRowCount(0)
        row = 0
        for k, v in data.items():
            if k == "ExtractedWith":
                v = ", ".join(v)
            self.table_meta.insertRow(row)
            self.table_meta.setItem(row, 0, QTableWidgetItem(str(k)))
            self.table_meta.setItem(row, 1, QTableWidgetItem(str(v)))
            row += 1

    def _populate_forensics(self, data):
        self.list_anomalies.clear()

        # Privacy Score
        privacy = MetadataForensics.calculate_privacy_score(data)
        score = privacy["score"]

        color = "#00ff00" if score >= 80 else "#ffaa00" if score >= 50 else "#ff0000"
        self.lbl_privacy_score.setText(f"Privacy Score: <span style='color:{color}'>{score}/100</span>")
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

    def _export_to_graph(self):
        from PyQt6.QtWidgets import QApplication

        main_win = None
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, "_open_graph_editor"):
                main_win = widget
                break

        if not main_win:
            QMessageBox.warning(self, "Error", "Cannot find main window to launch Graph Editor.")
            return

        main_win._open_graph_editor()
        graph_win = main_win._graph_editor_window
        if not graph_win or not hasattr(graph_win, "_graph"):
            QMessageBox.warning(self, "Error", "Graph Editor could not be initialized.")
            return

        added_files = 0
        added_edges = 0

        # Track globally created nodes to link correctly
        author_nodes = {}
        software_nodes = {}

        # To avoid blocking the UI, we'll iterate through items that were loaded.
        # Actually, we can just process all files currently in self.file_list.
        # We need their metadata.
        # If they haven't been clicked, we don't have their metadata yet.
        # Let's run a quick batch extraction for all files in the list.
        self.lbl_status.setText("Exporting to Graph Editor...")

        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            filepath = item.data(Qt.ItemDataRole.UserRole)

            # Synchronous extraction for graph build
            data = engine_instance.extract_metadata(filepath)
            if "error" in data:
                continue

            import uuid

            from laitoxx.shared.graph.model import Edge, Node

            # File Node
            file_node = Node(
                id=str(uuid.uuid4()),
                label=data.get("FileName", os.path.basename(filepath)),
                node_type="Document",
            )
            graph_win._graph.add_node(file_node)
            added_files += 1

            # Extract Authors
            for key in ["Author", "Creator", "Producer", "OwnerName"]:
                val = data.get(key)
                if val:
                    val_str = str(val)
                    if val_str not in author_nodes:
                        author_node = Node(id=str(uuid.uuid4()), label=val_str, node_type="Person")
                        graph_win._graph.add_node(author_node)
                        author_nodes[val_str] = author_node
                    edge = Edge(
                        id=str(uuid.uuid4()),
                        source_id=author_nodes[val_str].id,
                        target_id=file_node.id,
                        label="created/edited",
                        edge_type="Connected",
                    )
                    graph_win._graph.add_edge(edge)
                    added_edges += 1

            # Extract Software
            for key in [
                "EXIF:Software",
                "Software",
                "Tika:creator",
                "Hachoir:Software",
            ]:
                val = data.get(key)
                if val:
                    val_str = str(val)
                    if val_str not in software_nodes:
                        software_node = Node(
                            id=str(uuid.uuid4()),
                            label=val_str,
                            node_type="Custom",
                            mermaid_shape="hexagon",
                        )
                        graph_win._graph.add_node(software_node)
                        software_nodes[val_str] = software_node
                    edge = Edge(
                        id=str(uuid.uuid4()),
                        source_id=file_node.id,
                        target_id=software_nodes[val_str].id,
                        label="created with",
                        edge_type="Connected",
                    )
                    graph_win._graph.add_edge(edge)
                    added_edges += 1

        graph_win._refresh_all()
        self.lbl_status.setText("Export complete.")
        QMessageBox.information(
            self,
            "Graph Export",
            f"Exported {added_files} files and {added_edges} relationships to Graph Editor!",
        )


def open_metadata_viewer(parent, theme_data):
    dlg = MetadataViewerWindow(parent, theme_data)
    dlg.exec()
