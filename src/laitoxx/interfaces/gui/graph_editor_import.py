"""Focused GraphEditorWindow responsibility mixin."""
# ruff: noqa: F405

from __future__ import annotations

import os

from PyQt6.QtWidgets import (
    QMessageBox,
)

from laitoxx.shared.graph.mermaid import generate_mermaid
from laitoxx.shared.graph.model import (
    Edge,
    Node,
)

from .graph_ui_style import *  # noqa: F403


class GraphEditorImportMixin:
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return

        filepaths = []
        for url in urls:
            fp = url.toLocalFile()
            if fp:
                filepaths.append(fp)

        if not filepaths:
            event.ignore()
            return

        supported_extensions = {
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
            ".tiff",
            ".mp3",
            ".wav",
            ".mp4",
            ".avi",
            ".doc",
            ".xls",
            ".ppt",
            ".docx",
            ".xlsx",
            ".pptx",
            ".exe",
            ".dll",
            ".sys",
        }

        # Validate file extensions
        for fp in filepaths:
            ext = os.path.splitext(fp)[1].lower()
            if ext not in supported_extensions:
                QMessageBox.warning(
                    self,
                    _t("error"),
                    _t("ge_unsupported_file_type", ext=ext),
                    QMessageBox.StandardButton.Ok,
                )
                event.ignore()
                return

        event.acceptProposedAction()
        self.import_files(filepaths)

    def import_files(self, filepaths: list[str]):
        from laitoxx.features.utilities.metadata_viewer.engine import engine_instance

        imported_nodes = []
        imported_edges = []

        for fp in filepaths:
            try:
                metadata = engine_instance.extract_metadata(fp)
            except Exception as e:
                metadata = {
                    "FilePath": fp,
                    "FileName": os.path.basename(fp),
                    "error": str(e),
                }

            meta_str = {str(k): str(v) for k, v in metadata.items()}
            doc_label = os.path.basename(fp)

            # Find or create Document node
            doc_node = None
            for node in self._graph.nodes:
                if node.label == doc_label and node.node_type == "Document":
                    doc_node = node
                    break

            if doc_node is None:
                doc_node = Node.from_type(doc_label, "Document")
                doc_node.metadata = meta_str
                self._graph.add_node(doc_node)
                imported_nodes.append(doc_node)
            else:
                doc_node.metadata.update(meta_str)

            # Authors
            author_names = set()
            for k in ["Author", "Creator", "Producer", "OwnerName"]:
                val = metadata.get(k)
                if val:
                    if isinstance(val, list):
                        for item in val:
                            if str(item).strip():
                                author_names.add(str(item).strip())
                    elif isinstance(val, str):
                        if val.strip():
                            author_names.add(val.strip())
                    else:
                        if str(val).strip():
                            author_names.add(str(val).strip())

            for name in author_names:
                person_node = None
                for node in self._graph.nodes:
                    if node.label == name and node.node_type == "Person":
                        person_node = node
                        break

                if person_node is None:
                    person_node = Node.from_type(name, "Person")
                    self._graph.add_node(person_node)
                    imported_nodes.append(person_node)

                # Find or create edge from Person to Document
                edge_found = None
                for edge in self._graph.edges:
                    if (
                        edge.source_id == person_node.id
                        and edge.target_id == doc_node.id
                        and edge.label == "created/edited"
                    ):
                        edge_found = edge
                        break

                if edge_found is None:
                    new_edge = Edge(
                        source_id=person_node.id,
                        target_id=doc_node.id,
                        label="created/edited",
                        edge_type="Connected",
                    )
                    self._graph.add_edge(new_edge)
                    imported_edges.append(new_edge)

            # Software
            software_names = set()
            for k in ["EXIF:Software", "Software", "Tika:creator", "Hachoir:Software"]:
                val = metadata.get(k)
                if val:
                    if isinstance(val, list):
                        for item in val:
                            if str(item).strip():
                                software_names.add(str(item).strip())
                    elif isinstance(val, str):
                        if val.strip():
                            software_names.add(val.strip())
                    else:
                        if str(val).strip():
                            software_names.add(str(val).strip())

            for name in software_names:
                software_node = None
                for node in self._graph.nodes:
                    if node.label == name and node.node_type == "Custom":
                        software_node = node
                        break

                if software_node is None:
                    software_node = Node.from_type(name, "Custom")
                    software_node.mermaid_shape = "hexagon"
                    self._graph.add_node(software_node)
                    imported_nodes.append(software_node)

                # Find or create edge from Document to Software
                edge_found = None
                for edge in self._graph.edges:
                    if (
                        edge.source_id == doc_node.id
                        and edge.target_id == software_node.id
                        and edge.label == "created with"
                    ):
                        edge_found = edge
                        break

                if edge_found is None:
                    new_edge = Edge(
                        source_id=doc_node.id,
                        target_id=software_node.id,
                        label="created with",
                        edge_type="Connected",
                    )
                    self._graph.add_edge(new_edge)
                    imported_edges.append(new_edge)

        # The native scene owns its item lifecycle; rebuilding here avoids
        # stale links after importing a document-derived subgraph.
        self._refresh_view()

        # Sync Python lists and stats
        self._refresh_nodes_list()
        self._refresh_edges_list()
        self._raw_code.setPlainText(generate_mermaid(self._graph))
        self._set_status(
            f"Imported {len(filepaths)} file(s). Added {len(imported_nodes)} nodes, {len(imported_edges)} edges."
        )
