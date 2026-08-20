"""Focused behavior slice for MetadataViewerWindow."""
# ruff: noqa: F405

from .gui_window_context import *  # noqa: F403


class MetadataViewerWindowMixin3:
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
