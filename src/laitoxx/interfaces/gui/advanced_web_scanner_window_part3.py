"""Focused behavior slice for AdvancedWebScannerWindow."""
# ruff: noqa: F405

from .advanced_web_scanner_window_context import *  # noqa: F403


class AdvancedWebScannerWindowMixin3:
    def _show_selected_source(self):
        selected = self.sources_tree.selectedItems()
        if not selected or not self.report:
            return
        index = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if index is None:
            return
        result = self.report.providers[index]
        self.source_details.setPlainText(
            json.dumps(
                {
                    "name": result.name,
                    "status": result.status,
                    "error": result.error,
                    "data": result.data,
                    "entities": [vars(item) for item in result.entities],
                    "relations": [vars(item) for item in result.relations],
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )

    def _export_json(self):
        if not self.report:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, translator.get("aws_export_json"), "advanced-web-scan.json", "JSON (*.json)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(self.report.to_dict(), stream, ensure_ascii=False, indent=2, default=str)

    def _open_graph_editor(self):
        if not self.report:
            return
        self.tabs.setCurrentWidget(self.graph_tab)
        self.graph_editor.raise_()

    def _load_graph_projection(self):
        projection = project_for_graph(self.report)
        graph = Graph(name=f"Web scan: {self.report.target.value}", direction="TD")
        nodes = {}
        target_entity_id = f"{self.report.target.kind}:{self.report.target.value.casefold()}"
        for entity in projection.entities:
            node_type = self._graph_node_type(entity)
            node = Node.from_type(entity.label or entity.value, node_type)
            node.metadata = {"kind": entity.kind, **entity.metadata}
            if entity.id == target_entity_id:
                node.metadata["is_target"] = True
            node.description = str(entity.metadata.get("explanation") or entity.metadata.get("description") or "")
            graph.add_node(node)
            nodes[entity.id] = node
        for relation in projection.relations:
            source = nodes.get(relation.source)
            target = nodes.get(relation.target)
            if not source or not target:
                continue
            edge = Edge(source.id, target.id, label=relation.relation, edge_type="Connected")
            edge.metadata = {
                "source": relation.source_name,
                "confidence": relation.confidence,
                "current": relation.current,
                "evidence": relation.evidence,
                "state": relation.state,
                "observed_at": relation.observed_at,
                "checked_at": relation.checked_at,
                "expires_at": relation.expires_at,
                "supporting_sources": relation.supporting_sources,
            }
            edge.mermaid_line = "-.->" if relation.current is False else "-->"
            graph.add_edge(edge)
        self.graph_projection_notice.setText(
            ""
            if not (projection.omitted_entities or projection.omitted_relations)
            else translator.get(
                "aws_graph_safety_filter",
                entities=projection.omitted_entities,
                relations=projection.omitted_relations,
            )
        )
        self.graph_editor.set_graph(graph, self.graph_projection_notice.text() or translator.get("ge_status_ready"))

    @staticmethod
    def _graph_node_type(entity: Entity) -> str:
        if entity.kind == "service":
            category = entity.metadata.get("category")
            return {
                "database": "Database",
                "admin_panel": "AdminPanel",
                "remote_access": "RemoteAccess",
                "monitoring": "Monitoring",
                "message_broker": "MessageBroker",
                "devops": "DevOps",
                "file_sharing": "FileService",
                "mail": "MailService",
            }.get(category, "Service")
        return {
            "ip": "IP",
            "domain": "Domain",
            "url": "URL",
            "asn": "ASN",
            "prefix": "Network",
            "dns_record": "DNS",
            "organization": "Organization",
            "cpe": "Software",
            "technology": "Software",
            "cve": "Vulnerability",
            "certificate": "Certificate",
            "cloud": "Cloud",
            "infrastructure_provider": "Cloud",
            "dns_policy": "DNS",
            "rpki_status": "Network",
            "web_artifact": "URL",
            "web_fingerprint": "ThreatIndicator",
            "url_parameter": "Custom",
            "indicator": "ThreatIndicator",
            "finding": "ThreatIndicator",
        }.get(entity.kind, "Custom")

    def closeEvent(self, event):
        if self._thread and self._thread.isRunning():
            stop_and_detach_thread(self._thread)
            self._thread = None
        super().closeEvent(event)
